"""
Sérialiseurs pour la gestion des Organisations, de l'Équipe et de l'Onboarding.

Ce module gère la sérialisation et la validation des données d'échange de l'API pour :
- L'inspection du profil connecté (`AuthMeResponseSerializer`)
- La création de comptes clients par l'administrateur sans email (`CreateClientAccountSerializer`)
- L'activation de compte et saisie du mot de passe via lien WhatsApp (`SetPasswordFromTokenSerializer`)
- La gestion des invitations et des membres collaborateurs d'une organisation.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization, OrganizationMembership, Invitation

User = get_user_model()


class OrganizationSummarySerializer(serializers.ModelSerializer):
    """
    Sérialiseur concis présentant la fiche d'une organisation.
    Utilisé dans les réponses de profil pour identifier l'espace de travail actif du client.
    """
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "description", "website", "phone", "is_active", "created_at"]


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Sérialiseur du profil utilisateur exposant les champs en camelCase
    afin de respecter les conventions de nommage des frameworks frontend (React / Angular / Vue).
    """
    firstName = serializers.CharField(source="first_name")
    lastName = serializers.CharField(source="last_name")

    class Meta:
        model = User
        fields = ["id", "username", "email", "firstName", "lastName", "is_staff", "is_superuser"]


class AuthMeResponseSerializer(serializers.Serializer):
    """
    Schéma de la réponse de l'endpoint '/auth/me/'.
    Permet au frontend d'adapter dynamiquement la barre de navigation et les permissions
    selon le rôle retourné ('owner', 'manager', 'photographer' ou 'superuser').
    """
    user = UserProfileSerializer(help_text="Données de l'utilisateur connecté")
    organization = OrganizationSummarySerializer(
        allow_null=True,
        help_text="Organisation à laquelle est rattaché l'utilisateur (None si superuser non affilié)"
    )
    role = serializers.CharField(
        help_text="Rôle de l'utilisateur : 'owner', 'manager', 'photographer' ou 'superuser'"
    )


class CreateClientAccountSerializer(serializers.Serializer):
    """
    Validation du formulaire de création de compte client par l'administrateur plateforme (Option B).
    Génère l'organisation et pré-crée le compte utilisateur sans déclencher d'envoi d'email automatique,
    laissant l'administrateur copier le lien pour l'envoyer directement sur WhatsApp.
    """
    organizationName = serializers.CharField(max_length=200, help_text="Nom commercial de l'organisation ou du studio")
    ownerEmail = serializers.EmailField(help_text="Adresse email unique du futur propriétaire")
    ownerFirstName = serializers.CharField(max_length=150, required=False, default="", help_text="Prénom du client")
    ownerLastName = serializers.CharField(max_length=150, required=False, default="", help_text="Nom de famille du client")
    ownerPhone = serializers.CharField(max_length=35, required=False, default="", help_text="Numéro WhatsApp du client (+226...)")


class CreateInvitationSerializer(serializers.Serializer):
    """
    Validation pour la génération d'un lien d'invitation à destination d'un nouveau collaborateur.
    Restreint les rôles attribuables par l'organisateur à 'manager' ou 'photographer'.
    """
    role = serializers.ChoiceField(
        choices=["manager", "photographer"],
        default="manager",
        help_text="Rôle assigné au collaborateur invité"
    )
    email = serializers.EmailField(required=False, default="", help_text="Email optionnel pour référence")
    phone = serializers.CharField(max_length=35, required=False, default="", help_text="Numéro WhatsApp optionnel")


class SetPasswordFromTokenSerializer(serializers.Serializer):
    """
    Sérialiseur consommant le token d'invitation pour activer le compte et fixer le mot de passe.
    Impose une longueur minimale de 8 caractères pour garantir la sécurité des comptes.
    """
    token = serializers.CharField(help_text="Jeton unique d'invitation reçu dans l'URL WhatsApp")
    password = serializers.CharField(min_length=8, write_only=True, help_text="Nouveau mot de passe sécurisé (min. 8 car.)")
    firstName = serializers.CharField(max_length=150, required=False, default="", help_text="Prénom à renseigner ou corriger")
    lastName = serializers.CharField(max_length=150, required=False, default="", help_text="Nom à renseigner ou corriger")


class TeamMemberSerializer(serializers.ModelSerializer):
    """
    Représentation détaillée d'un collaborateur au sein d'une organisation.
    Aplatit la relation OrganizationMembership pour faciliter l'affichage dans un tableau React.
    """
    userId = serializers.IntegerField(source="user.id")
    username = serializers.CharField(source="user.username")
    email = serializers.EmailField(source="user.email")
    firstName = serializers.CharField(source="user.first_name")
    lastName = serializers.CharField(source="user.last_name")
    role = serializers.CharField()
    createdAt = serializers.DateTimeField(source="created_at")

    class Meta:
        model = OrganizationMembership
        fields = ["id", "userId", "username", "email", "firstName", "lastName", "role", "createdAt"]


class InvitationItemSerializer(serializers.ModelSerializer):
    """
    Sérialiseur listant les invitations générées avec calcul de l'URL absolue prête à copier.
    """
    invitationUrl = serializers.SerializerMethodField()
    isValid = serializers.BooleanField(source="is_valid")

    class Meta:
        model = Invitation
        fields = ["id", "token", "role", "email", "phone", "expires_at", "is_used", "isValid", "invitationUrl", "created_at"]

    def get_invitationUrl(self, obj) -> str:
        """
        Construit l'URL absolue complète pointant vers la page frontend de définition de mot de passe.
        """
        request = self.context.get("request")
        path = f"/auth/set-password?token={obj.token}"
        return request.build_absolute_uri(path) if request else path
