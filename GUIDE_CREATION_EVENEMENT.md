# 🔐 Guide : Créer un Événement via l'API Django

## 🚨 Problème Rencontré

Lorsque vous essayez de créer un événement depuis le frontend, vous recevez une erreur **401 Unauthorized** ou **403 Forbidden** car l'endpoint `POST /api/v1/admin/events/` nécessite :

1. ✅ **Authentification JWT** (Bearer Token)
2. ✅ **Être membre d'une organisation**
3. ✅ **Avoir le rôle `owner` ou `manager`** (pas `photographer`)

---

## 📋 Étapes pour Créer un Événement

### **Étape 1 : Se Connecter et Obtenir le Token JWT**

```bash
POST https://photo-scan-api-9o78.onrender.com/api/v1/auth/login/
Content-Type: application/json

{
  "email": "admin@example.com",
  "password": "votre_mot_de_passe"
}
```

**Réponse :**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

⚠️ **Sauvegardez le token `access`** : c'est votre clé d'authentification !

---

### **Étape 2 : Créer l'Événement**

```bash
POST https://photo-scan-api-9o78.onrender.com/api/v1/admin/events/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
Content-Type: application/json

{
  "slug": "mariage-aminata-2026",
  "name": "Mariage d'Aminata & Ibrahim",
  "tagline": "Une union mémorable",
  "description": "La célébration du mariage d'Aminata et Ibrahim au Burkina Faso",
  "city": "Ouagadougou",
  "venue": "Hôtel Azalaï",
  "date": "2026-12-15",
  "status": "traitement",
  "accent_color": "oklch(0.578 0.221 27.5)",
  "accent_text_color": "oklch(0.99 0 0)",
  "organizer_name": "Tanou Events",
  "organizer_about": "Organisateur professionnel d'événements",
  "organizer_website": "https://tanou-events.bf",
  "organizer_phone": "+22670123456",
  "highlights": ["Cérémonie traditionnelle", "Buffet royal", "Animation DJ"]
}
```

**Réponse Succès (201 Created) :**
```json
{
  "slug": "mariage-aminata-2026",
  "name": "Mariage d'Aminata & Ibrahim",
  "status": "traitement",
  ...
}
```

---

## 🔴 Erreurs Courantes

### **1. Erreur 401 Unauthorized**

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Cause** : Le header `Authorization` est manquant ou invalide.

**Solution** :
```javascript
headers: {
  "Authorization": `Bearer ${accessToken}`,
  "Content-Type": "application/json"
}
```

---

### **2. Erreur 403 Forbidden**

```json
{
  "detail": "Accès refusé : seuls les gestionnaires et propriétaires peuvent créer un événement."
}
```

**Cause** : Votre compte a le rôle `photographer` au lieu de `owner` ou `manager`.

**Solution** : Demandez à un administrateur de vous promouvoir au rôle `manager`.

---

### **3. Erreur 400 Bad Request - Champ manquant**

```json
{
  "slug": ["This field is required."],
  "name": ["This field is required."]
}
```

**Cause** : Des champs obligatoires sont manquants.

**Champs obligatoires** :
- `slug` (unique, sans espaces, ex: `mariage-aminata-2026`)
- `name`
- `city`
- `venue`
- `date` (format `YYYY-MM-DD`)
- `organizer_name`

---

### **4. Erreur 400 Bad Request - Slug dupliqué**

```json
{
  "slug": ["event with this slug already exists."]
}
```

**Cause** : Un événement avec ce slug existe déjà.

**Solution** : Choisissez un slug unique (ajoutez un numéro, une date, etc.).

---

## 💻 Code Frontend (React/TypeScript)

### **1. Service API d'Authentification**

```typescript
// services/auth.ts
const BASE_URL = "https://photo-scan-api-9o78.onrender.com/api/v1";

export async function login(email: string, password: string) {
  const response = await fetch(`${BASE_URL}/auth/login/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ email, password })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Échec de connexion");
  }

  const data = await response.json();
  // Sauvegarder le token
  localStorage.setItem("access_token", data.access);
  localStorage.setItem("refresh_token", data.refresh);
  
  return data;
}

export function getAccessToken(): string | null {
  return localStorage.getItem("access_token");
}

export function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}
```

---

### **2. Service API de Création d'Événement**

```typescript
// services/events.ts
const BASE_URL = "https://photo-scan-api-9o78.onrender.com/api/v1";

interface CreateEventPayload {
  slug: string;
  name: string;
  tagline: string;
  description: string;
  city: string;
  venue: string;
  date: string; // Format: "YYYY-MM-DD"
  status: "traitement" | "en_ligne" | "archive";
  accent_color?: string;
  accent_text_color?: string;
  organizer_name: string;
  organizer_about?: string;
  organizer_website?: string;
  organizer_phone?: string;
  highlights?: string[];
}

