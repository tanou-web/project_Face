from django.db import models

class Event(models.Model):
    STATUS_CHOICES = [
        ("en_ligne", "En ligne"),
        ("traitement", "Traitement"),
        ("archive", "Archive"),
    ]

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="events",
        null=True,
        blank=True,
        help_text="Organisation propriétaire de cet événement (multi-tenant)"
    )
    slug = models.SlugField(unique=True, db_index=True)
    name = models.CharField(max_length=200)
    tagline = models.CharField(max_length=300)
    description = models.TextField()
    logo = models.ImageField(upload_to="organizers/", null=True, blank=True)
    cover = models.ImageField(upload_to="covers/", null=True, blank=True)
    city = models.CharField(max_length=100)
    venue = models.CharField(max_length=200, blank=True)
    date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="traitement",
    )
    accent_color = models.CharField(max_length=100, default="oklch(0.578 0.221 27.5)")
    accent_text_color = models.CharField(max_length=100, default="oklch(0.99 0 0)")
    organizer_name = models.CharField(max_length=200)
    organizer_logo = models.ImageField(upload_to="organizers/", null=True, blank=True)
    organizer_about = models.TextField(blank=True)
    organizer_website = models.URLField(blank=True, null=True)
    organizer_phone = models.CharField(max_length=30, blank=True, null=True)
    highlights = models.JSONField(default=list)  # ["point 1", "point 2"]

    class Meta:
        indexes = [
            models.Index(fields=["status", "-date"]),
        ]

    def __str__(self):
        return self.name
