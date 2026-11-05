# 🚀 Guide Postman - Test API Photo Scan

## 🔑 Identifiants Admin

```
Email    : admin@clovis-dev.bf
Password : adminpassword123
```

---

## 📋 Collection de Requêtes Postman

### **1️⃣ LOGIN - Obtenir le Token JWT**

**URL** : `https://photo-scan-api-9o78.onrender.com/api/v1/auth/login/`  
**Méthode** : `POST`  
**Headers** :
```
Content-Type: application/json
```

**Body (JSON)** :
```json
{
  "email": "admin@clovis-dev.bf",
  "password": "adminpassword123"
}
```

**Réponse Attendue** :
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

⚠️ **IMPORTANT** : Copiez le token `access` pour les requêtes suivantes !

---

### **2️⃣ LISTER LES ÉVÉNEMENTS (PUBLIC)**

**URL** : `https://photo-scan-api-9o78.onrender.com/api/v1/events/`  
**Méthode** : `GET`  
**Headers** : Aucun (public)

**Résultat** : Liste des événements avec statut `"en_ligne"` uniquement

---

### **3️⃣ LISTER TOUS LES ÉVÉNEMENTS (ADMIN)**

**URL** : `https://photo-scan-api-9o78.onrender.com/api/v1/admin/events/`  
**Méthode** : `GET`  
**Headers** :
```
Authorization: Bearer VOTRE_TOKEN_ICI
```

**Résultat** : Tous les événements (traitement, en_ligne, archive)

---

### **4️⃣ CRÉER UN ÉVÉNEMENT**

**URL** : `https://photo-scan-api-9o78.onrender.com/api/v1/admin/events/`  
**Méthode** : `POST`  
**Headers** :
```
Authorization: Bearer VOTRE_TOKEN_ICI
Content-Type: application/json
```

**Body (JSON)** - Exemple Complet :
```json
{
  "slug": "mariage-aminata-2026",
  "name": "Mariage d'Aminata & Ibrahim",
  "tagline": "Une union mémorable sous le ciel burkinabè",
  "description": "Célébration du mariage d'Aminata OUÉDRAOGO et Ibrahim TRAORÉ, entourés de leurs familles et amis.",
  "city": "Ouagadougou",
  "venue": "Hôtel Azalaï",
  "date": "2026-12-15",
  "status": "traitement",
  "accent_color": "oklch(0.7 0.2 350)",
  "accent_text_color": "oklch(0.99 0 0)",
  "organizer_name": "Tanou Events",
  "organizer_about": "Spécialiste des événements haut de gamme au Burkina Faso",
  "organizer_website": "https://tanou-events.bf",
  "organizer_phone": "+22670123456",
  "highlights": [
    "Cérémonie traditionnelle",
    "Buffet royal 300 personnes",
    "Animation DJ international"
  ]
}
```

**Body (JSON)** - Exemple Minimal (champs requis seulement) :
```json
{
  "slug": "test-postman-2026",
  "name": "Test Postman",
  "tagline": "Test depuis Postman",
  "description": "Événement de test créé avec Postman",
  "city": "Ouagadougou",
  "venue": "Test Venue",
  "date": "2026-12-25",
  "status": "traitement",
  "organizer_name": "Organisateur Test"
}
```

**Réponse Succès (201 Created)** :
```json
{
  "slug": "mariage-aminata-2026",
  "name": "Mariage d'Aminata & Ibrahim",
  "status": "traitement",
  "dateLabel": "15 décembre 2026",
  ...
}
```

---

### **5️⃣ VOIR DÉTAILS D'UN ÉVÉNEMENT**

**URL** : `https://photo-scan-api-9o78.onrender.com/api/v1/events/mariage-aminata-2026/`  
**Méthode** : `GET`  
**Headers** : Aucun (public si status = "en_ligne")

---

### **6️⃣ MODIFIER UN ÉVÉNEMENT (Passer en ligne)**

**URL** : `https://photo-scan-api-9o78.onrender.com/api/v1/events/mariage-aminata-2026/`  
**Méthode** : `PATCH`  
**Headers** :
```
Authorization: Bearer VOTRE_TOKEN_ICI
Content-Type: application/json
```

**Body (JSON)** - Changer le statut :
```json
{
  "status": "en_ligne"
}
```

**Body (JSON)** - Modifier plusieurs champs :
```json
{
  "status": "en_ligne",
  "name": "Mariage d'Aminata & Ibrahim - Édition 2026",
  "date": "2026-12-20",
  "city": "Bobo-Dioulasso"
}
```

---

### **7️⃣ RAFRAÎCHIR LE TOKEN**

**URL** : `https://photo-scan-api-9o78.onrender.com/api/v1/auth/refresh/`  
**Méthode** : `POST`  
**Headers** :
```
Content-Type: application/json
```

**Body (JSON)** :
```json
{
  "refresh": "VOTRE_REFRESH_TOKEN_ICI"
}
```

**Réponse** :
```json
{
  "access": "NOUVEAU_ACCESS_TOKEN",
  "refresh": "NOUVEAU_REFRESH_TOKEN"
}
```

---

