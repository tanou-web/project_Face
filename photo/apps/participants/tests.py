import json
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from apps.events.models import Event
from apps.participants.models import Participant, FaceReference, PhotoMatch
from apps.media.models import Photo

class ParticipantAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.event = Event.objects.create(
            slug="nuit-des-entrepreneurs",
            name="La Nuit des Entrepreneurs",
            tagline="Le grand rendez-vous",
            description="Soirée annuelle",
            city="Ouagadougou",
            date="2026-07-18",
            status="en_ligne",
            organizer_name="Faso Business Club",
        )

    def test_upsert_participant(self):
        # 1. Premier enregistrement
        data = {
            "firstName": "Aïcha",
            "lastName": "Ouédraogo",
            "phone": "+226 70123456"
        }
        res = self.client.post("/participants/", data, format="json")
        self.assertEqual(res.status_code, 201)
        res_data = res.json()
        self.assertEqual(res_data["firstName"], "Aïcha")
        self.assertEqual(res_data["phone"], "+226 70123456")
        self.assertEqual(res_data["matchStatus"], "no_reference")
        participant_id = res_data["id"]

        # 2. Deuxième appel avec le même numéro (upsert)
        data_update = {
            "firstName": "Aïchatou",
            "lastName": "Ouédraogo",
            "phone": "+226 70123456"
        }
        res2 = self.client.post("/participants/", data_update, format="json")
        self.assertEqual(res2.status_code, 200)
        res2_data = res2.json()
        self.assertEqual(res2_data["id"], participant_id)
        self.assertEqual(res2_data["firstName"], "Aïchatou")

    def test_my_photos_with_phone_and_participant_id(self):
        participant = Participant.objects.create(
            first_name="Issa",
            last_name="Kaboré",
            phone="+226 78001122",
            match_status="no_reference"
        )

        # 1. Sans paramètre
        res = self.client.get(f"/events/{self.event.slug}/my-photos/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "no_reference")

        # 2. Avec paramètre phone (résout le Gap B du frontend)
        res_phone = self.client.get(f"/events/{self.event.slug}/my-photos/?phone=+226 78001122")
        self.assertEqual(res_phone.status_code, 200)
        self.assertEqual(res_phone.json()["status"], "no_reference")

        # 3. Passer en statut ready avec une photo matchée
        participant.match_status = "ready"
        participant.save()

        photo = Photo.objects.create(
            event=self.event,
            file="photos/sample.jpg",
            legend="Gala 1",
            is_public=True
        )
        PhotoMatch.objects.create(participant=participant, photo=photo)

        res_ready = self.client.get(f"/events/{self.event.slug}/my-photos/?participant={participant.id}")
        self.assertEqual(res_ready.status_code, 200)
        self.assertEqual(res_ready.json()["status"], "ready")
        self.assertEqual(len(res_ready.json()["photos"]), 1)
        self.assertEqual(res_ready.json()["photos"][0]["legend"], "Gala 1")

    def test_rgpd_deletion(self):
        import hashlib
        participant = Participant.objects.create(
            first_name="Paul",
            last_name="Sanou",
            phone="+226 65432100",
            match_status="ready"
        )
        FaceReference.objects.create(
            participant=participant,
            embedding=[0.1] * 512
        )

        # Génération du token RGPD (SHA256 du numéro de téléphone)
        rgpd_token = hashlib.sha256(participant.phone.encode()).hexdigest()

        # Vérification que sans token, la suppression est refusée (403)
        res_denied = self.client.delete(f"/participants/{participant.id}/face-reference/")
        self.assertEqual(res_denied.status_code, 403)

        # Suppression de l'embedding de référence avec token
        res_del_ref = self.client.delete(
            f"/participants/{participant.id}/face-reference/",
            HTTP_X_PARTICIPANT_TOKEN=rgpd_token
        )
        self.assertEqual(res_del_ref.status_code, 200)
        self.assertFalse(FaceReference.objects.filter(participant=participant).exists())

        participant.refresh_from_db()
        self.assertEqual(participant.match_status, "no_reference")

        # Droit à l'oubli complet avec token
        res_del_all = self.client.delete(
            f"/participants/{participant.id}/",
            HTTP_X_PARTICIPANT_TOKEN=rgpd_token
        )
        self.assertEqual(res_del_all.status_code, 200)
        self.assertFalse(Participant.objects.filter(id=participant.id).exists())

    def test_face_reference_security_validation(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        participant = Participant.objects.create(
            first_name="Sec",
            last_name="Test",
            phone="+226 79998877"
        )
        # 1. Fichier corrompu / invalide
        corrupt_file = SimpleUploadedFile("selfie.jpg", b"fake image content not valid jpeg", content_type="image/jpeg")
        res = self.client.post(f"/participants/{participant.id}/face-reference/", {"file": corrupt_file}, format="multipart")
        self.assertEqual(res.status_code, 400)
        self.assertIn("invalide", res.json().get("error", ""))

        # 2. Extension non autorisée
        bad_ext = SimpleUploadedFile("virus.exe", b"binary content", content_type="application/octet-stream")
        res2 = self.client.post(f"/participants/{participant.id}/face-reference/", {"file": bad_ext}, format="multipart")
        self.assertEqual(res2.status_code, 400)
