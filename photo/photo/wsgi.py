"""
Configuration WSGI (Web Server Gateway Interface) pour le projet 'photo'.

Ce point d'entrée expose l'application callable 'application' utilisée par les serveurs
HTTP de production compatibles WSGI (tels que Gunicorn sur Render).
Il initialise le runtime Django et charge l'ensemble des modules du framework.
"""

import os
from django.core.wsgi import get_wsgi_application

# Définition de l'environnement de configuration pour les workers WSGI
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'photo.settings')

# Instanciation de l'application WSGI réceptive aux requêtes HTTP synchrones
application = get_wsgi_application()
