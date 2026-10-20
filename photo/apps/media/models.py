"""
Modèles de données pour le stockage et l'indexation des Médias (Photos, Visages, Vidéos).

Ce module structure la conservation des contenus audiovisuels des événements :
1. `Photo` : Fichier haute résolution avec partitionnement mensuel et indexation optimisée.
2. `FaceIndex` : Vecteurs d'empreintes faciales (embeddings 512D) et boîtes englobantes (bounding boxes).
3. `Video` : Vidéo récapitulative (aftermovie) associée à un événement.
"""

from django.db import models
from apps.events.models import Event


class Photo(models.Model):
    """
    Représente une prise de vue officielle d'un événement.

    Organisation sur le stockage :
    L'attribut `upload_to="photos/%Y/%m/"` organise automatiquement les fichiers
    dans des sous-dossiers par année et mois. Cette pratique évite d'engorger un répertoire unique
    avec des dizaines de milliers de fichiers, ce qui dégraderait les performances du système de fichiers (inode lookups).
    """
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="photos")
    file = models.ImageField(upload_to="photos/%Y/%m/", help_text="Image source en haute définition")
    thumbnail = models.ImageField(upload_to="thumbs/%Y/%m/", null=True, blank=True, help_text="Miniature allégée pour affichage rapide")
    legend = models.CharField(max_length=200, blank=True, help_text="Légende ou description optionnelle")
    is_public = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Visible dans la galerie publique de l'événement"
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Photo"
        verbose_name_plural = "Photos"
        # Index composite couvrant la requête principale de consultation de galerie :
        # WHERE event_id = X AND is_public = TRUE ORDER BY created_at DESC
        indexes = [
            models.Index(fields=["event", "is_public", "-created_at"]),
        ]

    def __str__(self):
        return f"Photo {self.id} ({self.event.slug})"


class FaceIndex(models.Model):
    """
    Indexation vectorielle des visages présents sur une photo.

    Principe de granularité :
    Il existe une relation 1-à-plusieurs entre une photo et ses visages.
    Si une photo de groupe met en scène 6 convives, le moteur de détection créera 6 instances distinctes de `FaceIndex`.
    """
    photo = models.ForeignKey(Photo, on_delete=models.CASCADE, related_name="face_indexes")
    # Vecteur numérique dense de 512 flottants représentant la signature biométrique mathématique du visage (ArcFace)
    embedding = models.JSONField(help_text="Signature vectorielle 512D du visage")
    # Coordonnées du rectangle encadrant le visage dans l'image [x1, y1, x2, y2]
    bbox = models.JSONField(null=True, blank=True, help_text="Boîte englobante [x1, y1, x2, y2]")

    class Meta:
        verbose_name = "Index facial"
        verbose_name_plural = "Index faciaux"
        indexes = [
            models.Index(fields=["photo"]),
        ]

    def __str__(self):
        return f"FaceIndex {self.id} (Photo {self.photo_id})"


class Video(models.Model):
    """
    Fichier vidéo ou aftermovie associé à un événement.
    Relation 1-à-1 avec l'événement pour garantir une vidéo maîtresse unique par manifestation.
    """
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name="video")
    file = models.FileField(upload_to="videos/", help_text="Fichier vidéo MP4/WebM")
    title = models.CharField(max_length=200, help_text="Titre de la vidéo")
    duration = models.CharField(max_length=20, help_text="Durée lisible (ex: '3:45')")
    size_label = models.CharField(max_length=20, help_text="Taille lisible (ex: '45 Mo')")

    class Meta:
        verbose_name = "Vidéo"
        verbose_name_plural = "Vidéos"

    def __str__(self):
        return f"Video {self.title} ({self.event.slug})"
