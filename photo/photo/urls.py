"""
Routage principal de l'application Photo Scan.

Ce module structure l'ensemble des points d'entrée (endpoints) de l'API :
1. Authentification & Sécurité : Connexion JWT (email/username), rafraîchissement et profil (/auth/me/).
2. SaaS Multi-tenant : Création de clients via lien WhatsApp (Option B) et invitation de collaborateurs.
3. Événements publics : Consultation du catalogue, des galeries et recherche par reconnaissance faciale.
4. Participants & RGPD : Enregistrement, upload du selfie de référence et droit à l'oubli.
5. Espace d'administration : Gestion des médias, statistiques d'organisation et upload par lots.
6. Documentation OpenAPI : Schémas et interfaces interactives Swagger / Redoc.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from drf_spectacular.utils import extend_schema

from apps.events.auth_serializers import CustomTokenObtainPairSerializer
from apps.events.views import (
    EventListView,
    EventDetailView,
    EventPhotosView,
    MyPhotosView,
)
from apps.events.admin_views import (
    AdminStatsView,
    AdminContactsView,
    AdminLogoUploadView,
    AdminEventsView,
)
from apps.organizations.views import (
    AuthMeView,
    AdminCreateClientAccountView,
    SetPasswordFromTokenView,
    TeamMembersView,
    TeamMemberDetailView,
    CreateTeamInvitationView,
)
from apps.participants.views import (
    ParticipantView,
    FaceReferenceView,
    ParticipantDeleteView,
)
from apps.media.views import (
    AdminMediaUploadView,
    AdminMediaDeleteView,
)

# ==============================================================================
# VUES D'AUTHENTIFICATION JWT PERSONNALISÉES
# ==============================================================================

@extend_schema(
    tags=["Authentification"],
    summary="Connexion JWT (email ou username)",
    description="Authentifie un administrateur à l'aide de son email (ex: admin@clovis-dev.bf) et retourne les tokens access & refresh."
)
class LoginView(TokenObtainPairView):
    """
    Vue de connexion JWT personnalisée.
    Utilise CustomTokenObtainPairSerializer pour permettre aux utilisateurs de se connecter
    soit avec leur adresse email, soit avec leur nom d'utilisateur (plus ergonomique pour les clients).
    La directive throttle_scope applique la règle de 10 req/min définie dans settings.py.
    """
    serializer_class = CustomTokenObtainPairSerializer
    throttle_scope = 'auth'

@extend_schema(
    tags=["Authentification"],
    summary="Rafraîchissement de token JWT",
    description="Génère un nouveau token d'accès à partir du token de rafraîchissement."
)
class CustomTokenRefreshView(TokenRefreshView):
    """
    Renouvelle le jeton d'accès sans forcer l'utilisateur à ressaisir ses identifiants.
    Applique la rotation des tokens pour invalider l'ancien refresh token.
    """
    pass

# ==============================================================================
# MOTIFS D'URLS DE L'API REST
# ==============================================================================
# Regroupés dans une liste dédiée afin d'être exposés simultanément :
# - Sous le préfixe standardisé versionné `/api/v1/`
# - À la racine `/` pour garantir la rétrocompatibilité avec les frontends existants.
api_patterns = [
    # --- Authentification & Profil SaaS ---
    path("auth/login/", LoginView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("auth/me/", AuthMeView.as_view(), name="auth-me"),
    path("auth/set-password/", SetPasswordFromTokenView.as_view(), name="auth-set-password"),

    # --- SaaS Multi-tenant : Gestion des Clients & Équipes (Flux WhatsApp) ---
    path("admin/clients/create/", AdminCreateClientAccountView.as_view(), name="admin-client-create"),
    path("admin/team/", TeamMembersView.as_view(), name="admin-team-list"),
    path("admin/team/<int:pk>/", TeamMemberDetailView.as_view(), name="admin-team-member-delete"),
    path("admin/team/invite/", CreateTeamInvitationView.as_view(), name="admin-team-invite"),

    # --- Catalogue & Galeries Publiques d'Événements ---
    path("events/", EventListView.as_view(), name="event-list"),
    path("events/<slug:slug>/", EventDetailView.as_view(), name="event-detail"),
    path("events/<slug:slug>/photos/", EventPhotosView.as_view(), name="event-photos"),
    path("events/<slug:slug>/my-photos/", MyPhotosView.as_view(), name="my-photos"),

    # --- Participants & Conformité RGPD ---
    path("participants/", ParticipantView.as_view(), name="participants"),
    path("participants/<int:pk>/face-reference/", FaceReferenceView.as_view(), name="face-reference"),
    path("participants/<int:pk>/", ParticipantDeleteView.as_view(), name="participant-delete"),

    # --- Administration Sécurisée & Médias (Multi-tenant) ---
    path("admin/events/", AdminEventsView.as_view(), name="admin-events"),
    path("admin/stats/", AdminStatsView.as_view(), name="admin-stats"),
    path("admin/contacts/", AdminContactsView.as_view(), name="admin-contacts"),
    path("admin/events/<slug:slug>/media/", AdminMediaUploadView.as_view(), name="admin-media-upload"),
    path("admin/events/<slug:slug>/logo/", AdminLogoUploadView.as_view(), name="admin-logo-upload"),
    path("admin/media/<int:pk>/", AdminMediaDeleteView.as_view(), name="admin-media-delete"),
]

# ==============================================================================
# RACINE DU ROUTAGE GLOBAL
# ==============================================================================
urlpatterns = [
    # Administration Django par défaut
    path("django-admin/", admin.site.urls),

    # Documentation interactive Swagger / OpenAPI 3
    # Plusieurs alias sont fournis pour faciliter l'accès aux développeurs frontend
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui-root"),
    path("api/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui-alt"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # Endpoints API avec et sans préfixe api/v1/ (garantie de rétrocompatibilité)
    path("api/v1/", include(api_patterns)),
    path("", include(api_patterns)),
]

# En mode DEBUG local, Django prend en charge le service direct des fichiers médias uploadés.
# En production, ce rôle est dévolu à WhiteNoise (statiques) ou à un bucket/disque persistant.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
