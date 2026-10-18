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
    et participants y sont rattachés.
    """
    name = models.CharField(max_length=200, help_text="Nom de l'organisation ou de l'organisateur")
    slug = models.SlugField(max_length=220, unique=True, db_index=True)
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
    is_active = models.BooleanField(default=True, help_text="Accès actif à la plateforme")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Organisation"
        verbose_name_plural = "Organisations"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
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
        """Retourne le rôle de l'utilisateur ('owner', 'manager', 'photographer' ou None)."""
        if user == self.owner or user.is_superuser:
            return "owner"
        membership = self.memberships.filter(user=user).first()
        return membership.role if membership else None


class OrganizationMembership(models.Model):
    """
    Gestion des membres d'une organisation avec rôles et permissions.
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
        unique_together = ("organization", "user")

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()}) - {self.organization.name}"


class Invitation(models.Model):
    """
    Invitation par lien copiable (valable 7 jours) pour rejoindre une organisation ou définir son mot de passe.
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
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return (not self.is_used) and (timezone.now() < self.expires_at)
