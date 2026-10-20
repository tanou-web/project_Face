"""
Configuration de l'instance Celery pour le projet 'photo'.

Ce module initialise le worker asynchrone chargé d'exécuter les traitements lourds :
- Analyse faciale des photos uploadées (détection de visages)
- Extraction des embeddings (vecteurs 512D)
- Comparaison géométrique avec les selfies des participants
- Notifications en tâche de fond

L'exécution asynchrone permet à l'API de répondre immédiatement au photographe
lors de l'upload sans bloquer la requête HTTP pendant les calculs d'IA.
"""
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Définit le module de configuration Django par défaut pour le programme 'celery'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'photo.settings')

# Instanciation de l'application Celery liée au projet
app = Celery('photo')

# Les clés de configuration Celery sont lues depuis settings.py sous le préfixe 'CELERY_'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Découverte automatique des fichiers tasks.py dans chaque application Django déclarée
app.autodiscover_tasks()
