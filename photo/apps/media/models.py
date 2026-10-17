from django.db import models
from apps.events.models import Event

class Photo(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="photos")
    file = models.ImageField(upload_to="photos/%Y/%m/")
    thumbnail = models.ImageField(upload_to="thumbs/%Y/%m/", null=True, blank=True)
    legend = models.CharField(max_length=200, blank=True)
    is_public = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["event", "is_public", "-created_at"]),
        ]

    def __str__(self):
        return f"Photo {self.id} ({self.event.slug})"

class FaceIndex(models.Model):
    """
    Un enregistrement par visage détecté dans une photo.
    Une photo de groupe avec 5 personnes = 5 FaceIndex.
    """
    photo = models.ForeignKey(Photo, on_delete=models.CASCADE, related_name="face_indexes")
    embedding = models.JSONField()  # list[float] de 512 éléments
    bbox = models.JSONField(null=True, blank=True)  # [x1, y1, x2, y2] position du visage

    class Meta:
        indexes = [
            models.Index(fields=["photo"]),
        ]

    def __str__(self):
        return f"FaceIndex {self.id} (Photo {self.photo_id})"

class Video(models.Model):
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name="video")
    file = models.FileField(upload_to="videos/")
    title = models.CharField(max_length=200)
    duration = models.CharField(max_length=20)
    size_label = models.CharField(max_length=20)

    def __str__(self):
        return f"Video {self.title} ({self.event.slug})"
