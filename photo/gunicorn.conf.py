# Configuration Gunicorn pour Render
# Optimisé pour le traitement d'images avec InsightFace

import multiprocessing
import os

# Timeout augmenté pour le téléchargement du modèle InsightFace et traitement d'images
# Le modèle buffalo_l.zip fait 281 MB et peut prendre 30-60s à télécharger au premier appel
timeout = 120  # 2 minutes (au lieu de 30s par défaut)

# Timeout pour la lecture de la requête (upload de fichiers volumineux)
graceful_timeout = 120

# Nombre de workers : 1 sur Render Free (512 MB RAM)
# InsightFace + NumPy + PIL consomment ~400-500 MB par worker
workers = 1

# Type de worker : sync (meilleur pour le traitement CPU-intensif comme la détection de visages)
worker_class = "sync"

# Connexions simultanées par worker
worker_connections = 10

# Redémarrage automatique après N requêtes (évite les fuites mémoire)
max_requests = 100
max_requests_jitter = 10

# Logs détaillés
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "info"

# Bind (Render définit automatiquement $PORT)
bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"

# Pre-load de l'application (partage du modèle InsightFace entre workers)
# ⚠️ DÉSACTIVÉ sur Render Free car 1 seul worker
preload_app = False

# Gestion du signal de terminaison gracieuse
graceful_timeout = 30

print(f"🚀 Gunicorn configuré : {workers} worker(s), timeout={timeout}s")
