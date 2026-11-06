#!/usr/bin/env python
"""
Script de pré-téléchargement du modèle InsightFace au moment du build.
Évite le timeout lors de la première requête d'upload d'image.

Usage: python download_insightface_model.py
"""

import sys
import logging
from apps.faces.engine import get_face_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)

def main():
    """Pré-télécharge et initialise le modèle InsightFace."""
    try:
        logger.info("🔽 Pré-téléchargement du modèle InsightFace buffalo_l...")
        logger.info("⚠️  Cela peut prendre 1-2 minutes (téléchargement de ~281 MB)...")
        
        # Initialise le modèle (télécharge si nécessaire)
        app = get_face_app()
        
        logger.info("✅ Modèle InsightFace téléchargé et prêt.")
        logger.info(f"📦 Détails : {app}")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Erreur lors du téléchargement du modèle : {e}")
        logger.exception(e)
        return 1

if __name__ == "__main__":
    sys.exit(main())
