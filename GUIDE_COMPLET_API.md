# 📚 Guide Complet de l'API Photo Scan - Explication Détaillée

**Base URL Production** : `https://photo-scan-api-9o78.onrender.com`  
**Base URL API** : `https://photo-scan-api-9o78.onrender.com/api/v1`  
**Version** : 1.0.0

---

## 📖 Table des Matières

1. [Vue d'Ensemble du Système](#1-vue-densemble-du-système)
2. [Authentification JWT](#2-authentification-jwt)
3. [Gestion des Événements](#3-gestion-des-événements)
4. [Gestion des Participants](#4-gestion-des-participants)
5. [Reconnaissance Faciale](#5-reconnaissance-faciale)
6. [Upload de Médias](#6-upload-de-médias)
7. [Administration Multi-Tenant](#7-administration-multi-tenant)
8. [Statistiques](#8-statistiques)
9. [Gestion RGPD](#9-gestion-rgpd)
10. [Codes d'Erreur](#10-codes-derreur)

---

## 1. Vue d'Ensemble du Système

### 🎯 Concept Principal

Le système permet aux **organisateurs d'événements** de :
1. Créer un événement (mariage, gala, conférence)
2. Uploader des photos de l'événement
3. Les **participants** prennent un **selfie**
4. L'**IA détecte automatiquement** le participant sur les photos
5. Le participant reçoit **uniquement ses photos**

### 🔐 Rôles et Permissions

| Rôle | Permissions | Description |
|------|------------|-------------|
| **Superuser** | Tout | Administrateur plateforme |
| **Owner** | Gestion complète organisation | Propriétaire d'une organisation |
| **Manager** | Gestion événements + équipe | Gestionnaire d'événements |
| **Photographer** | Upload photos uniquement | Photographe prestataire |
| **Participant** | Consultation photos personnelles | Invité à un événement |

---

## 2. Authentification JWT

### 📌 Concept

L'API utilise **JWT (JSON Web Tokens)** pour l'authentification :
- **Access Token** : Valide 24h, utilisé pour les requêtes
- **Refresh Token** : Valide 7 jours, permet de renouveler l'access token

---

### 🔑 2.1 - Connexion (Login)

**Endpoint** : `POST /api/v1/auth/login/`  
**Authentification** : ❌ Aucune  
**Throttling** : 10 requêtes/minute

#### **Description**
Authentifie un utilisateur avec son **email** ou **username** et retourne deux tokens JWT.

#### **Requête**

**Headers** :
```http
Content-Type: application/json
```

**Body (Option 1 : Email)** :
```json
{
  "email": "admin@clovis-dev.bf",
  "password": "adminpassword123"
}
```

**Body (Option 2 : Username)** :
```json
{
  "username": "admin",
  "password": "adminpassword123"
}
```

#### **Réponse Succès (200 OK)**

```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### **Étapes d'Utilisation**

1. **Envoyer** email + password
2. **Récupérer** le token `access` de la réponse
3. **Sauvegarder** le token (localStorage/sessionStorage)
4. **Utiliser** le token dans toutes les requêtes suivantes :
   ```http
   Authorization: Bearer eyJhbGci...
   ```

#### **Erreurs Possibles**

| Code | Message | Cause | Solution |
|------|---------|-------|----------|
| 401 | "No active account found..." | Email/password incorrect | Vérifier identifiants |
| 400 | "Aucun compte n'est associé..." | Email n'existe pas | Vérifier l'email |
| 429 | "Request was throttled" | Trop de tentatives | Attendre 1 minute |

#### **Exemple Code Frontend**

```javascript
async function login(email, password) {
  const response = await fetch('https://photo-scan-api-9o78.onrender.com/api/v1/auth/login/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ email, password })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Échec de connexion');
  }

  const { access, refresh } = await response.json();
  
  // Sauvegarder les tokens
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);
  
  return { access, refresh };
}

// Utilisation
try {
  const tokens = await login('admin@clovis-dev.bf', 'adminpassword123');
  console.log('✅ Connecté !', tokens);
} catch (error) {
  console.error('❌ Erreur:', error.message);
}
```

---

### 🔄 2.2 - Rafraîchir le Token

**Endpoint** : `POST /api/v1/auth/refresh/`  
**Authentification** : ❌ Aucune (utilise le refresh token)

#### **Description**
Génère un **nouveau access token** à partir du refresh token sans redemander le mot de passe.

#### **Quand Utiliser ?**
- Quand l'access token expire (après 24h)
- Quand vous recevez une erreur 401 "Token expired"

#### **Requête**

**Headers** :
```http
Content-Type: application/json
```

**Body** :
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### **Réponse Succès (200 OK)**

```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

⚠️ **Important** : L'ancien refresh token est **invalidé**, utilisez le nouveau !

#### **Exemple Code Frontend**

```javascript
async function refreshToken() {
  const refreshToken = localStorage.getItem('refresh_token');
  
  const response = await fetch('https://photo-scan-api-9o78.onrender.com/api/v1/auth/refresh/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ refresh: refreshToken })
  });

  if (!response.ok) {
    // Refresh token expiré : il faut se reconnecter
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
    return;
  }

  const { access, refresh } = await response.json();
  
  // Mettre à jour les tokens
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);
  
  return access;
}
```

---

### 🔑 2.3 - Définir/Réinitialiser Mot de Passe

**Endpoint** : `POST /api/v1/auth/set-password/`  
**Authentification** : 🔑 Token d'invitation (dans l'URL)

#### **Description**
Permet à un nouveau utilisateur de définir son mot de passe après avoir reçu un lien d'invitation, ou à un utilisateur existant de réinitialiser son mot de passe.

#### **Workflow**
1. Admin crée un compte → Génère un token d'invitation
2. Utilisateur reçoit le lien par WhatsApp/Email
3. Utilisateur clique sur le lien : `https://frontend.com/auth/set-password?token=abc123`
4. Frontend envoie le token + nouveau mot de passe à cette API
5. Mot de passe défini → Utilisateur peut se connecter

#### **Requête**

**Headers** :
```http
Content-Type: application/json
```

**Body** :
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo1LCJleHAiOjE3OTQ0OTczNTl9...",
  "password": "MonNouveauMotDePasse123!"
}
```

#### **Réponse Succès (200 OK)**

```json
{
  "success": true,
  "message": "Mot de passe défini avec succès. Vous pouvez maintenant vous connecter."
}
```

**Exemple Réel** :
```json
{
  "success": true,
  "message": "Votre mot de passe a été configuré. Connectez-vous avec votre email."
}
```

#### **Erreurs**

| Code | Message | Cause | Solution |
|------|---------|-------|----------|
| 400 | "Token invalide ou expiré" | Token JWT invalide ou > 7 jours | Demander un nouveau lien |
| 400 | "Le mot de passe doit contenir..." | Mot de passe trop faible | Respecter les critères |

#### **Critères Mot de Passe**

- ✅ Au moins 8 caractères
- ✅ Au moins une majuscule
- ✅ Au moins un chiffre
- ✅ Au moins un caractère spécial (!@#$%...)

#### **Exemple Code Frontend**

```javascript
async function setPassword(token, password) {
  const response = await fetch('https://photo-scan-api-9o78.onrender.com/api/v1/auth/set-password/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ token, password })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Erreur lors de la définition du mot de passe');
  }

  return await response.json();
}

// Utilisation (dans la page /auth/set-password)
const urlParams = new URLSearchParams(window.location.search);
const token = urlParams.get('token');

if (!token) {
  alert('Lien invalide');
} else {
  const password = prompt('Entrez votre nouveau mot de passe:');
  try {
    await setPassword(token, password);
    alert('✅ Mot de passe défini ! Vous pouvez vous connecter.');
    window.location.href = '/login';
  } catch (error) {
    alert('❌ ' + error.message);
  }
}
```

---

### 👤 2.4 - Profil Utilisateur

**Endpoint** : `GET /api/v1/auth/me/`  
**Authentification** : ✅ JWT Required

#### **Description**
Récupère les informations du compte utilisateur connecté (profil, rôle, organisation).

#### **Requête**

**Headers** :
```http
Authorization: Bearer eyJhbGci...
```

#### **Réponse Succès (200 OK)**

```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@clovis-dev.bf",
  "first_name": "",
  "last_name": "",
  "is_superuser": true,
  "organization": {
    "id": 1,
    "name": "Faso Business Club",
    "slug": "faso-business-club"
  },
  "role": "owner"
}
```

#### **Utilisation**

```javascript
async function getProfile() {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch('https://photo-scan-api-9o78.onrender.com/api/v1/auth/me/', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });

  return await response.json();
}

// Utilisation
const profile = await getProfile();
console.log('Rôle:', profile.role);
console.log('Organisation:', profile.organization?.name);
```

---

## 3. Gestion des Événements

### 📌 Concept

Un **événement** représente une occasion (mariage, gala, conférence) avec :
- Des informations (nom, date, lieu)
- Des photos
- Des participants reconnus par IA

### 📊 Cycle de Vie d'un Événement

```
1. Création (status: "traitement")
   ↓
2. Upload des photos
   ↓
3. Passage en ligne (status: "en_ligne")
   ↓
4. Participants s'inscrivent et envoient selfie
   ↓
5. IA reconnaît les participants
   ↓
6. Archivage (status: "archive")
```

---

### 📋 3.1 - Liste des Événements Publics

**Endpoint** : `GET /api/v1/events/`  
**Authentification** : ❌ Aucune  
**Cache** : 60 secondes

#### **Description**
Retourne la liste de **tous les événements publics** (status = "en_ligne").

#### **Paramètres Query (Optionnels)**

| Paramètre | Type | Description | Exemple |
|-----------|------|-------------|---------|
| `org` | string | Filtrer par organisation | `?org=faso-business-club` |

#### **Requête**

```http
GET /api/v1/events/
```

ou avec filtre :

```http
GET /api/v1/events/?org=faso-business-club
```

#### **Réponse Succès (200 OK)**

```json
[
  {
    "slug": "nuit-des-entrepreneurs",
    "name": "La Nuit des Entrepreneurs",
    "tagline": "Le grand rendez-vous de l'écosystème entrepreneurial",
    "description": "Une soirée d'exception réunissant plus de 400 chefs d'entreprise...",
    "logoUrl": null,
    "city": "Ouagadougou",
    "venue": "Hôtel Silmandé",
    "date": "2026-07-18",
    "dateLabel": "18 juillet 2026",
    "status": "en_ligne",
    "cover": "https://photo-scan-api-9o78.onrender.com/media/covers/image.jpg",
    "theme": {
      "accent": "#7620df",
      "accentForeground": "oklch(0.99 0 0)"
    },
    "organizer": {
      "name": "Faso Business Club",
      "logoUrl": null,
      "about": "Le réseau leader des bâtisseurs d'entreprises...",
      "website": "https://fasobusinessclub.bf",
      "phone": "+226 70 11 22 33"
    },
    "highlights": [
      "Remise des Trophées de l'Innovation",
      "Dîner de gala prestige",
      "Networking VIP & investisseurs"
    ],
    "photos": [],
    "video": null,
    "participants": 45,
    "photosCount": 150
  }
]
```

#### **Exemple Code Frontend**

```javascript
async function getEvents(orgSlug = null) {
  const url = orgSlug 
    ? `https://photo-scan-api-9o78.onrender.com/api/v1/events/?org=${orgSlug}`
    : 'https://photo-scan-api-9o78.onrender.com/api/v1/events/';
  
  const response = await fetch(url);
  return await response.json();
}

// Utilisation
const events = await getEvents();
console.log(`${events.length} événements disponibles`);

events.forEach(event => {
  console.log(`- ${event.name} (${event.dateLabel})`);
  console.log(`  📍 ${event.city} - ${event.venue}`);
  console.log(`  📸 ${event.photosCount} photos`);
  console.log(`  👥 ${event.participants} participants`);
});
```

---

### 📄 3.2 - Détails d'un Événement

**Endpoint** : `GET /api/v1/events/{slug}/`  
**Authentification** : ❌ Aucune

#### **Description**
Récupère **tous les détails** d'un événement spécifique.

#### **Paramètres URL**

| Paramètre | Type | Description | Exemple |
|-----------|------|-------------|---------|
| `slug` | string | Identifiant unique de l'événement | `nuit-des-entrepreneurs` |

#### **Requête**

```http
GET /api/v1/events/nuit-des-entrepreneurs/
```

#### **Réponse Succès (200 OK)**

Même structure que la liste, mais pour un seul événement.

#### **Erreurs**

| Code | Message | Cause |
|------|---------|-------|
| 404 | "Not found" | Le slug n'existe pas ou l'événement n'est pas en ligne |

#### **Exemple Code Frontend**

```javascript
async function getEventDetail(slug) {
  const response = await fetch(
    `https://photo-scan-api-9o78.onrender.com/api/v1/events/${slug}/`
  );
  
  if (!response.ok) {
    throw new Error('Événement introuvable');
  }
  
  return await response.json();
}

// Utilisation
const event = await getEventDetail('nuit-des-entrepreneurs');
console.log('Événement:', event.name);
console.log('Date:', event.dateLabel);
console.log('Lieu:', `${event.city}, ${event.venue}`);
```

---

### ➕ 3.3 - Créer un Événement (Admin)

**Endpoint** : `POST /api/v1/admin/events/`  
**Authentification** : ✅ JWT Required (Owner ou Manager)  
**Throttling** : 60 requêtes/minute

#### **Description**
Crée un nouvel événement rattaché à l'organisation de l'utilisateur connecté.

#### **Requête**

**Headers** :
```http
Authorization: Bearer eyJhbGci...
Content-Type: application/json
```

**Body** :
```json
{
  "slug": "mariage-aminata-2026",
  "name": "Mariage d'Aminata & Ibrahim",
  "tagline": "Une union mémorable sous le ciel burkinabè",
  "description": "Célébration du mariage d'Aminata OUÉDRAOGO et Ibrahim TRAORÉ",
  "city": "Ouagadougou",
  "venue": "Hôtel Azalaï",
  "date": "2026-12-15",
  "status": "traitement",
  "accent_color": "oklch(0.7 0.2 350)",
  "accent_text_color": "oklch(0.99 0 0)",
  "organizer_name": "Tanou Events",
  "organizer_about": "Spécialiste des événements haut de gamme",
  "organizer_website": "https://tanou-events.bf",
  "organizer_phone": "+22670123456",
  "highlights": [
    "Cérémonie traditionnelle",
    "Buffet royal 300 personnes",
    "Animation DJ international"
  ]
}
```

#### **Champs Requis**

| Champ | Type | Description |
|-------|------|-------------|
| `slug` | string | Identifiant unique URL (sans espaces, tirets uniquement) |
| `name` | string | Nom de l'événement |
| `tagline` | string | Slogan court |
| `description` | string | Description complète |
| `city` | string | Ville |
| `venue` | string | Lieu précis |
| `date` | date | Date au format `YYYY-MM-DD` |
| `status` | string | `"traitement"`, `"en_ligne"` ou `"archive"` |
| `organizer_name` | string | Nom de l'organisateur |

#### **Champs Optionnels**

| Champ | Type | Défaut |
|-------|------|--------|
| `accent_color` | string | `"oklch(0.578 0.221 27.5)"` |
| `accent_text_color` | string | `"oklch(0.99 0 0)"` |
| `organizer_about` | string | `""` |
| `organizer_website` | url | `null` |
| `organizer_phone` | string | `null` |
| `highlights` | array | `[]` |

#### **Réponse Succès (201 Created)**

```json
{
  "slug": "mariage-aminata-2026",
  "name": "Mariage d'Aminata & Ibrahim",
  "status": "traitement",
  "dateLabel": "15 décembre 2026",
  ...
}
```

#### **Erreurs**

| Code | Message | Cause | Solution |
|------|---------|-------|----------|
| 400 | `"slug": ["event with this slug already exists"]` | Slug déjà utilisé | Changer le slug |
| 400 | `"date": ["Date has wrong format"]` | Format de date invalide | Utiliser `YYYY-MM-DD` |
| 403 | "Accès refusé : seuls les gestionnaires..." | Rôle insuffisant | Vérifier rôle (owner/manager) |
| 401 | "Authentication credentials were not provided" | Token manquant | Ajouter header Authorization |

#### **Exemple Code Frontend**

```javascript
async function createEvent(eventData) {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch('https://photo-scan-api-9o78.onrender.com/api/v1/admin/events/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(eventData)
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(JSON.stringify(error));
  }

  return await response.json();
}

// Utilisation
const newEvent = await createEvent({
  slug: 'mariage-test-' + Date.now(),
  name: 'Mon Mariage',
  tagline: 'Une journée inoubliable',
  description: 'Description complète...',
  city: 'Ouagadougou',
  venue: 'Hôtel Azalaï',
  date: '2027-06-15',
  status: 'traitement',
  organizer_name: 'Mon Organisation'
});

console.log('✅ Événement créé:', newEvent.slug);
```

---

### ✏️ 3.4 - Modifier un Événement

**Endpoint** : `PATCH /api/v1/events/{slug}/`  
**Authentification** : ✅ JWT Required (Owner ou Manager de l'événement)

#### **Description**
Modifie les informations d'un événement existant. **Modification partielle** (PATCH) : seuls les champs envoyés sont modifiés.

#### **Cas d'Usage Courants**

1. **Passer un événement en ligne** :
   ```json
   { "status": "en_ligne" }
   ```

2. **Modifier la date** :
   ```json
   { "date": "2027-01-20" }
   ```

3. **Changer plusieurs champs** :
   ```json
   {
     "name": "Nouveau Nom",
     "city": "Bobo-Dioulasso",
     "status": "en_ligne"
   }
   ```

#### **Requête**

**Headers** :
```http
Authorization: Bearer eyJhbGci...
Content-Type: application/json
```

**Body (Exemple : Passer en ligne)** :
```json
{
  "status": "en_ligne"
}
```

#### **Réponse Succès (200 OK)**

```json
{
  "slug": "mariage-aminata-2026",
  "name": "Mariage d'Aminata & Ibrahim",
  "status": "en_ligne",
  ...
}
```

#### **Exemple Code Frontend**

```javascript
async function updateEvent(slug, updates) {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(
    `https://photo-scan-api-9o78.onrender.com/api/v1/events/${slug}/`,
    {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(updates)
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(JSON.stringify(error));
  }

  return await response.json();
}

// Utilisation : Passer l'événement en ligne
await updateEvent('mariage-aminata-2026', {
  status: 'en_ligne'
});

console.log('✅ Événement maintenant public');
```

---

## 4. Gestion des Participants

### 📌 Concept

Un **participant** est une personne invitée à un événement qui s'inscrit pour récupérer ses photos via reconnaissance faciale.

### 🔄 Workflow Participant

```
1. Participant scanne QR code de l'événement
   ↓
2. Entre son numéro WhatsApp
   ↓
3. Reçoit un access_token unique
   ↓
4. Envoie un selfie de référence
   ↓
5. IA analyse le selfie (match_status: "pending")
   ↓
6. IA compare avec toutes les photos de l'événement
   ↓
7. Participant reçoit ses photos (match_status: "ready")
```

---

### 📝 4.1 - Inscription Participant

**Endpoint** : `POST /api/v1/participants/`  
**Authentification** : ❌ Aucune  
**Throttling** : 120 requêtes/minute

#### **Description**
Enregistre un nouveau participant ou récupère un participant existant (upsert) basé sur le **numéro de téléphone**.

#### **Concept Important : Upsert**

- Si le numéro **n'existe pas** → Crée un nouveau participant
- Si le numéro **existe déjà** → Retourne le participant existant avec son token

#### **Requête**

**Headers** :
```http
Content-Type: application/json
```

**Body** :
```json
{
  "firstName": "Aïcha",
  "lastName": "Ouédraogo",
  "phone": "+22670123456"
}
```

ou format local (sera normalisé automatiquement) :

```json
{
  "firstName": "Aïcha",
  "lastName": "Ouédraogo",
  "phone": "70123456"
}
```

#### **Normalisation Automatique des Numéros**

L'API normalise automatiquement les numéros burkinabés :

| Format Entré | Format Normalisé |
|--------------|------------------|
| `70123456` | `+22670123456` |
| `226 70 123 456` | `+22670123456` |
| `+226-70-123-456` | `+22670123456` |
| `0022670123456` | `+22670123456` |

#### **Réponse Succès (201 Created ou 200 OK)**

```json
{
  "id": 42,
  "firstName": "Aïcha",
  "lastName": "Ouédraogo",
  "phone": "+22670123456",
  "matchStatus": "no_reference",
  "accessToken": "xVz9K_3mP-7tQsL4nY2wF8jRbC6hNdA1gE5pU0iO"
}
```

#### **Match Status**

| Status | Description |
|--------|-------------|
| `no_reference` | Pas encore de selfie fourni |
| `pending` | Selfie reçu, analyse IA en cours |
| `ready` | Analyse terminée, photos disponibles |

⚠️ **IMPORTANT** : Sauvegardez le `accessToken` ! C'est la clé d'accès unique du participant.

#### **Erreurs**

| Code | Message | Cause | Solution |
|------|---------|-------|----------|
| 400 | "Le numéro de téléphone WhatsApp est obligatoire" | Champ `phone` manquant | Ajouter le numéro |
| 400 | "Numéro invalide" | Format incorrect | Vérifier le numéro |

#### **Exemple Code Frontend**

```javascript
async function registerParticipant(firstName, lastName, phone) {
  const response = await fetch('https://photo-scan-api-9o78.onrender.com/api/v1/participants/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ firstName, lastName, phone })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Erreur inscription');
  }

  const participant = await response.json();
  
  // ⚠️ SAUVEGARDER LE TOKEN !
  localStorage.setItem('participant_token', participant.accessToken);
  localStorage.setItem('participant_id', participant.id);
  
  return participant;
}

// Utilisation
const participant = await registerParticipant('Aïcha', 'Ouédraogo', '+22670123456');
console.log('✅ Inscrit ! Token:', participant.accessToken);
console.log('Status:', participant.matchStatus); // "no_reference"
```

---

## 5. Reconnaissance Faciale

### 📌 Concept

La **reconnaissance faciale** permet d'identifier automatiquement un participant sur les photos d'un événement.

### 🔬 Comment ça Marche ?

1. **Participant envoie un selfie** → L'IA extrait un vecteur mathématique (embedding 512D)
2. **IA analyse les photos** → Pour chaque visage détecté, extrait aussi un embedding
3. **Comparaison des embeddings** → Calcul de similarité cosinus
4. **Si similarité > 60%** → Match ! Le participant est sur cette photo
5. **Liste des photos** → Le participant reçoit uniquement les photos où il apparaît

### 🔐 Privacy by Design (RGPD)

⚠️ **IMPORTANT** : Le selfie original n'est **JAMAIS sauvegardé** !

1. Selfie reçu → Stocké temporairement en RAM
2. IA extrait l'embedding (512 nombres)
3. Selfie supprimé immédiatement
4. Seul l'embedding est sauvegardé (irréversible)

---

### 📸 5.1 - Upload Selfie de Référence

**Endpoint** : `POST /api/v1/participants/{id}/face-reference/`  
**Authentification** : 🔑 Participant Token (X-Participant-Token)  
**Throttling** : 20 requêtes/minute

#### **Description**
Upload du selfie du participant pour lancer la reconnaissance faciale.

#### **Requête**

**Headers** :
```http
X-Participant-Token: xVz9K_3mP-7tQsL4nY2wF8jRbC6hNdA1gE5pU0iO
Content-Type: multipart/form-data
```

**Body (form-data)** :
```
file: [image du selfie .jpg/.png]
```

#### **Critères de Qualité du Selfie**

✅ **Bonnes Pratiques** :
- Photo de face, bien éclairée
- Visage visible et net
- Fond neutre
- Pas de lunettes de soleil
- Taille : 500KB - 5MB

❌ **À Éviter** :
- Photos de groupe
- Visage de profil
- Mauvais éclairage
- Photo floue

#### **Réponse Succès (200 OK)**

```json
{
  "success": true,
  "message": "Selfie enregistré. Reconnaissance en cours (2-5 minutes)."
}
```

#### **Que Se Passe-t-il Après ?**

1. **Immédiatement** : `matchStatus` passe à `"pending"`
2. **En arrière-plan** : Tâche Celery lance l'analyse
3. **2-5 minutes** : IA compare avec toutes les photos
4. **Fin** : `matchStatus` passe à `"ready"`

#### **Erreurs**

| Code | Message | Cause | Solution |
|------|---------|-------|----------|
| 400 | "Aucun fichier fourni" | Pas de fichier dans la requête | Ajouter le fichier |
| 400 | "Format invalide" | Extension non supportée | Utiliser .jpg ou .png |
| 403 | "Token invalide" | Token incorrect/expiré | Vérifier le token |
| 413 | "Fichier trop volumineux" | Taille > 50MB | Compresser l'image |

#### **Exemple Code Frontend**

```javascript
async function uploadSelfie(participantId, imageFile) {
  const token = localStorage.getItem('participant_token');
  
  const formData = new FormData();
  formData.append('file', imageFile);
  
  const response = await fetch(
    `https://photo-scan-api-9o78.onrender.com/api/v1/participants/${participantId}/face-reference/`,
    {
      method: 'POST',
      headers: {
        'X-Participant-Token': token
      },
      body: formData
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Erreur upload selfie');
  }

  return await response.json();
}

// Utilisation avec un input file
const fileInput = document.getElementById('selfie-input');
fileInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  
  if (!file) return;
  
  // Vérifier la taille
  if (file.size > 5 * 1024 * 1024) { // 5MB
    alert('Fichier trop volumineux (max 5MB)');
    return;
  }
  
  try {
    const result = await uploadSelfie(42, file);
    console.log('✅', result.message);
    // Afficher un message : "Analyse en cours, revenez dans 5 minutes"
  } catch (error) {
    console.error('❌ Erreur:', error.message);
  }
});
```

---

### 📷 5.2 - Récupérer Mes Photos

**Endpoint** : `GET /api/v1/events/{slug}/my-photos/`  
**Authentification** : 🔑 Participant Token (X-Participant-Token ou ?token=...)

#### **Description**
Récupère la liste de **toutes les photos** où le participant a été reconnu par l'IA.

#### **Requête (Option 1 : Header)**

**Headers** :
```http
X-Participant-Token: xVz9K_3mP-7tQsL4nY2wF8jRbC6hNdA1gE5pU0iO
```

```http
GET /api/v1/events/nuit-des-entrepreneurs/my-photos/
```

#### **Requête (Option 2 : Query Parameter)**

```http
GET /api/v1/events/nuit-des-entrepreneurs/my-photos/?token=xVz9K_3mP-7tQsL4nY2wF8jRbC6hNdA1gE5pU0iO
```

#### **Réponse Succès (200 OK)**

**Cas 1 : Pas de selfie fourni**
```json
{
  "status": "no_reference",
  "message": "Veuillez d'abord fournir un selfie de référence.",
  "photos": []
}
```

**Cas 2 : Analyse en cours**
```json
{
  "status": "pending",
  "message": "Analyse en cours. Revenez dans quelques minutes.",
  "photos": []
}
```

**Cas 3 : Photos disponibles**
```json
{
  "status": "ready",
  "message": "12 photos trouvées",
  "photos": [
    {
      "id": 123,
      "src": "https://photo-scan-api-9o78.onrender.com/media/photos/2026/11/IMG_001.jpg",
      "thumbnail": "https://photo-scan-api-9o78.onrender.com/media/thumbs/2026/11/IMG_001.jpg",
      "legend": "Photo de groupe à l'ouverture",
      "isPublic": true
    },
    {
      "id": 124,
      "src": "https://photo-scan-api-9o78.onrender.com/media/photos/2026/11/IMG_042.jpg",
      "thumbnail": "https://photo-scan-api-9o78.onrender.com/media/thumbs/2026/11/IMG_042.jpg",
      "legend": "Cocktail VIP",
      "isPublic": true
    }
  ]
}
```

#### **Erreurs**

| Code | Message | Cause |
|------|---------|-------|
| 401 | "Token manquant" | Pas de token fourni |
| 403 | "Token invalide" | Token incorrect |
| 404 | "Événement introuvable" | Slug invalide |

#### **Exemple Code Frontend**

```javascript
async function getMyPhotos(eventSlug) {
  const token = localStorage.getItem('participant_token');
  
  const response = await fetch(
    `https://photo-scan-api-9o78.onrender.com/api/v1/events/${eventSlug}/my-photos/`,
    {
      headers: {
        'X-Participant-Token': token
      }
    }
  );

  return await response.json();
}

// Utilisation
const result = await getMyPhotos('nuit-des-entrepreneurs');

if (result.status === 'no_reference') {
  // Afficher formulaire upload selfie
  console.log('📸 Veuillez envoyer un selfie');
  
} else if (result.status === 'pending') {
  // Afficher spinner + message
  console.log('⏳ Analyse en cours...');
  
} else if (result.status === 'ready') {
  // Afficher galerie de photos
  console.log(`✅ ${result.photos.length} photos trouvées`);
  
  result.photos.forEach(photo => {
    console.log(`- Photo #${photo.id}: ${photo.legend}`);
    console.log(`  URL: ${photo.src}`);
  });
}
```

---

## 6. Upload de Médias

### 📸 6.1 - Upload Photos par Lot

**Endpoint** : `POST /api/v1/admin/events/{slug}/media/`  
**Authentification** : ✅ JWT Required (Owner, Manager ou Photographer)  
**Throttling** : 60 requêtes/minute  
**Taille max** : 50MB par photo, 100MB total par requête

#### **Description**
Upload de **plusieurs photos** simultanément pour un événement.

#### **Requête**

**Headers** :
```http
Authorization: Bearer eyJhbGci...
Content-Type: multipart/form-data
```

**Body (form-data)** :
```
files: [photo1.jpg, photo2.jpg, photo3.jpg, ...]
```

⚠️ **Important** : Le champ s'appelle `files` (pluriel) et accepte plusieurs fichiers.

#### **Processus Automatique**

Pour chaque photo :
1. ✅ Validation format (.jpg, .png, .heic)
2. ✅ Sauvegarde en haute résolution
3. ✅ Génération miniature automatique
4. ✅ **Détection faciale automatique** (IA extrait les visages)
5. ✅ Indexation pour recherche

#### **Réponse Succès (201 Created)**

```json
{
  "success": true,
  "uploaded": 3,
  "message": "3 photos uploadées avec succès"
}
```

#### **Erreurs**

| Code | Message | Cause | Solution |
|------|---------|-------|----------|
| 400 | "Aucun fichier fourni" | Champ `files` vide | Ajouter des fichiers |
| 413 | "Fichier trop volumineux" | Taille > 50MB | Compresser les images |
| 403 | "Accès refusé" | Pas d'autorisation | Vérifier rôle |

#### **Exemple Code Frontend**

```javascript
async function uploadPhotos(eventSlug, files) {
  const token = localStorage.getItem('access_token');
  
  const formData = new FormData();
  
  // Ajouter tous les fichiers
  Array.from(files).forEach(file => {
    formData.append('files', file);
  });
  
  const response = await fetch(
    `https://photo-scan-api-9o78.onrender.com/api/v1/admin/events/${eventSlug}/media/`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Erreur upload');
  }

  return await response.json();
}

// Utilisation avec input file multiple
const fileInput = document.getElementById('photos-input');
fileInput.addEventListener('change', async (e) => {
  const files = e.target.files;
  
  if (files.length === 0) return;
  
  console.log(`Upload de ${files.length} photos...`);
  
  try {
    const result = await uploadPhotos('mon-evenement', files);
    console.log('✅', result.message);
  } catch (error) {
    console.error('❌ Erreur:', error.message);
  }
});
```

---

### 🖼️ 6.2 - Upload Logo Événement

**Endpoint** : `POST /api/v1/admin/events/{slug}/logo/`  
**Authentification** : ✅ JWT Required (Owner ou Manager)

#### **Description**
Upload ou mise à jour du logo d'un événement.

#### **Requête**

**Headers** :
```http
Authorization: Bearer eyJhbGci...
Content-Type: multipart/form-data
```

**Body (form-data)** :
```
file: [logo.png]
```

#### **Formats Acceptés**

- ✅ PNG (recommandé, transparent)
- ✅ JPG/JPEG
- ✅ SVG
- ✅ WebP

#### **Taille Recommandée**

- Largeur : 200-400px
- Format : Carré ou paysage
- Poids : < 500KB

#### **Réponse Succès (200 OK)**

```json
{
  "success": true,
  "logoUrl": "https://photo-scan-api-9o78.onrender.com/media/organizers/logo_abc123.png"
}
```

#### **Exemple Code Frontend**

```javascript
async function uploadLogo(eventSlug, logoFile) {
  const token = localStorage.getItem('access_token');
  
  const formData = new FormData();
  formData.append('file', logoFile);
  
  const response = await fetch(
    `https://photo-scan-api-9o78.onrender.com/api/v1/admin/events/${eventSlug}/logo/`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData
    }
  );

  return await response.json();
}
```

---

## 7. Administration Multi-Tenant

### 📌 Concept Multi-Tenant

Le système SaaS permet à plusieurs **organisations** (clients) de coexister :
- Chaque organisation a ses propres événements
- Isolation totale des données
- Gestion d'équipe interne (owner, manager, photographer)

---

### 🏢 7.1 - Créer un Compte Client

**Endpoint** : `POST /api/v1/admin/clients/create/`  
**Authentification** : ✅ JWT Required (Superuser uniquement)

#### **Description**
Crée un nouveau compte client avec son organisation. Utilisé par l'administrateur plateforme pour onboarder de nouveaux clients.

#### **Requête**

**Headers** :
```http
Authorization: Bearer eyJhbGci...
Content-Type: application/json
```

**Body** :
```json
{
  "ownerEmail": "client@example.com",
  "ownerFirstName": "Jean",
  "ownerLastName": "Dupont",
  "ownerPhone": "+22670123456",
  "organizationName": "Studio Photo Dupont"
}
```

#### **Réponse Succès (201 Created)**

```json
{
  "success": true,
  "user": {
    "id": 5,
    "email": "client@example.com",
    "username": "client"
  },
  "organization": {
    "id": 3,
    "name": "Studio Photo Dupont",
    "slug": "studio-photo-dupont"
  },
  "invitationLink": "https://votre-frontend.com/auth/set-password?token=abc123xyz...",
  "setPasswordUrl": "https://platforme-photo-scan.onrender.com/auth/set-password?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo1LCJleHAiOjE3OTQ0OTczNTl9.xYz123",
  "whatsappMessage": "Bonjour Jean Dupont,\n\nVotre compte a été créé sur Photo Scan Platform.\n\n🔗 Définissez votre mot de passe ici :\nhttps://platforme-photo-scan.onrender.com/auth/set-password?token=eyJhbGci...\n\n📱 Numéro: +22670123456\n\nCe lien expire dans 7 jours."
}
```

**Exemple Réel** :
```json
{
  "success": true,
  "user": {
    "id": 2,
    "email": "test@example.com",
    "username": "test"
  },
  "organization": {
    "id": 2,
    "name": "Test Organization",
    "slug": "test-organization"
  },
  "setPasswordUrl": "https://platforme-photo-scan.onrender.com/auth/set-password?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoyLCJleHAiOjE3OTQ1MDIzNDV9.dGVzdF90b2tlbl9zaWduYXR1cmU",
  "whatsappMessage": "Bonjour Test User,\n\nVotre compte organisateur Photo Scan a été créé avec succès.\n\n🔐 Définissez votre mot de passe :\nhttps://platforme-photo-scan.onrender.com/auth/set-password?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...\n\n📧 Email: test@example.com\n📱 Téléphone: +22670000000\n\n⏰ Ce lien expire dans 7 jours.\n\nCordialement,\nL'équipe Photo Scan"
}
```

#### **Workflow Client**

1. Superuser crée le compte
2. Client reçoit le lien d'invitation (WhatsApp/Email)
3. Client définit son mot de passe
4. Client peut se connecter et créer des événements

---

### 👥 7.2 - Inviter un Membre d'Équipe

**Endpoint** : `POST /api/v1/admin/team/invite/`  
**Authentification** : ✅ JWT Required (Owner uniquement)

#### **Description**
Invite un nouveau membre (manager ou photographer) à rejoindre l'organisation.

#### **Requête**

**Headers** :
```http
Authorization: Bearer eyJhbGci...
Content-Type: application/json
```

**Body** :
```json
{
  "email": "photographe@example.com",
  "role": "photographer",
  "phone": "+22670987654"
}
```

#### **Rôles Disponibles**

| Rôle | Permissions |
|------|-------------|
| `manager` | Gestion événements + équipe |
| `photographer` | Upload photos uniquement |

⚠️ **Note** : Un owner ne peut pas inviter d'autre owner.

#### **Réponse Succès (201 Created)**

```json
{
  "success": true,
  "invitationLink": "https://votre-frontend.com/auth/set-password?token=def456uvw...",
  "message": "Invitation envoyée à photographe@example.com",
  "setPasswordUrl": "https://platforme-photo-scan.onrender.com/auth/set-password?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo3LCJleHAiOjE3OTQ1MDI0NTV9.aW52aXRlX3Rva2Vu",
  "whatsappMessage": "Bonjour,\n\nVous avez été invité(e) à rejoindre l'équipe de Studio Photo Dupont sur Photo Scan.\n\n🔗 Créez votre mot de passe :\nhttps://platforme-photo-scan.onrender.com/auth/set-password?token=eyJhbGci...\n\n📧 Email: photographe@example.com\n👤 Rôle: Photographe\n\n⏰ Ce lien expire dans 7 jours."
}
```

**Exemple Réel** :
```json
{
  "success": true,
  "setPasswordUrl": "https://platforme-photo-scan.onrender.com/auth/set-password?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo4LCJleHAiOjE3OTQ1MDI1MDB9.cGhvdG9ncmFwaGVyX3Rva2Vu",
  "message": "Invitation créée pour photo@test.com",
  "whatsappMessage": "Bonjour,\n\nVous êtes invité à rejoindre Test Organization en tant que Photographe.\n\n🔐 Activez votre compte ici :\nhttps://platforme-photo-scan.onrender.com/auth/set-password?token=eyJhbGci...\n\n📧 Email: photo@test.com\n\nCe lien est valable 7 jours.\n\nÀ bientôt !"
}
```

---

### 📊 7.3 - Liste des Membres

**Endpoint** : `GET /api/v1/admin/team/`  
**Authentification** : ✅ JWT Required (Owner ou Manager)

#### **Description**
Liste tous les membres de l'organisation.

#### **Réponse Succès (200 OK)**

```json
[
  {
    "id": 5,
    "email": "owner@example.com",
    "username": "owner",
    "first_name": "Jean",
    "last_name": "Dupont",
    "role": "owner"
  },
  {
    "id": 6,
    "email": "manager@example.com",
    "username": "manager",
    "first_name": "Marie",
    "last_name": "Martin",
    "role": "manager"
  },
  {
    "id": 7,
    "email": "photo@example.com",
    "username": "photo",
    "first_name": "Paul",
    "last_name": "Durant",
    "role": "photographer"
  }
]
```

---

## 8. Statistiques

### 📊 8.1 - Statistiques Organisation

**Endpoint** : `GET /api/v1/admin/stats/`  
**Authentification** : ✅ JWT Required (Owner ou Manager)

#### **Description**
Récupère les statistiques globales de l'organisation.

#### **Requête**

**Headers** :
```http
Authorization: Bearer eyJhbGci...
```

#### **Réponse Succès (200 OK)**

```json
{
  "events": 12,
  "photos": 1850,
  "participants": 340,
  "downloads": 2150
}
```

**Exemple Réel** :
```json
{
  "events": 3,
  "photos": 0,
  "participants": 0,
  "downloads": 0
}
```

#### **Explication des Métriques**

| Métrique | Description |
|----------|-------------|
| `events` | Nombre total d'événements de l'organisation |
| `photos` | Nombre total de photos uploadées |
| `participants` | Nombre de participants uniques reconnus |
| `downloads` | Nombre total de photos consultées/téléchargées |

#### **Exemple Code Frontend**

```javascript
async function getStats() {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch('https://photo-scan-api-9o78.onrender.com/api/v1/admin/stats/', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });

  return await response.json();
}

