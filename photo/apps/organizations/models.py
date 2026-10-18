from django.db import models
from django.conf import settings
from django.utils.text import slugify

class Organization(models.Model):
    """
    Représente le compte 'Organisateur' ou Tenant SaaS.
    Chaque organisateur possède son organisation et tous ses événements, photos
    et participants y sont rattachés.
    """
    name = models.CharField(max_length=200, help_text="Nom de l'organisation ou de l'organisateur")
    slug = models.SlugField(max_length=220, unique=True, db_index=True)
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization",
        help_text="Utilisateur propriétaire de l'organisation"
    )
    logo = models.ImageField(upload_to="organizations/logos/", null=True, blank=True)
    description = models.TextField(blank=True, default="")
    website = models.URLField(blank=True, null=True)
    phone = models.CharField(max_length=35, blank=True, default="")
    is_active = models.BooleanField(default=True, help_text="Accès actif à la plateforme")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Organisation"
        verbose_name_plural = "Organisations"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "org"
            slug = base_slug
            counter = 1
            while Organization.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
