"""
Modèles de données pour la gestion des Participants, de la Biométrie et de la Conformité RGPD.

Ce module structure les données des invités aux événements :
1. `Participant` : Fiche usager identifiée par son numéro WhatsApp avec machine à états de reconnaissance.
2. `FaceReference` : Empreinte faciale mathématique (Privacy-by-Design : zéro photo brute conservée).
3. `PhotoMatch` : Table de liaison établissant les correspondances entre photos d'événements et participants.
"""

from django.db import models
from apps.media.models import Photo


class Participant(models.Model):
    """
    Représente un invité ou participant à un ou plusieurs événements.

    L'unicité est portée par le numéro de téléphone au format E.164 (`+226...`),
    ce qui permet à un utilisateur de retrouver l'ensemble de ses photos même s'il participe
    à plusieurs cérémonies distinctes au fil des années.
    """
    # Cycle de vie de la recherche faciale
    MATCH_STATUS = [
        ("no_reference", "Pas de photo de référence"), # Le participant n'a pas encore pris de selfie
        ("pending", "Matching en cours"),              # Selfie reçu, tâche Celery en cours d'exécution
        ("ready", "Matching terminé"),                 # Algorithme terminé, photos consultables
    ]
    first_name = models.CharField(max_length=100, help_text="Prénom de l'invité")
    last_name = models.CharField(max_length=100, help_text="Nom de famille de l'invité")
    phone = models.CharField(max_length=30, unique=True, db_index=True, help_text="Numéro WhatsApp normalisé E.164")
    match_status = models.CharField(max_length=20, choices=MATCH_STATUS, default="no_reference", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Participant"
        verbose_name_plural = "Participants"
        indexes = [
            models.Index(fields=["phone"]),
            models.Index(fields=["match_status"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone})"


class FaceReference(models.Model):
    """
    Empreinte faciale de référence du participant.

    Principe de protection de la vie privée (Privacy by Design / RGPD) :
    Aucun fichier image brut (selfie original) n'est jamais conservé sur le serveur ou en base de données.
    Dès la réception du selfie, l'algorithme calcule immédiatement la projection mathématique
    (vecteur 512D) puis détruit l'image source. Ce vecteur unidirectionnel est irréversible
    (il est impossible de reconstituer le visage d'origine à partir des 512 nombres flottants).
    """
    participant = models.OneToOneField(Participant, on_delete=models.CASCADE, related_name="face_reference")
    # Liste de 512 nombres flottants (vecteur unitaire normalisé issu du modèle ArcFace)
    embedding = models.JSONField(help_text="Signature vectorielle 512D issue du selfie")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Référence faciale"
        verbose_name_plural = "Références faciales"

    def __str__(self):
        return f"FaceReference ({self.participant})"


class PhotoMatch(models.Model):
    """
    Table de correspondance indiquant qu'un participant a été identifié avec succès sur une photo.
    Assure une relation plusieurs-à-plusieurs (Many-to-Many) optimisée.
    """
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="matches")
    photo = models.ForeignKey(Photo, on_delete=models.CASCADE, related_name="matched_participants")

    class Meta:
        verbose_name = "Correspondance photo"
        verbose_name_plural = "Correspondances photos"
        # Empêche d'enregistrer deux fois le même match pour une paire (participant, photo)
        unique_together = ("participant", "photo")
        indexes = [
            models.Index(fields=["participant", "photo"]),
        ]

    def __str__(self):
        return f"Match P{self.participant_id} <-> Photo {self.photo_id}"
