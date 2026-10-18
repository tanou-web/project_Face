import secrets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from drf_spectacular.utils import extend_schema, OpenApiTypes

from apps.organizations.models import Organization, OrganizationMembership, Invitation
from apps.organizations.permissions import (
    get_user_organization,
    get_user_role,
    IsOrganizationMember,
    IsOrganizationManagerOrOwner,
    IsOrganizationOwner,
)
from apps.organizations.serializers import (
    AuthMeResponseSerializer,
    CreateClientAccountSerializer,
    CreateInvitationSerializer,
    SetPasswordFromTokenSerializer,
    TeamMemberSerializer,
    InvitationItemSerializer,
    OrganizationSummarySerializer,
    UserProfileSerializer,
)

User = get_user_model()

class AuthMeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Authentification"],
        summary="Profil de l'utilisateur connecté avec son organisation et rôle",
        description="Retourne les informations de l'utilisateur, l'organisation à laquelle il appartient et son rôle ('owner', 'manager', 'photographer' ou 'superuser'). Permet d'adapter l'interface et les menus frontend.",
        responses={200: AuthMeResponseSerializer}
    )
    def get(self, request):
        user = request.user
        org = get_user_organization(user)
        role = get_user_role(user, org)

        user_data = UserProfileSerializer(user).data
        org_data = OrganizationSummarySerializer(org).data if org else None

        return Response({
            "user": user_data,
            "organization": org_data,
            "role": role or ("superuser" if user.is_superuser else "guest"),
        })


class AdminCreateClientAccountView(APIView):
    """
    Option B : Création de compte par l'admin plateforme.
    Génère une organisation + un compte utilisateur pré-créé + un lien copiable WhatsApp valable 7 jours.
    """
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["Plateforme Admin"],
        summary="Créer un compte client avec lien WhatsApp copiable (Option B)",
        description="L'administrateur plateforme crée l'organisation et le compte client. Retourne un lien unique valable 7 jours pour que le client définisse son mot de passe sans passer par un email.",
        request=CreateClientAccountSerializer,
        responses={201: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        serializer = CreateClientAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        email = data["ownerEmail"].strip().lower()
        org_name = data["organizationName"].strip()

        # 1. Création ou récupération du compte User
        username = email.split("@")[0]
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exclude(email=email).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = User.objects.filter(email=email).first()
        if not user:
            # Mot de passe aléatoire temporaire non utilisable directement
            random_pw = secrets.token_urlsafe(24)
            user = User.objects.create_user(
                username=username,
                email=email,
                password=random_pw,
                first_name=data.get("ownerFirstName", ""),
                last_name=data.get("ownerLastName", ""),
            )
            is_new_user = True
        else:
            is_new_user = False

        # 2. Création de l'Organisation
        org, org_created = Organization.objects.get_or_create(
            owner=user,
            defaults={
                "name": org_name,
                "phone": data.get("ownerPhone", ""),
                "is_active": True,
            }
        )

        # 3. Création de l'Invitation avec Token (7 jours)
        invitation = Invitation.objects.create(
            organization=org,
            email=email,
            phone=data.get("ownerPhone", ""),
            role="owner",
            created_by=request.user,
            target_user=user,
        )

        # Lien copiable vers le frontend pour WhatsApp
        set_password_path = f"/auth/set-password?token={invitation.token}"
        full_url = request.build_absolute_uri(set_password_path)

        return Response({
            "success": True,
            "organization": {
                "id": org.id,
                "name": org.name,
                "slug": org.slug,
            },
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
            },
            "invitationToken": invitation.token,
            "setPasswordUrl": full_url,
            "expiresAt": invitation.expires_at,
            "whatsappMessage": (
                f"Bonjour ! Voici votre lien d'accès exclusif à votre espace photo {org.name} : "
                f"{full_url} (Valable 7 jours pour définir votre mot de passe)."
            )
        }, status=status.HTTP_201_CREATED)


