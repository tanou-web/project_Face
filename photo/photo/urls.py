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

@extend_schema(
    tags=["Authentification"],
    summary="Connexion JWT (email ou username)",
    description="Authentifie un administrateur à l'aide de son email (ex: admin@clovis-dev.bf) et retourne les tokens access & refresh."
)
class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_scope = 'auth'

@extend_schema(
    tags=["Authentification"],
    summary="Rafraîchissement de token JWT",
    description="Génère un nouveau token d'accès à partir du token de rafraîchissement."
)
class CustomTokenRefreshView(TokenRefreshView):
    pass

api_patterns = [
    # Auth JWT
    path("auth/login/", LoginView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),

    # Public Events
    path("events/", EventListView.as_view(), name="event-list"),
    path("events/<slug:slug>/", EventDetailView.as_view(), name="event-detail"),
    path("events/<slug:slug>/photos/", EventPhotosView.as_view(), name="event-photos"),
    path("events/<slug:slug>/my-photos/", MyPhotosView.as_view(), name="my-photos"),

    # Participants & RGPD
    path("participants/", ParticipantView.as_view(), name="participants"),
    path("participants/<int:pk>/face-reference/", FaceReferenceView.as_view(), name="face-reference"),
    path("participants/<int:pk>/", ParticipantDeleteView.as_view(), name="participant-delete"),

    # Admin endpoints
    path("admin/stats/", AdminStatsView.as_view(), name="admin-stats"),
    path("admin/contacts/", AdminContactsView.as_view(), name="admin-contacts"),
    path("admin/events/<slug:slug>/media/", AdminMediaUploadView.as_view(), name="admin-media-upload"),
    path("admin/events/<slug:slug>/logo/", AdminLogoUploadView.as_view(), name="admin-logo-upload"),
    path("admin/media/<int:pk>/", AdminMediaDeleteView.as_view(), name="admin-media-delete"),
]

urlpatterns = [
    path("django-admin/", admin.site.urls),

    # Documentation interactive Swagger OpenAPI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui-root"),
    path("api/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui-alt"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # Endpoints API avec et sans préfixe api/v1/
    path("api/v1/", include(api_patterns)),
    path("", include(api_patterns)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
