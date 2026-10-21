"""
Sérialiseurs pour les opérations de téléversement et réponses médias.

Ce module structure les flux de données entrants et sortants pour :
- L'upload unitaire d'image (logos d'organisations, bannières d'événements)
- L'upload massif par lots (batch) de photos de reportage
- Le schéma de réponse de recherche faciale personnalisée.
"""

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.openapi import OpenApiTypes


class SingleFileUploadSerializer(serializers.Serializer):
    """
    Validation pour le téléversement d'un fichier binaire unique (champ 'file').
    Utilisé notamment pour le logo de l'événement et les selfies de référence.
    """
    file = serializers.FileField(help_text="Fichier image source (JPEG, PNG ou WEBP)")


class MultiFileUploadSerializer(serializers.Serializer):
    """
    Validation pour le téléversement simultané d'une série de photos (champ 'files').
    Permet aux photographes d'envoyer des lots complets de prise de vue en une seule requête HTTP.
    """
    files = serializers.ListField(
        child=serializers.FileField(),
        help_text="Sélection de photos multiples à téléverser et soumettre au moteur IA"
    )


class MyPhotosResponseSerializer(serializers.Serializer):
    """
    Schéma de la réponse retournée au participant lors de sa recherche faciale.
    - 'status' : État d'avancement ('no_reference', 'pending', 'ready')
    - 'photos' : Liste des fiches photos matchées avec URL et légende.
    """
    status = serializers.ChoiceField(
        choices=["no_reference", "pending", "ready"],
        help_text="État du matching biométrique"
    )
    photos = serializers.ListField(
        child=serializers.DictField(),
        help_text="Collection des photos reconnues pour ce participant"
    )


class PhotoPatchSerializer(serializers.Serializer):
    """
    Validation pour la modification d'une photo (visibilité publique / légende).
    """
    isPublic = serializers.BooleanField(required=False, help_text="Rendre visible ou masquer dans la galerie publique")
    legend = serializers.CharField(max_length=200, required=False, allow_blank=True, help_text="Légende de la photo")


class AdminPhotoListSerializer(serializers.Serializer):
    """
    Représentation allégée d'une photo pour la liste d'administration.
    Retourne TOUTES les photos (publiques ET privées) afin de permettre à
    l'organisateur de retrouver et de réactiver une photo passée en privé.
    """
    id = serializers.IntegerField()
    thumbnail = serializers.SerializerMethodField(help_text="URL de la miniature")
    isPublic = serializers.BooleanField(source="is_public")
    legend = serializers.CharField(allow_blank=True)
    createdAt = serializers.DateTimeField(source="created_at")

    @extend_schema_field(OpenApiTypes.URI)
    def get_thumbnail(self, obj):
        request = self.context.get("request")
        if obj.thumbnail:
            url = obj.thumbnail.url
            return request.build_absolute_uri(url) if request else url
        if obj.file:
            url = obj.file.url
            return request.build_absolute_uri(url) if request else url
        return None

