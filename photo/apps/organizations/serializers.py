from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.organizations.models import Organization, OrganizationMembership, Invitation

User = get_user_model()

class OrganizationSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug", "description", "website", "phone", "is_active", "created_at"]

class UserProfileSerializer(serializers.ModelSerializer):
    firstName = serializers.CharField(source="first_name")
    lastName = serializers.CharField(source="last_name")

    class Meta:
        model = User
        fields = ["id", "username", "email", "firstName", "lastName", "is_staff", "is_superuser"]

class AuthMeResponseSerializer(serializers.Serializer):
    user = UserProfileSerializer()
    organization = OrganizationSummarySerializer(allow_null=True)
    role = serializers.CharField(help_text="Rôle de l'utilisateur : 'owner', 'manager', 'photographer' ou 'superuser'")

class CreateClientAccountSerializer(serializers.Serializer):
    """
    Utilisé par l'admin plateforme (Option B) pour pré-créer une organisation et son propriétaire,
    générant un lien copiable pour définir le mot de passe sans email.
    """
    organizationName = serializers.CharField(max_length=200, help_text="Nom de l'organisation / studio")
    ownerEmail = serializers.EmailField(help_text="Email du responsable")
    ownerFirstName = serializers.CharField(max_length=150, required=False, default="")
    ownerLastName = serializers.CharField(max_length=150, required=False, default="")
    ownerPhone = serializers.CharField(max_length=35, required=False, default="")

class CreateInvitationSerializer(serializers.Serializer):
    """
    Utilisé par un responsable d'organisation pour inviter un collaborateur (lien copiable 7 jours).
    """
    role = serializers.ChoiceField(choices=["manager", "photographer"], default="manager")
    email = serializers.EmailField(required=False, default="")
    phone = serializers.CharField(max_length=35, required=False, default="")

class SetPasswordFromTokenSerializer(serializers.Serializer):
    """
    Permet à l'invité d'activer son compte et de définir son mot de passe via le token reçu sur WhatsApp.
    """
    token = serializers.CharField()
    password = serializers.CharField(min_length=8, write_only=True)
    firstName = serializers.CharField(max_length=150, required=False, default="")
    lastName = serializers.CharField(max_length=150, required=False, default="")

class TeamMemberSerializer(serializers.ModelSerializer):
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
    invitationUrl = serializers.SerializerMethodField()
    isValid = serializers.BooleanField(source="is_valid")

    class Meta:
        model = Invitation
        fields = ["id", "token", "role", "email", "phone", "expires_at", "is_used", "isValid", "invitationUrl", "created_at"]

    def get_invitationUrl(self, obj) -> str:
        request = self.context.get("request")
        # Lien copiable vers le frontend
        path = f"/auth/set-password?token={obj.token}"
        return request.build_absolute_uri(path) if request else path
