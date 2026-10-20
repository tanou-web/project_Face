"""
Configuration ASGI (Asynchronous Server Gateway Interface) pour le projet 'photo'.

Ce point d'entrée expose l'application 'application' pour les serveurs compatibles ASGI
(tels que Uvicorn ou Daphne). Il permet la prise en charge de protocoles asynchrones
comme les WebSockets (utile pour les notifications en temps réel de fin d'analyse faciale).
"""

import os
from django.core.asgi import get_asgi_application

# Définition de l'environnement de configuration pour les workers ASGI
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'photo.settings')

# Instanciation de l'application ASGI réceptive aux flux asynchrones
application = get_asgi_application()