// Utilisation
const stats = await getStats();
console.log(`📊 Statistiques :`);
console.log(`  🎪 ${stats.events} événements`);
console.log(`  📸 ${stats.photos} photos`);
console.log(`  👥 ${stats.participants} participants`);
console.log(`  ⬇️  ${stats.downloads} téléchargements`);
```

---

### 📞 8.2 - Liste des Contacts Participants

**Endpoint** : `GET /api/v1/admin/contacts/`  
**Authentification** : ✅ JWT Required (Owner ou Manager)

#### **Description**
Liste de tous les participants ayant fourni un selfie, avec leurs coordonnées.

#### **Paramètres Query (Optionnels)**

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `event` | Filtrer par événement | `?event=nuit-des-entrepreneurs` |

#### **Requête**

```http
GET /api/v1/admin/contacts/
```

ou avec filtre :

```http
GET /api/v1/admin/contacts/?event=nuit-des-entrepreneurs
```

#### **Headers** :
```http
Authorization: Bearer eyJhbGci...
```

#### **Réponse Succès (200 OK)**

```json
{
  "event": "Tous les événements",
  "participants": [
    {
      "id": 42,
      "firstName": "Aïcha",
      "lastName": "Ouédraogo",
      "phone": "+22670123456",
      "hasFaceReference": true,
      "valid": true,
      "date": "05/11/2026"
    },
    {
      "id": 43,
      "firstName": "Ibrahim",
      "lastName": "Traoré",
      "phone": "+22670987654",
      "hasFaceReference": true,
      "valid": true,
      "date": "05/11/2026"
    }
  ]
}
```

**Exemple Réel (Aucun Participant)** :
```json
{
  "event": "Tous les événements",
  "participants": []
}
```

#### **Utilité**

- Export de contacts pour campagnes WhatsApp
- Statistiques de participation
- Suivi des participants ayant fourni un selfie

---

## 9. Gestion RGPD

### 🔒 Principe RGPD

Le système respecte le **Règlement Général sur la Protection des Données** :

1. **Consentement explicite** : Participant accepte lors de l'inscription
2. **Minimisation des données** : Seulement nom, prénom, numéro
3. **Privacy by Design** : Selfies jamais sauvegardés
4. **Droit à l'oubli** : Suppression totale possible
5. **Portabilité** : Export des données possible

---

### 🗑️ 9.1 - Droit à l'Oubli (Supprimer un Participant)

**Endpoint** : `DELETE /api/v1/participants/{id}/`  
**Authentification** : 🔑 Participant Token (X-Participant-Token)

#### **Description**
Supprime **définitivement et irréversiblement** toutes les données d'un participant conformément au RGPD.

#### **Ce qui est Supprimé**

1. ✅ Fiche participant (nom, prénom, téléphone)
2. ✅ Embedding facial (vecteur 512D)
3. ✅ Tous les matchs avec les photos
4. ✅ Token d'accès

#### **Ce qui est Conservé**

- ✅ Les photos de l'événement (propriété de l'organisateur)
- ✅ Les statistiques anonymisées

#### **Requête**

**Headers** :
```http
X-Participant-Token: xVz9K_3mP-7tQsL4nY2wF8jRbC6hNdA1gE5pU0iO
```

```http
DELETE /api/v1/participants/42/
```

#### **Réponse Succès (204 No Content)**

Pas de body, juste le code 204.

#### **Erreurs**

| Code | Message | Cause |
|------|---------|-------|
| 403 | "Token invalide" | Token incorrect |
| 404 | "Not found" | ID participant inexistant |

#### **Exemple Code Frontend**

```javascript
async function deleteMyAccount(participantId) {
  const token = localStorage.getItem('participant_token');
  
  const confirmation = confirm(
    '⚠️ Êtes-vous sûr de vouloir supprimer votre compte ?\n\n' +
    'Cette action est IRRÉVERSIBLE et supprimera :\n' +
    '- Vos informations personnelles\n' +
    '- Votre reconnaissance faciale\n' +
    '- L\'accès à vos photos\n\n' +
    'Les photos de l\'événement resteront propriété de l\'organisateur.'
  );
  
  if (!confirmation) return;
  
  const response = await fetch(
    `https://photo-scan-api-9o78.onrender.com/api/v1/participants/${participantId}/`,
    {
      method: 'DELETE',
      headers: {
        'X-Participant-Token': token
      }
    }
  );

  if (response.status === 204) {
    // Suppression réussie
    localStorage.removeItem('participant_token');
    localStorage.removeItem('participant_id');
    console.log('✅ Compte supprimé définitivement');
    window.location.href = '/';
  } else {
    const error = await response.json();
    throw new Error(error.detail || 'Erreur suppression');
  }
}

