"""
Commande Django pour corriger les événements ayant un slug vide.
Génère automatiquement un slug basé sur le nom de l'événement.
"""

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from apps.events.models import Event
import random
import string


class Command(BaseCommand):
    help = "Corrige les événements ayant un slug vide en générant un slug à partir du nom"

    def handle(self, *args, **options):
        # Trouver tous les événements avec slug vide ou null
        empty_slug_events = Event.objects.filter(slug__in=['', None]) | Event.objects.filter(slug='')
        
        count = empty_slug_events.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS("✅ Aucun événement avec slug vide trouvé"))
            return
        
        self.stdout.write(f"🔍 Trouvé {count} événement(s) avec slug vide")
        
        fixed = 0
        for event in empty_slug_events:
            old_slug = event.slug
            
            # Générer slug basé sur le nom
            base_slug = slugify(event.name)
            
            if not base_slug:
                # Si le nom ne donne rien, utiliser l'ID
                base_slug = f"event-{event.id}"
            
            # Vérifier unicité
            slug = base_slug
            counter = 1
            while Event.objects.filter(slug=slug).exclude(id=event.id).exists():
                suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
                slug = f"{base_slug}-{suffix}"
                counter += 1
                
                if counter > 100:
                    slug = f"{base_slug}-{random.randint(10000, 99999)}"
                    break
            
            # Mettre à jour
            event.slug = slug
            event.save(update_fields=['slug'])
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Événement '{event.name}' (ID: {event.id}): '{old_slug or '(vide)'}' → '{slug}'"
                )
            )
            fixed += 1
        
        self.stdout.write(
            self.style.SUCCESS(f"\n🎉 {fixed} événement(s) corrigé(s) avec succès !")
        )
