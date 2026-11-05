# 📚 Documentation API - Photo Scan Platform

**Version**: 1.0.0  
**Base URL Production**: `https://photo-scan-api-9o78.onrender.com`  
**Base URL Locale**: `http://localhost:8000`

---

## 🔗 Liens Rapides

- **Swagger UI** : `/api/docs/` ou `/swagger/`
- **ReDoc** : `/api/redoc/`
- **Schéma OpenAPI** : `/api/schema/`
- **Fichiers**: 
  - [`openapi-schema.json`](./photo/openapi-schema.json)
  - [`openapi-schema.yml`](./photo/openapi-schema.yml)

---

## 🌐 Structure des URLs

Tous les endpoints sont disponibles avec **deux préfixes** :

1. ✅ **`/api/v1/`** - Recommandé (versionné)
2. 🔄 **`/`** - Rétrocompatibilité

**Exemple** :
- `/api/v1/events/` ✅
- `/events/` ✅ (rétrocompatible)

---

## 🔐 Authentification

### JWT (JSON Web Token)

```http
Authorization: Bearer {access_token}
```

### Obtenir un token

```http
POST /api/v1/auth/login/
Content-Type: application/json

{
  "email": "admin@example.com",
  "password": "votre_mot_de_passe"
}
```

**Réponse** :
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Rafraîchir un token

```http
POST /api/v1/auth/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

## 📋 Endpoints Principaux

### 1️⃣ Authentification & Profil

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| `POST` | `/api/v1/auth/login/` | Connexion JWT | ❌ |
| `POST` | `/api/v1/auth/refresh/` | Rafraîchir token | ❌ |
| `GET` | `/api/v1/auth/me/` | Profil utilisateur | ✅ |
| `POST` | `/api/v1/auth/set-password/` | Définir mot de passe (lien d'invitation) | ❌ |

---

### 2️⃣ Événements (Public)

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| `GET` | `/api/v1/events/` | Liste des événements publics | ❌ |
| `GET` | `/api/v1/events/{slug}/` | Détails d'un événement | ❌ |
| `GET` | `/api/v1/events/{slug}/photos/` | Photos publiques de l'événement | ❌ |
| `GET` | `/api/v1/events/{slug}/my-photos/` | Photos reconnues d'un participant | 🔑 Token |

#### Exemple : Liste des événements

```http
GET /api/v1/events/
```

**Réponse** :
```json
[
  {
    "slug": "nuit-des-entrepreneurs",
    "name": "Nuit des Entrepreneurs",
    "tagline": "Une soirée exceptionnelle",
    "description": "...",
    "logoUrl": "https://.../logo.jpg",
    "city": "Ouagadougou",
    "venue": "Hôtel Azalaï",
    "date": "2026-11-15",
    "dateLabel": "15 novembre 2026",
    "status": "en_ligne",
    "cover": "https://.../cover.jpg",
    "theme": {
      "accent": "oklch(0.578 0.221 27.5)",
      "accentForeground": "oklch(0.99 0 0)"
    },
    "photosCount": 150,
    "participants": 45
  }
]
```

#### Exemple : Photos d'un participant

```http
GET /api/v1/events/nuit-des-entrepreneurs/my-photos/
X-Participant-Token: abc123xyz456
```

**ou avec query parameter** :
```http
GET /api/v1/events/nuit-des-entrepreneurs/my-photos/?token=abc123xyz456
```

**Réponse** :
```json
{
  "status": "ready",
  "photos": [
    {
      "id": "123",
      "src": "https://.../photo1.jpg",
      "legend": "Photo de groupe",
      "isPublic": true
    }
  ]
}
```

**Status possibles** :
- `no_reference` : Pas de selfie fourni
- `pending` : Traitement IA en cours
- `ready` : Photos disponibles

---

### 3️⃣ Participants & RGPD

| Méthode | Endpoint | Description | Auth |
|---------|----------|-------------|------|
| `POST` | `/api/v1/participants/` | Enregistrer un participant | ❌ |
| `POST` | `/api/v1/participants/{id}/face-reference/` | Upload selfie de référence | 🔑 Token |
| `DELETE` | `/api/v1/participants/{id}/` | Droit à l'oubli (RGPD) | 🔑 Token |

#### Exemple : Enregistrement participant

```http
POST /api/v1/participants/
Content-Type: application/json

