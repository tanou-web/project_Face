"""
Vues de l'API pour l'authentification SaaS, le multi-tenant et l'onboarding WhatsApp.

Ce module implémente la logique métier des comptes et de la sécurité SaaS :
1. `AuthMeView` : Profil de l'utilisateur connecté avec son organisation et son rôle effectif.
2. `AdminCreateClientAccountView` : Onboarding Option B (création directe de compte client + lien WhatsApp copiable).
3. `SetPasswordFromTokenView` : Consommation du jeton WhatsApp et définition du mot de passe (sans email).
4. `TeamMembersView` & `CreateTeamInvitationView` : Gestion des collaborateurs de l'organisation.
"""

import secrets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from drf_spectacular.utils import extend_schema, OpenApiTypes, OpenApiParameter
from django.conf import settings

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


def build_frontend_invitation_url(request, token: str) -> str:
    """
    Construit l'URL absolue vers la page frontend de saisie de mot de passe.
    Si FRONTEND_URL est configuré dans settings (ou variable d'env Render), l'utilise en priorité.
    Sinon, se replie sur l'URL absolue de la requête courante.
    """
    frontend_base = getattr(settings, 'FRONTEND_URL', '')
    path = f"/auth/set-password?token={token}"
    if frontend_base:
        return f"{frontend_base.rstrip('/')}{path}"
    return request.build_absolute_uri(path)


