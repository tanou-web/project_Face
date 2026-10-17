from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
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