### **8️⃣ PROFIL UTILISATEUR**

**URL** : `https://photo-scan-api-9o78.onrender.com/api/v1/auth/me/`  
**Méthode** : `GET`  
**Headers** :
```
Authorization: Bearer VOTRE_TOKEN_ICI
```

**Réponse** :
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@clovis-dev.bf",
  "is_superuser": true
}
```

---

### **9️⃣ UPLOAD PHOTOS (Lot)**

**URL** : `https://photo-scan-api-9o78.onrender.com/api/v1/admin/events/mariage-aminata-2026/media/`  
**Méthode** : `POST`  
**Headers** :
```
Authorization: Bearer VOTRE_TOKEN_ICI
```

**Body (form-data)** :
```
files: [Sélectionner plusieurs fichiers .jpg]
```

Dans Postman :
1. Allez dans l'onglet **Body**
2. Sélectionnez **form-data**
3. Key : `files` (changez en **File** au lieu de **Text**)
4. Value : Cliquez "Select Files" et choisissez plusieurs images

---

### **🔟 STATISTIQUES ORGANISATION**

**URL** : `https://photo-scan-api-9o78.onrender.com/api/v1/admin/stats/`  
**Méthode** : `GET`  
**Headers** :
```
Authorization: Bearer VOTRE_TOKEN_ICI
```

**Réponse** :
```json
{
  "total_events": 3,
  "total_photos": 125,
  "total_participants": 45,
  "events_by_status": {
    "en_ligne": 2,
    "traitement": 1
  }
}
```

---

## 🎯 Workflow de Test Complet

### **Scénario : Créer et publier un événement**

```
1. LOGIN (Requête #1)
   → Récupérer le token "access"
   
2. CRÉER ÉVÉNEMENT (Requête #4)
   → Status : "traitement"
   → Copier le "slug" retourné
   
3. VÉRIFIER CRÉATION (Requête #3)
   → Lister tous les événements admin
   → Votre événement doit apparaître
   
4. MODIFIER STATUT (Requête #6)
   → Changer status → "en_ligne"
   
5. VÉRIFIER PUBLIC (Requête #2)
   → Lister événements publics
   → Votre événement est maintenant visible !
```

---

## 🛠️ Configuration Postman

### **Variables d'Environnement (Recommandé)**

Créez un environnement Postman avec ces variables :

| Variable | Valeur |
|----------|--------|
| `base_url` | `https://photo-scan-api-9o78.onrender.com/api/v1` |
| `access_token` | `<laissez vide, sera rempli après login>` |
| `refresh_token` | `<laissez vide, sera rempli après login>` |

Ensuite utilisez dans vos requêtes :
- URL : `{{base_url}}/events/`
- Header : `Authorization: Bearer {{access_token}}`

### **Script Post-Login (Automatiser la sauvegarde du token)**

Dans la requête LOGIN, allez dans l'onglet **Tests** et ajoutez :

```javascript
// Sauvegarder automatiquement le token dans les variables
if (pm.response.code === 200) {
    const response = pm.response.json();
    pm.environment.set("access_token", response.access);
    pm.environment.set("refresh_token", response.refresh);
    console.log("✅ Token sauvegardé !");
}
```

---

## ❌ Erreurs Courantes

### **401 Unauthorized**
```json
{
  "detail": "Authentication credentials were not provided."
}
```
→ Vérifiez le header `Authorization: Bearer TOKEN`

---

### **403 Forbidden**
```json
{
  "detail": "Accès refusé : seuls les gestionnaires..."
}
```
→ Votre compte n'a pas les droits (doit être owner/manager)

---

### **400 Bad Request - Slug déjà existant**
```json
{
  "slug": ["event with this slug already exists."]
}
```
→ Changez le slug (doit être unique)

---

### **400 Bad Request - Champ manquant**
```json
{
  "date": ["This field is required."]
}
```
→ Ajoutez tous les champs obligatoires

---

## 📥 Importer dans Postman

### **Option 1 : Créer manuellement**
Suivez les requêtes ci-dessus

### **Option 2 : Utiliser Swagger**
Allez sur : `https://photo-scan-api-9o78.onrender.com/api/docs/`
Postman peut importer depuis OpenAPI !

---

## 🧪 Tests Rapides

### **Test 1 : Le backend répond-il ?**
```
GET https://photo-scan-api-9o78.onrender.com/api/v1/events/
Status attendu : 200 OK
```

### **Test 2 : Puis-je me connecter ?**
```
POST /auth/login/ avec les identifiants
Status attendu : 200 OK + tokens
```

### **Test 3 : Puis-je créer un événement ?**
```
POST /admin/events/ avec token
Status attendu : 201 Created
```

---

## 📝 Checklist

- [ ] J'ai créé une collection Postman "Photo Scan API"
- [ ] J'ai testé le login et récupéré le token
- [ ] J'ai créé un événement de test
- [ ] J'ai modifié le statut en "en_ligne"
- [ ] J'ai vérifié qu'il apparaît publiquement
- [ ] J'ai testé l'upload de photos

---

## 🎉 Bon Test !

Si vous rencontrez des erreurs, copiez le message exact et je vous aiderai !
