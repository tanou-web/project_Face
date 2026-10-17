import numpy as np
from django.test import TestCase
from apps.faces.utils import cosine_similarity, is_same_person, validate_selfie, MATCH_THRESHOLD

class FaceUtilsTestCase(TestCase):
    def test_cosine_similarity_identical(self):
        v1 = np.random.rand(512).astype(np.float32)
        score = cosine_similarity(v1, v1)
        self.assertAlmostEqual(score, 1.0, places=4)
        self.assertTrue(is_same_person(v1, v1))

    def test_cosine_similarity_orthogonal(self):
        v1 = np.zeros(512, dtype=np.float32)
        v1[0] = 1.0
        v2 = np.zeros(512, dtype=np.float32)
        v2[1] = 1.0
        score = cosine_similarity(v1, v2)
        self.assertAlmostEqual(score, 0.0, places=4)
        self.assertFalse(is_same_person(v1, v2))

    def test_threshold_constant(self):
        self.assertEqual(MATCH_THRESHOLD, 0.40)

    def test_validate_selfie_invalid_bytes(self):
        bad_bytes = b"not an image"
        result = validate_selfie(bad_bytes)
        self.assertFalse(result["valid"])
        self.assertIn("illisible", result["error"])

    def test_task_matching_matrix(self):
        from apps.events.models import Event
        from apps.media.models import Photo, FaceIndex
        from apps.participants.models import Participant, FaceReference, PhotoMatch
        from apps.faces.tasks import match_participant_to_event

        event = Event.objects.create(
            slug="test-event",
            name="Test Event",
            tagline="Tagline",
            description="Desc",
            city="Ouaga",
            date="2026-07-18",
            status="en_ligne"
        )
        photo1 = Photo.objects.create(event=event, file="photos/p1.jpg", is_public=True)
        photo2 = Photo.objects.create(event=event, file="photos/p2.jpg", is_public=True)

        # Embedding 1 correspond au participant
        vec = np.random.rand(512).astype(np.float32)
        norm_vec = (vec / np.linalg.norm(vec)).tolist()

        # Embedding 2 est orthogonal (ne match pas)
        vec_other = np.zeros(512, dtype=np.float32)
        vec_other[0] = 1.0
        # S'assurer que norm_vec a 0 sur l'indice 0 pour être strictement orthogonal
        vec[0] = 0.0
        norm_vec = (vec / np.linalg.norm(vec)).tolist()

        FaceIndex.objects.create(photo=photo1, embedding=norm_vec)
        FaceIndex.objects.create(photo=photo2, embedding=vec_other.tolist())

        participant = Participant.objects.create(
            first_name="Test",
            last_name="User",
            phone="+226 71112233",
            match_status="pending"
        )
        FaceReference.objects.create(participant=participant, embedding=norm_vec)

        # Lancer la tâche de matching
        res = match_participant_to_event(participant.id, event.slug)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["matched"], 1)

        participant.refresh_from_db()
        self.assertEqual(participant.match_status, "ready")

        matches = PhotoMatch.objects.filter(participant=participant)
        self.assertEqual(matches.count(), 1)
        self.assertEqual(matches.first().photo_id, photo1.id)