// Utilisation
await deleteMyAccount(42);
```

---

## 10. Codes d'Erreur

### 📋 Liste Complète des Codes HTTP

| Code | Nom | Signification |
|------|-----|---------------|
| 200 | OK | Requête réussie |
| 201 | Created | Ressource créée |
| 204 | No Content | Suppression réussie |
| 400 | Bad Request | Données invalides |
| 401 | Unauthorized | Non authentifié |
| 403 | Forbidden | Accès refusé |
| 404 | Not Found | Ressource introuvable |
| 413 | Payload Too Large | Fichier trop volumineux |
| 429 | Too Many Requests | Rate limit dépassé |
| 500 | Internal Server Error | Erreur serveur |

---

### ❌ Format des Erreurs

Toutes les erreurs retournent un JSON :

```json
{
  "detail": "Message d'erreur explicite"
}
```

ou pour les erreurs de validation :

```json
{
  "email": ["Aucun compte n'est associé à cette adresse email."],
  "date": ["Date has wrong format. Use one of these formats instead: YYYY-MM-DD."]
}
```

---

### 🛡️ Gestion des Erreurs Frontend

```javascript
async function apiCall(url, options = {}) {
  try {
    const response = await fetch(url, options);
    
    if (!response.ok) {
      // Gérer les différents codes d'erreur
      if (response.status === 401) {
        // Token expiré : rafraîchir ou reconnecter
        const newToken = await refreshToken();
        if (newToken) {
          // Réessayer la requête avec le nouveau token
          options.headers['Authorization'] = `Bearer ${newToken}`;
          return await fetch(url, options);
        } else {
          // Rediriger vers login
          window.location.href = '/login';
          return;
        }
      }
      
      if (response.status === 429) {
        // Rate limit : attendre et réessayer
        await new Promise(resolve => setTimeout(resolve, 60000)); // 1 minute
        return await fetch(url, options);
      }
      
      if (response.status === 403) {
        // Accès refusé
        throw new Error('Vous n\'avez pas les droits pour cette action');
      }
      
      if (response.status === 404) {
        throw new Error('Ressource introuvable');
      }
      
      // Autres erreurs
      const error = await response.json();
      throw new Error(error.detail || JSON.stringify(error));
    }
    
    return await response.json();
    
  } catch (error) {
    console.error('Erreur API:', error);
    throw error;
  }
}
```

---

## 📚 Résumé des Endpoints

### 🔓 Endpoints Publics (Sans Authentification)

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/auth/login/` | POST | Connexion |
| `/auth/refresh/` | POST | Rafraîchir token |
| `/events/` | GET | Liste événements publics |
| `/events/{slug}/` | GET | Détails événement |
| `/events/{slug}/photos/` | GET | Photos publiques |
| `/participants/` | POST | Inscription participant |

