"""
Commande de gestion Django pour l'initialisation des données de démonstration (seed_data).

Pourquoi cette commande est essentielle :
Exécutée automatiquement à chaque build dans `build.sh` (Render et CI/CD), elle garantit
qu'une base de données fraîchement déployée dispose immédiatement :
1. D'un compte superadministrateur fonctionnel (`admin@clovis-dev.bf`) pour tester la connexion JWT.
2. D'une organisation SaaS multi-tenant modèle (`Faso Business Club`).
3. D'un événement vitrine complet en ligne (`La Nuit des Entrepreneurs`) avec description et thèmes graphiques.
4. D'un participant de test avec numéro Burkinabè (+22670123456).

Toutes les opérations utilisent `get_or_create` pour être strictement idempotentes (aucun doublon lors des redéploiements).
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.events.models import Event
from apps.participants.models import Participant
import datetime

User = get_user_model()


class Command(BaseCommand):
    help = "Initialise des données de test (Événement La Nuit des Entrepreneurs, Admin, Participant)"

    def handle(self, *args, **options):
        # ----------------------------------------------------------------------
        # 1. Création idempotente du superadministrateur système
        # ----------------------------------------------------------------------
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

        # ----------------------------------------------------------------------
        # 2. Création de l'Organisation modèle (Multi-Tenant SaaS)
        # ----------------------------------------------------------------------
        from apps.organizations.models import Organization
        org, org_created = Organization.objects.get_or_create(
            owner=admin_user,
            defaults={
                "name": "Faso Business Club",
                "slug": "faso-business-club",
                "description": "Le réseau leader des bâtisseurs d'entreprises au Burkina Faso et en Afrique de l'Ouest.",
                "website": "https://fasobusinessclub.bf",
                "phone": "+22670112233",
                "is_active": True,
            }
        )
        if org_created:
            self.stdout.write(self.style.SUCCESS(f"Organisation créée : {org.name} ({org.slug})"))
        else:
            self.stdout.write(f"Organisation existante : {org.name}")

        # ----------------------------------------------------------------------
        # 3. Création de l'événement vitrine rattaché à l'Organisation
        # ----------------------------------------------------------------------
        event, created = Event.objects.get_or_create(
            slug="nuit-des-entrepreneurs",
            defaults={
                "organization": org,
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
        # Garantit le rattachement multi-tenant même si l'événement existait avant la migration
        if not event.organization:
            event.organization = org
            event.save(update_fields=["organization"])

        if created:
            self.stdout.write(self.style.SUCCESS(f"Événement créé : {event.name} ({event.slug})"))
        else:
            self.stdout.write(f"Événement déjà existant : {event.name}")

        # ----------------------------------------------------------------------
        # 4. Création d'un participant de démonstration (Workflow reconnaissance)
        # ----------------------------------------------------------------------
        participant, p_created = Participant.objects.get_or_create(
            phone="+22670123456",
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