{
  "phone": "+22670123456",
  "event_slug": "nuit-des-entrepreneurs"
}
```

**Réponse** :
```json
{
  "id": 42,
  "access_token": "abc123xyz456",
  "phone": "+22670123456",
  "match_status": "no_reference"
}
```

⚠️ **Sauvegarder le `access_token` côté frontend !**

#### Exemple : Upload selfie

```http
POST /api/v1/participants/42/face-reference/
X-Participant-Token: abc123xyz456
Content-Type: multipart/form-data

file: [image_file.jpg]
```

---

### 4️⃣ Administration (Authentification requise)

| Méthode | Endpoint | Description | Rôle |
|---------|----------|-------------|------|
| `GET` | `/api/v1/admin/events/` | Liste événements de l'organisation | owner, manager |
| `PATCH` | `/api/v1/events/{slug}/` | ⚠️ **MODIFIÉ** - Modifier un événement | owner, manager |
| `POST` | `/api/v1/admin/events/{slug}/media/` | Upload photos par lot | owner, manager |
| `POST` | `/api/v1/admin/events/{slug}/logo/` | Upload logo événement | owner, manager |
| `DELETE` | `/api/v1/admin/media/{id}/` | Supprimer une photo | owner, manager |
| `GET` | `/api/v1/admin/stats/` | Statistiques organisation | owner, manager |
| `GET` | `/api/v1/admin/contacts/` | Liste contacts participants | owner, manager |

#### ⚠️ **NOUVEAU : Modification d'événement avec validation**

```http
PATCH /api/v1/events/nuit-des-entrepreneurs/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "Nuit des Entrepreneurs 2026",
  "date": "2026-11-20",
  "status": "en_ligne",
  "tagline": "Nouvelle édition",
  "description": "Description mise à jour",
  "city": "Ouagadougou",
  "venue": "Centre de Conférences",
  "accent_color": "oklch(0.6 0.2 30)",
  "accent_text_color": "oklch(0.99 0 0)",
  "organizer_name": "Tanou Events",
  "organizer_about": "Organisateur professionnel",
  "organizer_website": "https://tanou-events.com",
  "organizer_phone": "+22670123456",
  "highlights": ["Networking", "Conférences", "Buffet"]
}
```

✅ **Changements** :
- Le champ `date` est maintenant **validé correctement** (format `YYYY-MM-DD`)
- Retourne une erreur 400 avec détails si validation échoue
- Tous les champs sont **optionnels** (PATCH partiel)

**Erreur de validation (400)** :
```json
{
  "date": ["Date has wrong format. Use one of these formats instead: YYYY-MM-DD."],
  "status": ["\"invalide\" is not a valid choice."]
}
```

#### Exemple : Upload photos par lot

```http
POST /api/v1/admin/events/nuit-des-entrepreneurs/media/
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

files: [photo1.jpg, photo2.jpg, photo3.jpg]
```

---

### 5️⃣ Gestion Multi-tenant (SaaS)

| Méthode | Endpoint | Description | Rôle |
|---------|----------|-------------|------|
| `POST` | `/api/v1/admin/clients/create/` | Créer un compte client + organisation | superuser |
| `GET` | `/api/v1/admin/team/` | Liste membres de l'équipe | owner, manager |
| `POST` | `/api/v1/admin/team/invite/` | Inviter un collaborateur | owner |
| `DELETE` | `/api/v1/admin/team/{id}/` | Retirer un membre | owner |

---

## 🎨 Thèmes & Couleurs

Les événements supportent des **couleurs d'accent personnalisées** au format **OKLCH** :

```json
{
  "theme": {
    "accent": "oklch(0.578 0.221 27.5)",
    "accentForeground": "oklch(0.99 0 0)"
  }
}
```

**Utilisation CSS** :
```css
:root {
  --accent: oklch(0.578 0.221 27.5);
  --accent-foreground: oklch(0.99 0 0);
}
```

---

## 🚦 Codes de Statut HTTP

| Code | Description |
|------|-------------|
| `200` | Succès |
| `201` | Création réussie |
| `400` | ⚠️ **Erreur de validation** (champs manquants/invalides) |
| `401` | Non authentifié |
| `403` | Non autorisé (rôle insuffisant) |
| `404` | Ressource non trouvée |
| `429` | Rate limit dépassé |
| `500` | Erreur serveur |

---

## 🔒 Sécurité

### Rate Limiting (Throttling)

| Scope | Limite |
|-------|--------|
| `anon` | 120 req/min |
| `user` | 300 req/min |
| `auth` | 10 req/min (login) |
| `face_upload` | 20 req/min |
| `admin_media` | 60 req/min |

### Headers CORS

```http
Access-Control-Allow-Origin: *
Access-Control-Allow-Credentials: true
Access-Control-Allow-Headers: authorization, content-type, x-participant-token
```

---

## 📦 Modèles de Données

### Event (Événement)

```typescript
interface Event {
  slug: string;
  name: string;
  tagline: string;
  description: string;
  logoUrl: string | null;
  cover: string | null;
  city: string;
  venue: string;
  date: string; // Format: "YYYY-MM-DD"
  dateLabel: string; // Format: "15 novembre 2026"
  status: "en_ligne" | "traitement" | "archive";
  theme: {
    accent: string; // OKLCH color
    accentForeground: string;
  };
  organizer: {
    name: string;
    logoUrl: string | null;
    about: string;
    website: string | null;
    phone: string | null;
  };
  highlights: string[];
  photos: Photo[];
  video: Video | null;
  participants: number;
  photosCount: number;
}
```

### Participant

```typescript
interface Participant {
  id: number;
  access_token: string; // À sauvegarder côté client
  phone: string;
  match_status: "no_reference" | "pending" | "ready";
}
```

### Photo

```typescript
interface Photo {
  id: string;
  src: string; // URL absolue
  legend: string;
  isPublic: boolean;
}
```

---

## 🛠️ Exemples d'Intégration Frontend

### React / Next.js

```typescript
// api/events.ts
const BASE_URL = "https://photo-scan-api-9o78.onrender.com/api/v1";

