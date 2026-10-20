"""
Modèle de données pour la gestion des événements et des galeries associées.

Ce module définit l'entité centrale 'Event' :
- Rattachement multi-tenant à une organisation propriétaire
- Cycle de vie : de l'ingestion/traitement des photos jusqu'à la mise en ligne et l'archivage
- Personnalisation visuelle (couleurs d'accent OKLCH, logos, couvertures)
- Indexation optimisée pour les requêtes de consultation publique.
"""

from django.db import models


class Event(models.Model):
    """
    Représente un événement (mariage, gala, conférence, festival, cérémonie).

    L'événement regroupe l'ensemble des photos prises lors de la manifestation,
    les vidéos récapitulatives et les participants reconnus par le moteur IA.
    """
    # Cycle de vie d'un événement
    STATUS_CHOICES = [
        ("en_ligne", "En ligne"),     # Visible du grand public dans la galerie
        ("traitement", "Traitement"), # Photos en cours d'upload et de vectorisation IA (privé)
        ("archive", "Archive"),       # Événement clôturé
    ]

    # Rattachement Multi-Tenant :
    # Garantit que seuls les membres de cette organisation peuvent administrer l'événement
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="events",
        null=True,
        blank=True,
        help_text="Organisation propriétaire de cet événement (isolation multi-tenant)"
    )
    # Identifiant textuel unique pour l'URL publique (ex: /events/mariage-aminata-ibrahim/)
    slug = models.SlugField(unique=True, db_index=True)
    name = models.CharField(max_length=200, help_text="Titre officiel de l'événement")
    tagline = models.CharField(max_length=300, help_text="Slogan ou sous-titre d'accroche")
    description = models.TextField(help_text="Présentation détaillée de la cérémonie ou du projet")
    logo = models.ImageField(upload_to="organizers/", null=True, blank=True)
    cover = models.ImageField(upload_to="covers/", null=True, blank=True, help_text="Photo de couverture plein écran")
    city = models.CharField(max_length=100, help_text="Ville de l'événement (ex: Ouagadougou, Bobo-Dioulasso)")
    venue = models.CharField(max_length=200, blank=True, help_text="Lieu précis (salle, hôtel, domaine)")
    date = models.DateField(help_text="Date de déroulement de l'événement")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="traitement",
        help_text="Statut de publication"
    )
    # Paramètres de thème graphique dynamique (espace colorimétrique moderne OKLCH)
    accent_color = models.CharField(max_length=100, default="oklch(0.578 0.221 27.5)")
    accent_text_color = models.CharField(max_length=100, default="oklch(0.99 0 0)")
    
    # Informations sur l'organisateur hôte affichées sur la landing page
    organizer_name = models.CharField(max_length=200)
    organizer_logo = models.ImageField(upload_to="organizers/", null=True, blank=True)
    organizer_about = models.TextField(blank=True)
    organizer_website = models.URLField(blank=True, null=True)
    organizer_phone = models.CharField(max_length=30, blank=True, null=True)
    
    # Points forts ou temps forts de l'événement stockés au format JSON (liste de chaînes)
    highlights = models.JSONField(default=list)

    class Meta:
        verbose_name = "Événement"
        verbose_name_plural = "Événements"
        # Index composite : optimise les requêtes de la page d'accueil qui filtrent
        # sur les événements 'en_ligne' triés par date décroissante (-date).
        indexes = [
            models.Index(fields=["status", "-date"]),
        ]

    def __str__(self):
        return self.name
