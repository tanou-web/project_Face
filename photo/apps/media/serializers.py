from rest_framework import serializers

class SingleFileUploadSerializer(serializers.Serializer):
    file = serializers.FileField(help_text="Fichier image (JPEG ou PNG)")

class MultiFileUploadSerializer(serializers.Serializer):
    files = serializers.ListField(
        child=serializers.FileField(),
        help_text="Sélection de photos à téléverser et indexer"
    )

class MyPhotosResponseSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["no_reference", "pending", "ready"])
    photos = serializers.ListField(child=serializers.DictField())