class SetPasswordFromTokenView(APIView):
    """
    L'invité ouvre le lien WhatsApp (/auth/set-password?token=...) et définit son mot de passe.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentification"],
        summary="Définir son mot de passe depuis un lien d'invitation",
        description="Active le compte et enregistre le mot de passe du client ou du collaborateur à partir du token d'invitation WhatsApp.",
        request=SetPasswordFromTokenSerializer,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        serializer = SetPasswordFromTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        invitation = Invitation.objects.filter(token=data["token"]).first()
        if not invitation:
            return Response({"error": "Lien d'invitation invalide."}, status=status.HTTP_404_NOT_FOUND)

        if not invitation.is_valid:
            return Response({"error": "Ce lien d'invitation a expiré ou a déjà été utilisé."}, status=status.HTTP_400_BAD_REQUEST)

        # Cas 1 : Utilisateur cible pré-créé (Option B - Propriétaire d'organisation)
        if invitation.target_user:
            user = invitation.target_user
            user.set_password(data["password"])
            if data.get("firstName"):
                user.first_name = data["firstName"]
            if data.get("lastName"):
                user.last_name = data["lastName"]
            user.is_active = True
            user.save()
        else:
            # Cas 2 : Invitation d'un collaborateur (Team member)
            email = invitation.email or f"user_{secrets.token_hex(4)}@workspace.local"
            username = email.split("@")[0]
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            user = User.objects.create_user(
                username=username,
                email=email,
                password=data["password"],
                first_name=data.get("firstName", ""),
                last_name=data.get("lastName", ""),
            )
            # Rangement dans OrganizationMembership
            OrganizationMembership.objects.create(
                organization=invitation.organization,
                user=user,
                role=invitation.role,
            )

        invitation.is_used = True
        invitation.save(update_fields=["is_used"])

        return Response({
            "success": True,
            "message": "Mot de passe défini avec succès. Vous pouvez maintenant vous connecter.",
            "username": user.username,
            "email": user.email,
        })


class TeamMembersView(APIView):
    """
    Gestion des membres d'équipe de l'organisation connectée.
    """
    permission_classes = [IsOrganizationManagerOrOwner]

    @extend_schema(
        tags=["Équipe SaaS"],
        summary="Lister les collaborateurs de l'organisation",
        responses={200: TeamMemberSerializer(many=True)}
    )
    def get(self, request):
        org = get_user_organization(request.user)
        members = OrganizationMembership.objects.filter(organization=org).select_related("user")
        serializer = TeamMemberSerializer(members, many=True)
        return Response(serializer.data)


class CreateTeamInvitationView(APIView):
    """
    Créer une invitation par lien copiable (valable 7 jours) pour ajouter un collaborateur avec rôle (manager ou photographer).
    """
    permission_classes = [IsOrganizationManagerOrOwner]

    @extend_schema(
        tags=["Équipe SaaS"],
        summary="Générer un lien d'invitation pour un collaborateur (valable 7 jours)",
        description="Retourne un lien WhatsApp copiable avec le rôle spécifié ('manager' ou 'photographer'). Rôles vérifiés côté API (403).",
        request=CreateInvitationSerializer,
        responses={201: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        serializer = CreateInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        org = get_user_organization(request.user)
        invitation = Invitation.objects.create(
            organization=org,
            role=data.get("role", "manager"),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            created_by=request.user,
        )

        full_url = request.build_absolute_uri(f"/auth/set-password?token={invitation.token}")

        return Response({
            "token": invitation.token,
            "role": invitation.role,
            "invitationUrl": full_url,
            "expiresAt": invitation.expires_at,
            "whatsappMessage": (
                f"Bonjour ! Vous avez été invité à rejoindre l'équipe de {org.name} avec le rôle '{invitation.get_role_display()}'. "
                f"Cliquez ici pour activer votre compte : {full_url} (Valable 7 jours)."
            )
        }, status=status.HTTP_201_CREATED)
