"""
Modèles de données pour la gestion Multi-Tenant (SaaS) et les Organisations.

Ce module implémente l'architecture d'isolation des données de la plateforme :
1. `Organization` : Le tenant (client ou agence photo) propriétaire de ses événements et médias.
2. `OrganizationMembership` : L'association utilisateur-organisation avec contrôle d'accès basé sur les rôles (RBAC).
3. `Invitation` : Le mécanisme d'onboarding sécurisé par lien WhatsApp à usage unique (Option B).
"""

import secrets
from datetime import timedelta
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify


class Organization(models.Model):
    """
    Représente le compte 'Organisateur' ou Tenant SaaS.

    Chaque organisateur possède son organisation et tous ses événements, photos
    et participants y sont strictement rattachés pour garantir l'étanchéité des données
    entre les différents clients de la plateforme.
    """
    name = models.CharField(
        max_length=200,
        help_text="Nom commercial de l'organisation ou de l'agence photo"
    )
    # Le slug sert d'identifiant textuel unique dans les URLs publiques (ex: /events/?org=mon-agence)
    slug = models.SlugField(max_length=220, unique=True, db_index=True)
    
    # Le propriétaire principal détient les pleins pouvoirs administratifs sur l'organisation
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_organizations",
        help_text="Utilisateur propriétaire principal de l'organisation"
    )
    logo = models.ImageField(upload_to="organizations/logos/", null=True, blank=True)
    description = models.TextField(blank=True, default="")
    website = models.URLField(blank=True, null=True)
    phone = models.CharField(max_length=35, blank=True, default="")
    
    # Permet de suspendre l'accès d'un tenant en cas d'impayé ou de fin de contrat
    is_active = models.BooleanField(
        default=True,
        help_text="Accès actif à la plateforme (désactivable par l'administrateur système)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Organisation"
        verbose_name_plural = "Organisations"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        Génération automatique d'un slug unique à partir du nom lors de la création.
        En cas de doublon de nom, un suffixe incrémental (-1, -2...) est automatiquement ajouté.
        """
        if not self.slug:
            base_slug = slugify(self.name) or "org"
            slug = base_slug
            counter = 1
            while Organization.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_user_role(self, user):
        """
        Résout le rôle effectif d'un utilisateur au sein de cette organisation.

        Hiérarchie appliquée :
        - Le propriétaire ('owner') ou le superadministrateur système a tous les droits ('owner').
        - Pour les autres membres, le rôle est lu depuis OrganizationMembership ('manager' ou 'photographer').
        - Retourne None si l'utilisateur ne fait pas partie de l'organisation.
        """
        if user == self.owner or user.is_superuser:
            return "owner"
        membership = self.memberships.filter(user=user).first()
        return membership.role if membership else None


class OrganizationMembership(models.Model):
    """
    Table de liaison pour la gestion des collaborateurs d'une organisation.

    Met en œuvre le contrôle d'accès basé sur les rôles (RBAC) :
    - 'owner' : Propriétaire avec gestion des abonnements et suppression de l'organisation.
    - 'manager' : Gestionnaire pouvant créer/éditer des événements et inviter des membres.
    - 'photographer' : Accès restreint à l'upload de médias sur les événements existants.
    """
    ROLE_CHOICES = [
        ("owner", "Propriétaire"),
        ("manager", "Gestionnaire d'événements"),
        ("photographer", "Photographe (Upload uniquement)"),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="manager")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Membre d'organisation"
        verbose_name_plural = "Membres d'organisation"
        # Empêche d'assigner deux rôles distincts au même utilisateur dans une organisation
        unique_together = ("organization", "user")

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()}) - {self.organization.name}"


class Invitation(models.Model):
    """
    Gestion des invitations sécurisées par lien copiable (Option B).

    Conçu pour un onboarding sans friction via messagerie instantanée (WhatsApp) :
    - Génère un jeton cryptographique aléatoire de 32 octets (token_urlsafe).
    - Possède une durée de validité limitée à 7 jours pour des raisons de sécurité.
    - Deux cas d'usage :
      1. Client : Active un compte pré-créé (`target_user`) et lui permet de définir son mot de passe.
      2. Collaborateur : Permet à un membre d'équipe invité de s'enregistrer directement avec le rôle désiré.
    """
    ROLE_CHOICES = [
        ("owner", "Propriétaire"),
        ("manager", "Gestionnaire d'événements"),
        ("photographer", "Photographe (Upload uniquement)"),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="invitations"
    )
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=35, blank=True, default="")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="manager")
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_invitations"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_invitations",
        help_text="Utilisateur pré-créé par l'admin (Option B) qui doit définir son mot de passe"
    )

    class Meta:
        verbose_name = "Invitation"
        verbose_name_plural = "Invitations"

    def save(self, *args, **kwargs):
        """
        Initialise automatiquement un jeton unique et une date d'expiration de 7 jours
        lors de la première sauvegarde si non renseignés.
        """
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        """
        Vérifie si le lien d'invitation est encore consommable :
        - Il ne doit pas avoir déjà été utilisé.
        - L'horodatage actuel doit être strictement inférieur à la date d'expiration.
        """
        return (not self.is_used) and (timezone.now() < self.expires_at)
