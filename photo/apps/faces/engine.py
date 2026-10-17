import logging
import insightface
import numpy as np

logger = logging.getLogger(__name__)

_app = None

def get_face_app():
    global _app
    if _app is None:
        logger.info("Chargement du modèle InsightFace FaceAnalysis(buffalo_l)...")
        _app = insightface.app.FaceAnalysis(
            name="buffalo_l",
            allowed_modules=["detection", "recognition"],
        )
        # ctx_id=0 -> GPU si disponible, ctx_id=-1 -> CPU
        _app.prepare(ctx_id=-1, det_size=(640, 640))
        logger.info("Modèle InsightFace prêt.")
    return _app