export async function createEvent(payload: CreateEventPayload) {
  const accessToken = localStorage.getItem("access_token");
  
  if (!accessToken) {
    throw new Error("Non authentifié. Veuillez vous connecter.");
  }

  const response = await fetch(`${BASE_URL}/admin/events/`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${accessToken}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const error = await response.json();
    
    // Gestion spécifique des erreurs
    if (response.status === 401) {
      // Token expiré ou invalide
      localStorage.removeItem("access_token");
      throw new Error("Session expirée. Reconnectez-vous.");
    }
    
    if (response.status === 403) {
      throw new Error("Vous n'avez pas les droits pour créer un événement.");
    }
    
    // Erreurs de validation
    throw new Error(JSON.stringify(error));
  }

  return await response.json();
}
```

---

### **3. Composant React de Création d'Événement**

```tsx
// components/CreateEventForm.tsx
import { useState } from "react";
import { createEvent } from "../services/events";

export function CreateEventForm() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    const formData = new FormData(e.currentTarget);
    
    try {
      const event = await createEvent({
        slug: formData.get("slug") as string,
        name: formData.get("name") as string,
        tagline: formData.get("tagline") as string,
        description: formData.get("description") as string,
        city: formData.get("city") as string,
        venue: formData.get("venue") as string,
        date: formData.get("date") as string,
        status: "traitement",
        organizer_name: formData.get("organizer_name") as string,
        organizer_phone: formData.get("organizer_phone") as string,
        highlights: []
      });
      
      alert(`✅ Événement créé : ${event.name}`);
      // Redirection ou autre action
      
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <h2>Créer un Événement</h2>
      
      {error && (
        <div style={{ color: "red", padding: "10px", background: "#ffebee" }}>
          ❌ {error}
        </div>
      )}
      
      <input name="slug" placeholder="Slug (ex: mariage-2026)" required />
      <input name="name" placeholder="Nom de l'événement" required />
      <input name="tagline" placeholder="Slogan" required />
      <textarea name="description" placeholder="Description" required />
      <input name="city" placeholder="Ville" required />
      <input name="venue" placeholder="Lieu" required />
      <input name="date" type="date" required />
      <input name="organizer_name" placeholder="Nom organisateur" required />
      <input name="organizer_phone" placeholder="Téléphone (+226...)" />
      
      <button type="submit" disabled={loading}>
        {loading ? "Création..." : "Créer l'événement"}
      </button>
    </form>
  );
}
```

---

## 🧪 Test avec cURL (Terminal)

### **1. Login**
```bash
curl -X POST https://photo-scan-api-9o78.onrender.com/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password123"}'
```

### **2. Créer un événement (remplacez YOUR_TOKEN)**
```bash
curl -X POST https://photo-scan-api-9o78.onrender.com/api/v1/admin/events/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "test-event-2026",
    "name": "Test Événement",
    "tagline": "Un test",
    "description": "Description test",
    "city": "Ouagadougou",
    "venue": "Test Venue",
    "date": "2026-12-20",
    "status": "traitement",
    "organizer_name": "Organisateur Test"
  }'
```

---

## 🔑 Récapitulatif

### **Pour créer un événement, il faut :**

1. ✅ **Avoir un compte utilisateur** dans Django
2. ✅ **Être membre d'une organisation**
3. ✅ **Avoir le rôle `owner` ou `manager`**
4. ✅ **Se connecter** via `/auth/login/` pour obtenir le JWT
5. ✅ **Envoyer le token** dans le header `Authorization: Bearer <token>`
6. ✅ **Appeler** `POST /api/v1/admin/events/` avec les données requises

---

## ❓ Questions Fréquentes

### **Q : Comment créer le premier compte administrateur ?**

Utilisez Django Admin ou la commande shell :
```python
python manage.py createsuperuser
```

### **Q : Comment créer une organisation ?**

Via l'interface Django Admin (`/django-admin/`) ou via code :
```python
from apps.organizations.models import Organization, OrganizationMember
from django.contrib.auth.models import User

org = Organization.objects.create(name="Mon Organisation", slug="mon-org")
OrganizationMember.objects.create(organization=org, user=user, role="owner")
```

### **Q : Mon token expire rapidement, que faire ?**

Utilisez le **refresh token** pour obtenir un nouveau `access token` :
```bash
POST /api/v1/auth/refresh/
Content-Type: application/json

{
  "refresh": "eyJ0eXAiOiJKV1QiLCJh..."
}
```

---

**Besoin d'aide ?** Vérifiez les logs du backend Django ou la console navigateur (F12) pour voir l'erreur exacte.
