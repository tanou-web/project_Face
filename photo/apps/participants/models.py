from django.db import models
from apps.media.models import Photo

class Participant(models.Model):
    MATCH_STATUS = [
        ("no_reference", "Pas de photo de référence"),
        ("pending", "Matching en cours"),
        ("ready", "Matching terminé"),
    ]
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=30, unique=True, db_index=True)
    match_status = models.CharField(max_length=20, choices=MATCH_STATUS, default="no_reference", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["phone"]),
            models.Index(fields=["match_status"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone})"

class FaceReference(models.Model):
    """
    JAMAIS de photo brute stockée — uniquement l'embedding.
    """
    participant = models.OneToOneField(Participant, on_delete=models.CASCADE, related_name="face_reference")
    embedding = models.JSONField()  # list[float] 512 éléments
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"FaceReference ({self.participant})"

class PhotoMatch(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="matches")
    photo = models.ForeignKey(Photo, on_delete=models.CASCADE, related_name="matched_participants")

    class Meta:
        unique_together = ("participant", "photo")
        indexes = [
            models.Index(fields=["participant", "photo"]),
        ]

    def __str__(self):
        return f"Match P{self.participant_id} <-> Photo {self.photo_id}"