class AuthMeView(APIView):
    """
    Endpoint d'introspection du compte connecté : 'Qui suis-je ?'

    Permet au frontend (Angular, React, Vue) d'adapter dynamiquement l'interface :
    - Afficher le nom de l'organisation et du photographe connecté en haut à droite.
    - Masquer les boutons 'Inviter des membres' et 'Créer un événement' si le rôle est 'photographer'.
    - Donner accès aux statistiques globales de la plateforme si 'superuser'.
    """
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
    Onboarding Client - Option B (Par l'administrateur système).

    Pourquoi ce choix :
    En contexte professionnel en Afrique de l'Ouest (Burkina Faso), l'envoi d'invitations par email
    se heurte fréquemment aux filtres anti-spam ou à une faible consultation des boîtes de réception.
    L'administrateur de la plateforme crée donc ici l'organisation et le compte client pré-initialisé,
    puis obtient un lien sécurisé à usage unique (valable 7 jours) qu'il peut copier et transmettre
    directement au client via WhatsApp ou SMS.
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

        # 1. Résolution ou création du compte User avec nom d'utilisateur unique
        username = email.split("@")[0]
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exclude(email=email).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = User.objects.filter(email=email).first()
        if not user:
            # Génération d'un mot de passe temporaire complexe non communiqué :
            # Le client devra obligatoirement passer par le jeton WhatsApp pour définir le sien.
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

        # 2. Création de l'Organisation associée avec le client comme propriétaire
        org, org_created = Organization.objects.get_or_create(
            owner=user,
            defaults={
                "name": org_name,
                "phone": data.get("ownerPhone", ""),
                "is_active": True,
            }
        )

        # 3. Création automatique de l'adhésion en tant que 'owner' pour le tableau d'équipe
        OrganizationMembership.objects.get_or_create(
            organization=org,
            user=user,
            defaults={"role": "owner"}
        )

        # 4. Création du jeton d'invitation (durée de validité de 7 jours)
        invitation = Invitation.objects.create(
            organization=org,
            email=email,
            phone=data.get("ownerPhone", ""),
            role="owner",
            created_by=request.user,
            target_user=user,
        )

        # Construction du lien vers la page frontend de saisie de mot de passe
        full_url = build_frontend_invitation_url(request, invitation.token)

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
    Point d'entrée pour la consommation et la vérification du jeton d'invitation WhatsApp.

    Accessible sans authentification préalable (AllowAny).
    - GET : Vérifie la validité du jeton et retourne les informations de l'invitation (nom de l'organisation, rôle, email).
    - POST : Valide le jeton, affecte le mot de passe choisi, active le compte et rattache l'utilisateur à l'organisation.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentification"],
        summary="Vérifier la validité d'un lien d'invitation (token)",
        description="Permet à la page frontend 'Définir mon mot de passe' de vérifier si le lien est valide, non expiré et de récupérer le nom de l'organisation et le profil invité avant la saisie.",
        parameters=[
            OpenApiParameter(
                name="token",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Jeton unique d'invitation reçu dans l'URL"
            )
        ],
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    )
    def get(self, request):
        token = request.query_params.get("token", "").strip()
        if not token:
            return Response({"error": "Le paramètre 'token' est obligatoire."}, status=status.HTTP_400_BAD_REQUEST)

        invitation = Invitation.objects.filter(token=token).select_related("organization", "target_user").first()
        if not invitation:
            return Response({"valid": False, "error": "Ce lien d'invitation est invalide ou introuvable."}, status=status.HTTP_404_NOT_FOUND)

        if not invitation.is_valid:
            return Response({"valid": False, "error": "Ce lien d'invitation a expiré ou a déjà été utilisé."}, status=status.HTTP_400_BAD_REQUEST)

        target = invitation.target_user
        return Response({
            "valid": True,
            "token": invitation.token,
            "role": invitation.role,
            "roleLabel": invitation.get_role_display(),
            "organization": {
                "id": invitation.organization.id,
                "name": invitation.organization.name,
                "slug": invitation.organization.slug,
            },
            "email": invitation.email or (target.email if target else ""),
            "firstName": target.first_name if target else "",
            "lastName": target.last_name if target else "",
            "expiresAt": invitation.expires_at,
        })

    @extend_schema(
        tags=["Authentification"],
        summary="Définir son mot de passe et accepter l'invitation",
        description="Active le compte et enregistre le mot de passe du client ou du collaborateur à partir du token d'invitation WhatsApp.",
        request=SetPasswordFromTokenSerializer,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        serializer = SetPasswordFromTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        invitation = Invitation.objects.filter(token=data["token"]).select_related("organization", "target_user").first()
        if not invitation:
            return Response({"error": "Lien d'invitation invalide."}, status=status.HTTP_404_NOT_FOUND)

        if not invitation.is_valid:
            return Response({"error": "Ce lien d'invitation a expiré ou a déjà été utilisé."}, status=status.HTTP_400_BAD_REQUEST)

        # Cas 1 : Utilisateur cible pré-créé (Option B - Propriétaire de l'organisation)
        if invitation.target_user:
            user = invitation.target_user
            user.set_password(data["password"])
            if data.get("firstName"):
                user.first_name = data["firstName"]
            if data.get("lastName"):
                user.last_name = data["lastName"]
            user.is_active = True
            user.save()

            # Garantir l'adhésion explicite de propriétaire
            OrganizationMembership.objects.get_or_create(
                organization=invitation.organization,
                user=user,
                defaults={"role": "owner"}
            )
        else:
            # Cas 2 : Invitation d'un nouveau collaborateur (Membre d'équipe invité par un manager/owner)
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
            # Liaison de l'utilisateur à l'organisation avec le rôle attribué dans l'invitation
            OrganizationMembership.objects.create(
                organization=invitation.organization,
                user=user,
                role=invitation.role,
            )

        # Invalidation immédiate du jeton pour empêcher toute réutilisation (protection anti-rejeu)
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
    Gestion des membres d'équipe au sein de l'organisation connectée.
    Permet au propriétaire et aux gestionnaires de consulter la liste des collaborateurs actuels.
    """
    permission_classes = [IsOrganizationManagerOrOwner]

    @extend_schema(
        tags=["Équipe SaaS"],
        summary="Lister les collaborateurs de l'organisation",
        responses={200: TeamMemberSerializer(many=True)}
    )
    def get(self, request):
        org = get_user_organization(request.user)
        # S'assurer que le propriétaire a bien un membership explicite 'owner' pour apparaître dans la liste
        if org.owner:
            OrganizationMembership.objects.get_or_create(
                organization=org,
                user=org.owner,
                defaults={"role": "owner"}
            )
        members = OrganizationMembership.objects.filter(organization=org).select_related("user").order_by("created_at")
        serializer = TeamMemberSerializer(members, many=True)
        return Response(serializer.data)


class TeamMemberDetailView(APIView):
    """
    Gestion individuelle d'un collaborateur d'équipe.
    Permet de retirer un membre de l'organisation.
    """
    permission_classes = [IsOrganizationManagerOrOwner]

    @extend_schema(
        tags=["Équipe SaaS"],
        summary="Retirer un collaborateur de l'équipe",
        description="Retire un membre de l'organisation. Seul un propriétaire ou gestionnaire peut effectuer cette action. Le propriétaire principal ne peut pas être retiré.",
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT}
    )
    def delete(self, request, pk):
        org = get_user_organization(request.user)
        user_role = get_user_role(request.user, org)

        membership = get_object_or_404(OrganizationMembership, pk=pk, organization=org)

        # Protection : impossible d'expulser le propriétaire principal
        if membership.user == org.owner or membership.role == "owner":
            return Response(
                {"error": "Impossible de retirer le propriétaire de l'organisation."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Un gestionnaire ne peut pas retirer un autre gestionnaire ou le propriétaire
        if user_role == "manager" and membership.role in ["manager", "owner"]:
            return Response(
                {"error": "Seul le propriétaire de l'organisation peut retirer un autre gestionnaire."},
                status=status.HTTP_403_FORBIDDEN
            )

        user_name = membership.user.get_full_name() or membership.user.username
        membership.delete()
        return Response({
            "success": True,
            "message": f"Le collaborateur {user_name} a été retiré de l'équipe."
        }, status=status.HTTP_200_OK)


class CreateTeamInvitationView(APIView):
    """
    Génération d'un lien d'invitation sécurisé pour ajouter un collaborateur.

    Le responsable choisit le rôle :
    - 'manager' : pour un co-gestionnaire
    - 'photographer' : pour un photographe dédié à la prise de vue
    Retourne une URL et un message WhatsApp prêt à être copié-collé.
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

        full_url = build_frontend_invitation_url(request, invitation.token)

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