export async function getEvents() {
  const res = await fetch(`${BASE_URL}/events/`);
  if (!res.ok) throw new Error("Failed to fetch events");
  return res.json();
}

export async function getEventDetail(slug: string) {
  const res = await fetch(`${BASE_URL}/events/${slug}/`);
  if (!res.ok) throw new Error("Event not found");
  return res.json();
}

export async function getMyPhotos(slug: string, token: string) {
  const res = await fetch(`${BASE_URL}/events/${slug}/my-photos/`, {
    headers: {
      "X-Participant-Token": token
    }
  });
  return res.json();
}

export async function updateEvent(slug: string, data: Partial<Event>, accessToken: string) {
  const res = await fetch(`${BASE_URL}/events/${slug}/`, {
    method: "PATCH",
    headers: {
      "Authorization": `Bearer ${accessToken}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(data)
  });
  
  if (!res.ok) {
    const error = await res.json();
    throw new Error(JSON.stringify(error));
  }
  
  return res.json();
}
```

### Vue / Nuxt

```typescript
// composables/useApi.ts
export const useApi = () => {
  const config = useRuntimeConfig();
  const baseUrl = config.public.apiBase;

  const getEvents = async () => {
    return await $fetch(`${baseUrl}/events/`);
  };

  const updateEvent = async (slug: string, data: any, token: string) => {
    return await $fetch(`${baseUrl}/events/${slug}/`, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${token}`
      },
      body: data
    });
  };

  return { getEvents, updateEvent };
};
```

---

## 🧪 Tests avec cURL

### Login
```bash
curl -X POST https://photo-scan-api-9o78.onrender.com/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password123"}'
```

### Modifier un événement
```bash
curl -X PATCH https://photo-scan-api-9o78.onrender.com/api/v1/events/nuit-des-entrepreneurs/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Nouveau nom",
    "date": "2026-12-01",
    "status": "en_ligne"
  }'
```

---

## 📌 Notes Importantes

1. ⚠️ **Format des dates** : Toujours `YYYY-MM-DD` (ISO 8601)
2. 🔑 **Token participant** : Sauvegarder localement (localStorage/sessionStorage)
3. 🎨 **Couleurs OKLCH** : Format moderne, meilleur que HSL/RGB
4. 🌍 **CORS** : Configuré pour localhost:5173-5175 et production
5. 📱 **WhatsApp** : Les numéros doivent inclure l'indicatif (+226)

---

## 🆘 Support

- **Issues GitHub** : [tanou-web/project_Face](https://github.com/tanou-web/project_Face/issues)
- **Documentation interactive** : [/api/docs/](https://photo-scan-api-9o78.onrender.com/api/docs/)

---

**Dernière mise à jour** : 2026-11-04  
**Version API** : 1.0.0