### 🔐 Endpoints Admin (JWT Required)

| Endpoint | Méthode | Rôle | Description |
|----------|---------|------|-------------|
| `/auth/me/` | GET | Tous | Profil utilisateur |
| `/admin/events/` | GET | Owner/Manager | Liste événements org |
| `/admin/events/` | POST | Owner/Manager | Créer événement |
| `/events/{slug}/` | PATCH | Owner/Manager | Modifier événement |
| `/admin/events/{slug}/media/` | POST | Tous | Upload photos |
| `/admin/events/{slug}/logo/` | POST | Owner/Manager | Upload logo |
| `/admin/stats/` | GET | Owner/Manager | Statistiques |
| `/admin/contacts/` | GET | Owner/Manager | Liste contacts |
| `/admin/team/` | GET | Owner/Manager | Liste équipe |
| `/admin/team/invite/` | POST | Owner | Inviter membre |

### 🔑 Endpoints Participants (Participant Token)

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/participants/{id}/face-reference/` | POST | Upload selfie |
| `/events/{slug}/my-photos/` | GET | Mes photos |
| `/participants/{id}/` | DELETE | Supprimer compte |

---

## 🎓 Guides Pratiques

### 🚀 Guide Rapide : Créer un Événement

```javascript
// 1. Se connecter
const { access } = await login('admin@clovis-dev.bf', 'adminpassword123');

