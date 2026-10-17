from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.events.models import Event
from apps.participants.models import Participant
import datetime

User = get_user_model()

class Command(BaseCommand):
    help = "Initialise des données de test (Événement La Nuit des Entrepreneurs, Admin, Participant)"

    def handle(self, *args, **options):
        # 1. Création du superutilisateur admin si nécessaire
        admin_email = "admin@clovis-dev.bf"
        admin_user = User.objects.filter(email=admin_email).first()
        if not admin_user:
            admin_user = User.objects.filter(username="admin").first()

        if not admin_user:
            admin_user = User.objects.create_superuser(
                username="admin",
                email=admin_email,
                password="adminpassword123"
            )
            self.stdout.write(self.style.SUCCESS(f"Superutilisateur créé : {admin_email} / adminpassword123"))
        else:
            self.stdout.write(f"Superutilisateur existant : {admin_user.username}")

        # 2. Création de l'événement Nuit des Entrepreneurs
        event, created = Event.objects.get_or_create(
            slug="nuit-des-entrepreneurs",
            defaults={
                "name": "La Nuit des Entrepreneurs",
                "tagline": "Le grand rendez-vous de l'écosystème entrepreneurial burkinabè",
                "description": "Une soirée d'exception réunissant plus de 400 chefs d'entreprise, innovateurs et investisseurs autour de tables rondes et d'une remise de distinctions.",
                "city": "Ouagadougou",
                "venue": "Hôtel Silmandé",
                "date": datetime.date(2026, 7, 18),
                "status": "en_ligne",
                "accent_color": "oklch(0.578 0.221 27.5)",
                "accent_text_color": "oklch(0.99 0 0)",
                "organizer_name": "Faso Business Club",
                "organizer_about": "Le réseau leader des bâtisseurs d'entreprises au Burkina Faso et en Afrique de l'Ouest.",
                "organizer_website": "https://fasobusinessclub.bf",
                "organizer_phone": "+226 70 11 22 33",
                "highlights": [
                    "Remise des Trophées de l'Innovation",
                    "Dîner de gala prestige",
                    "Networking VIP & investisseurs",
                ],
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Événement créé : {event.name} ({event.slug})"))
        else:
            self.stdout.write(f"Événement déjà existant : {event.name}")

        # 3. Création d'un participant de démonstration
        participant, p_created = Participant.objects.get_or_create(
            phone="+226 70123456",
            defaults={
                "first_name": "Aïcha",
                "last_name": "Ouédraogo",
                "match_status": "no_reference",
            }
        )
        if p_created:
            self.stdout.write(self.style.SUCCESS(f"Participant de test créé : {participant.first_name} ({participant.phone})"))
        else:
            self.stdout.write(f"Participant déjà existant : {participant.first_name}")

        self.stdout.write(self.style.SUCCESS("Initialisation des données terminée avec succès."))
