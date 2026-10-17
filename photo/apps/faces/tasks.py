import logging
import numpy as np
from celery import shared_task
from apps.participants.models import Participant, FaceReference, PhotoMatch
from apps.media.models import FaceIndex
from .utils import MATCH_THRESHOLD

logger = logging.getLogger(__name__)

@shared_task
def match_participant_to_event(participant_id: int, event_slug: str):
    """
    Tâche de matching facial : compare l'embedding de référence (512D)
    avec tous les FaceIndex des photos publiques de l'événement.
    Optimisé par calcul matriciel NumPy ultra-rapide.
    """
    logger.info(f"Début du matching facial: participant={participant_id}, event={event_slug}")
    try:
        ref = FaceReference.objects.get(participant_id=participant_id)
    except FaceReference.DoesNotExist:
        logger.warning(f"FaceReference introuvable pour participant {participant_id}")
        return {"matched": 0, "status": "no_reference"}

    ref_embedding = np.array(ref.embedding, dtype=np.float32)

    # Récupère tous les FaceIndex des photos publiques de cet événement (une seule requête DB)
    face_indexes_qs = FaceIndex.objects.filter(
        photo__event__slug=event_slug,
        photo__is_public=True
    ).values_list("photo_id", "embedding")

    # Matérialiser en mémoire en une seule passe (évite le double-hit DB de .exists() + itération)
    face_indexes = list(face_indexes_qs)
    if not face_indexes:
        Participant.objects.filter(pk=participant_id).update(match_status="ready")
        return {"matched": 0, "status": "ready"}

    photo_ids = []
    embeddings_list = []
    for photo_id, emb in face_indexes:
        photo_ids.append(photo_id)
        embeddings_list.append(emb)

    matrix = np.array(embeddings_list, dtype=np.float32)

    # Normalisation L2
    ref_norm = ref_embedding / (np.linalg.norm(ref_embedding) + 1e-10)
    matrix_norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10
    normalized_matrix = matrix / matrix_norms

    # Similarité cosinus vectorisée pour l'ensemble des visages en une opération
    scores = np.dot(normalized_matrix, ref_norm)

    matched_indices = np.where(scores >= MATCH_THRESHOLD)[0]
    matched_photo_ids = {photo_ids[idx] for idx in matched_indices}

    for p_id in matched_photo_ids:
        PhotoMatch.objects.get_or_create(
            participant_id=participant_id,
            photo_id=p_id,
        )

    Participant.objects.filter(pk=participant_id).update(match_status="ready")
    logger.info(f"Matching terminé pour participant {participant_id}: {len(matched_photo_ids)} photos matchées.")
    return {"matched": len(matched_photo_ids), "status": "ready"}