// 2. Créer l'événement
const event = await createEvent({
  slug: 'mon-evenement-' + Date.now(),
  name: 'Mon Événement',
  tagline: 'Un événement incroyable',
  description: 'Description complète',
  city: 'Ouagadougou',
  venue: 'Centre',
  date: '2027-06-15',
  status: 'traitement',
  organizer_name: 'Mon Org'
});

// 3. Upload photos
await uploadPhotos(event.slug, filesArray);

// 4. Passer en ligne
await updateEvent(event.slug, { status: 'en_ligne' });

console.log(`✅ Événement créé et publié : ${event.slug}`);
```

---

### 👤 Guide Rapide : Parcours Participant

```javascript
// 1. Inscription
const participant = await registerParticipant('Aïcha', 'Ouédraogo', '+22670123456');
localStorage.setItem('participant_token', participant.accessToken);

// 2. Upload selfie
await uploadSelfie(participant.id, selfieFile);
console.log('⏳ Analyse en cours...');

// 3. Attendre 2-5 minutes puis récupérer les photos
await new Promise(resolve => setTimeout(resolve, 300000)); // 5 min

// 4. Consulter mes photos
const result = await getMyPhotos('nuit-des-entrepreneurs');
if (result.status === 'ready') {
  console.log(`✅ ${result.photos.length} photos trouvées !`);
  result.photos.forEach(photo => {
    console.log(`📸 ${photo.legend}: ${photo.src}`);
  });
}
```

---

## 🔗 Liens Utiles

- **Swagger UI** : `https://photo-scan-api-9o78.onrender.com/api/docs/`
- **ReDoc** : `https://photo-scan-api-9o78.onrender.com/api/redoc/`
- **Schéma OpenAPI** : `https://photo-scan-api-9o78.onrender.com/api/schema/`

---

## ✅ Cette Documentation Est-Elle à Jour ?

**Oui ! ✅** Mise à jour : 05/11/2026

Tous les bugs ont été corrigés :
- ✅ AdminStatsView fonctionne avec comptes clients
- ✅ AdminContactsView fonctionne avec comptes clients
- ✅ Upload logo fonctionne avec comptes clients
- ✅ Login avec email inconnu retourne 400 au lieu de 500
- ✅ POST participants avec firstName null géré correctement
- ✅ URLs en HTTPS (SECURE_PROXY_SSL_HEADER ajouté)
- ✅ Médias servis même en production (DEBUG=False)

---

**Version** : 1.1.0  
**Date** : 05 novembre 2026  
**Auteur** : Documentation générée pour l'équipe frontend
