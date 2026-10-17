import cv2
import numpy as np
import logging
from .engine import get_face_app

logger = logging.getLogger(__name__)

# Seuil recommandé pour InsightFace buffalo_l
MATCH_THRESHOLD = 0.40

def cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
    """
    Retourne la similarité cosinus normalisée entre deux embeddings.
    """
    norm1 = np.linalg.norm(emb1)
    norm2 = np.linalg.norm(emb2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    n1 = emb1 / norm1
    n2 = emb2 / norm2
    return float(np.dot(n1, n2))

def is_same_person(emb_ref: np.ndarray, emb_photo: np.ndarray) -> bool:
    return cosine_similarity(emb_ref, emb_photo) >= MATCH_THRESHOLD

def validate_selfie(image_bytes: bytes) -> dict:
    """
    Retourne { "valid": bool, "error": str | None }
    Vérifie : décodage image, taille minimale (200x200), flou (Laplacian var >= 50),
    1 seul visage détecté, taille du visage (au moins 20% de la largeur).
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return {"valid": False, "error": "Fichier image illisible ou corrompu."}

    h, w = img.shape[:2]
    if w < 200 or h < 200:
        return {"valid": False, "error": "Image trop petite (minimum 200×200 px)."}

    # Détection de flou (Laplacian variance)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    if blur_score < 50:
        return {"valid": False, "error": "Photo trop floue. Retake en pleine lumière."}

    app = get_face_app()
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    faces = app.get(rgb)

    if len(faces) == 0:
        return {"valid": False, "error": "Aucun visage détecté. Prenez un selfie bien de face."}
    if len(faces) > 1:
        return {"valid": False, "error": "Plusieurs visages détectés. Un seul visage requis."}

    face = faces[0]
    bbox = face.bbox  # [x1, y1, x2, y2]
    face_width = bbox[2] - bbox[0]
    if face_width < w * 0.20:
        return {"valid": False, "error": "Visage trop petit sur la photo. Rapprochez-vous."}

    return {"valid": True, "error": None}

def extract_single_embedding(image_bytes: bytes) -> np.ndarray | None:
    """
    Pour le selfie de référence : attend exactement 1 visage.
    Retourne l'embedding 512-dim unitaire (norm=1) ou None si 0 ou >1 visage détecté.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return None
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    app = get_face_app()
    faces = app.get(rgb)
    if len(faces) != 1:
        return None
    emb = faces[0].embedding
    norm = np.linalg.norm(emb)
    if norm > 0:
        emb = emb / norm
    return emb

def extract_embeddings(image_path: str) -> list[dict]:
    """
    Extrait tous les visages détectés dans l'image spécifiée par image_path.
    Retourne une liste de dictionnaires [{"embedding": list[float] unitaire, "bbox": list[float]}].
    """
    img = cv2.imread(image_path)
    if img is None:
        return []
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    app = get_face_app()
    faces = app.get(rgb)
    results = []
    for face in faces:
        bbox = face.bbox.tolist() if hasattr(face, "bbox") and face.bbox is not None else None
        emb = face.embedding
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm
        embedding = emb.tolist() if hasattr(emb, "tolist") else list(emb)
        results.append({
            "embedding": embedding,
            "bbox": bbox
        })
    return results
