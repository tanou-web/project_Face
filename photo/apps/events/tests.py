from io import BytesIO
import tempfile
from django.test import TestCase
from django.test import override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from unittest.mock import patch
from PIL import Image
from apps.events.models import Event
from apps.media.models import Photo

User = get_user_model()

class EventsAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            username="admin_test",
            email="admin@clovis-dev.bf",
            password="adminpassword123"
        )
        self.event = Event.objects.create(
            slug="nuit-des-entrepreneurs",
            name="La Nuit des Entrepreneurs",
            tagline="Le grand rendez-vous",
            description="Soirée annuelle",
            city="Ouagadougou",
            venue="Hôtel Silmandé",
            date="2026-07-18",
            status="en_ligne",
            accent_color="oklch(0.578 0.221 27.5)",
            accent_text_color="oklch(0.99 0 0)",
            organizer_name="Faso Business Club",
            organizer_about="Réseau leader",
            organizer_website="https://fasobusinessclub.bf",
            organizer_phone="+226 70 11 22 33",
            highlights=["Trophées", "Dîner"]
        )
        self.photo = Photo.objects.create(
            event=self.event,
            file="photos/test.jpg",
            legend="Photo 1",
            is_public=True
        )

    def test_events_list(self):
        res = self.client.get("/events/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data), 1)
        ev = data[0]
        self.assertEqual(ev["slug"], "nuit-des-entrepreneurs")
        self.assertEqual(ev["name"], "La Nuit des Entrepreneurs")
        self.assertEqual(ev["dateLabel"], "18 juillet 2026")
        self.assertEqual(ev["theme"]["accent"], "oklch(0.578 0.221 27.5)")
        self.assertEqual(ev["organizer"]["name"], "Faso Business Club")
        self.assertEqual(ev["photosCount"], 1)

    def test_event_detail(self):
        res = self.client.get(f"/events/{self.event.slug}/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["slug"], "nuit-des-entrepreneurs")
        self.assertEqual(len(data["photos"]), 1)
        self.assertEqual(data["photos"][0]["legend"], "Photo 1")

    def test_event_photos(self):
        res = self.client.get(f"/events/{self.event.slug}/photos/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["legend"], "Photo 1")

    def test_admin_jwt_auth_with_email_and_stats(self):
        # 1. Login JWT avec email (spécification stricte: {"email": "...", "password": "..."})
        login_res = self.client.post("/auth/login/", {
            "email": "admin@clovis-dev.bf",
            "password": "adminpassword123"
        })
        self.assertEqual(login_res.status_code, 200)
        token = login_res.json()["access"]
        self.assertIn("refresh", login_res.json())

        # 2. Accès aux stats admin avec Bearer token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        stats_res = self.client.get("/admin/stats/")
        self.assertEqual(stats_res.status_code, 200)
        stats_data = stats_res.json()
        self.assertEqual(stats_data["events"], 1)
        self.assertEqual(stats_data["photos"], 1)

        # 3. Accès aux contacts admin
        contacts_res = self.client.get("/admin/contacts/")
        self.assertEqual(contacts_res.status_code, 200)

        # 4. Patch événement
        patch_res = self.client.patch(f"/events/{self.event.slug}/", {
            "venue": "Palais des Sports"
        }, format="json")
        self.assertEqual(patch_res.status_code, 200)
        self.assertEqual(patch_res.json()["venue"], "Palais des Sports")

    def test_prefix_api_v1_compatibility(self):
        # Vérifie que l'accès via /api/v1/ fonctionne identiquement
        res = self.client.get("/api/v1/events/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), 1)

    def test_swagger_schema_endpoint(self):
        # Test OpenAPI schema endpoint JSON
        res_schema = self.client.get("/api/schema/")
        self.assertEqual(res_schema.status_code, 200)
        schema_data = res_schema.data
        self.assertEqual(schema_data["info"]["title"], "Plateforme Photo Scan API")

    def test_event_list_query_efficiency(self):
        # Crée 3 événements supplémentaires
        for i in range(3):
            Event.objects.create(
                slug=f"event-{i}",
                name=f"Event {i}",
                tagline="Tagline",
                description="Desc",
                city="Ouaga",
                date="2026-07-20",
                status="en_ligne"
            )
        # Vérifie que la performance reste acceptable : 1 requête SQL principale (annotate + order_by)
        # Le test vérifie surtout l'absence de requêtes N+1
        with self.assertNumQueries(1):
            res = self.client.get("/events/")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(res.json()), 4)

    def test_photo_patch_is_public_and_legend(self):
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.patch(f"/admin/media/{self.photo.id}/", {
            "isPublic": False,
            "legend": "Photo privée VIP"
        }, format="json")
        self.assertEqual(res.status_code, 200)
        self.photo.refresh_from_db()
        self.assertFalse(self.photo.is_public)
        self.assertEqual(self.photo.legend, "Photo privée VIP")

    def _upload_photo(self):
        image_buffer = BytesIO()
        Image.new("RGB", (200, 200), color="white").save(image_buffer, format="JPEG")
        image = SimpleUploadedFile(
            "portrait.jpg",
            image_buffer.getvalue(),
            content_type="image/jpeg",
        )
        self.client.force_authenticate(user=self.admin_user)
        return self.client.post(
            f"/admin/events/{self.event.slug}/media/",
            {"files": [image]},
            format="multipart",
        )

    def test_media_upload_queues_face_indexing(self):
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            with patch("apps.media.views.index_event_photos.delay") as enqueue_index:
                response = self._upload_photo()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["received"], 1)
        self.assertEqual(response.data["indexing"], "queued")
        enqueue_index.assert_called_once()

    def test_media_upload_reports_when_indexing_queue_is_unavailable(self):
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            with patch(
                "apps.media.views.index_event_photos.delay",
                side_effect=ConnectionError("Redis is unavailable"),
            ):
                response = self._upload_photo()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["received"], 1)
        self.assertEqual(response.data["indexing"], "unavailable")
        self.assertEqual(len(response.data["indexingErrors"]), 1)

    def test_manager_can_only_invite_photographer(self):
        from apps.organizations.models import Organization, OrganizationMembership
        owner_user = User.objects.create_user(username="owner1", password="password123")
        org = Organization.objects.create(name="Studio Test", slug="studio-test", owner=owner_user)
        manager_user = User.objects.create_user(username="manager1", password="password123")
        OrganizationMembership.objects.create(organization=org, user=manager_user, role="manager")

        self.client.force_authenticate(user=manager_user)

        # 1. Manager tente d'inviter un manager -> 403 Forbidden
        res_fail = self.client.post("/admin/team/invite/", {
            "role": "manager",
            "phone": "+22670112233"
        }, format="json")
        self.assertEqual(res_fail.status_code, 403)
        self.assertIn("ne pouvez inviter que des photographes", res_fail.json().get("error", ""))

        # 2. Manager invite un photographe -> 201 Created
        res_ok = self.client.post("/admin/team/invite/", {
            "role": "photographer",
            "phone": "+22670112233"
        }, format="json")
        self.assertEqual(res_ok.status_code, 201)
        self.assertEqual(res_ok.json()["role"], "photographer")
