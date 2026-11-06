# Tests de Production - Vérification des Corrections

## Prérequis
- URL Backend : `https://photo-scan-api-9o78.onrender.com/api/v1`
- Credentials Admin : 
  - Email: `admin@clovis-dev.bf`
  - Password: `adminpassword123`

---

## 1️⃣ Test Login + Obtenir Token

```bash
POST https://photo-scan-api-9o78.onrender.com/api/v1/auth/login/
Content-Type: application/json

{
  "email": "admin@clovis-dev.bf",
  "password": "adminpassword123"
}
```

**Résultat attendu :** 200 OK avec `access` et `refresh` tokens

**Copier le token `access`** pour les tests suivants.

---

## 2️⃣ BUG #1 CORRIGÉ : GET /admin/stats/ (user.organization)

**Avant :** 500 Internal Server Error - AttributeError: 'User' object has no attribute 'organization'

```bash
GET https://photo-scan-api-9o78.onrender.com/api/v1/admin/stats/
Authorization: Bearer <VOTRE_TOKEN>
```

**Résultat attendu :** 200 OK
```json
{
  "totalEvents": 0,
  "upcomingEvents": 0,
  "pastEvents": 0,
  "ongoingEvents": 0,
  "totalParticipants": 0,
  "totalPhotos": 0
}
```

---

## 3️⃣ BUG #2 CORRIGÉ : GET /admin/contacts/ (user.organization)

**Avant :** 500 Internal Server Error - AttributeError

```bash
GET https://photo-scan-api-9o78.onrender.com/api/v1/admin/contacts/
Authorization: Bearer <VOTRE_TOKEN>
```

**Résultat attendu :** 200 OK avec liste des contacts

---

## 4️⃣ BUG #3 CORRIGÉ : Création d'événement SANS slug (auto-génération)

**Avant :** Slug vide accepté, causait des problèmes de routing

```bash
POST https://photo-scan-api-9o78.onrender.com/api/v1/admin/events/
Authorization: Bearer <VOTRE_TOKEN>
Content-Type: application/json

{
  "name": "Test Auto Slug Production",
  "dateDebut": "2024-12-25T10:00:00Z",
  "dateFin": "2024-12-25T18:00:00Z",
  "city": "Ouagadougou",
  "status": "upcoming"
}
```

**Résultat attendu :** 201 Created avec un slug auto-généré
```json
{
  "id": "...",
  "slug": "test-auto-slug-production-abc123",
  "name": "Test Auto Slug Production",
  ...
}
```

**Vérifier que :** Le champ `slug` est généré automatiquement et n'est pas vide.

---

## 5️⃣ BUG #4 CORRIGÉ : Login avec email inconnu (ValidationError)

**Avant :** 500 Internal Server Error - KeyError: 'username'

```bash
POST https://photo-scan-api-9o78.onrender.com/api/v1/auth/login/
Content-Type: application/json

{
  "email": "utilisateur_inexistant_xyz@example.com",
  "password": "nimportequoi"
}
```

**Résultat attendu :** 400 Bad Request (PAS 500)
```json
{
  "email": [
    "Aucun utilisateur trouvé avec cet email."
  ]
}
```

---

## 6️⃣ BUG #5 CORRIGÉ : Participant avec firstName null (None.strip())

**Avant :** 500 Internal Server Error - AttributeError: 'NoneType' object has no attribute 'strip'

D'abord, créer un événement valide (ou utiliser un slug existant) :

```bash
POST https://photo-scan-api-9o78.onrender.com/api/v1/participants/
Content-Type: application/json

{
  "eventSlug": "test-auto-slug-production-abc123",
  "email": "participant_test@example.com",
  "firstName": null,
  "lastName": "TestNull"
}
```

**Résultat attendu :** 201 Created (PAS 500)
```json
{
  "id": "...",
  "firstName": "",
  "lastName": "TestNull",
  "email": "participant_test@example.com",
  ...
}
```

**Vérifier que :** `firstName` est une chaîne vide `""` et non `null`.

---

## 7️⃣ Test Upload Logo Événement (Bug #3 admin_views.py)

**Avant :** 500 Internal Server Error lors de l'upload

```bash
POST https://photo-scan-api-9o78.onrender.com/api/v1/admin/events/test-auto-slug-production-abc123/logo/
Authorization: Bearer <VOTRE_TOKEN>
Content-Type: multipart/form-data

# Dans Postman :
# - Method: POST
# - Body: form-data
# - Key: "logo" (type: File)
# - Value: Sélectionner une image JPG/PNG
```

**Résultat attendu :** 200 OK avec URL du logo

---

## ✅ Checklist de Vérification

Après avoir exécuté tous les tests ci-dessus :

- [ ] Login fonctionne (token obtenu)
- [ ] `/admin/stats/` retourne 200 au lieu de 500
- [ ] `/admin/contacts/` retourne 200 au lieu de 500
- [ ] Création d'événement sans slug génère automatiquement un slug
- [ ] Login avec email inconnu retourne 400 au lieu de 500
- [ ] Création de participant avec `firstName: null` retourne 201 au lieu de 500
- [ ] Upload de logo événement fonctionne
- [ ] Variable `FRONTEND_URL` configurée sur Render
- [ ] Commande `fix_empty_slugs` exécutée sur Render Shell

---

## 🎯 Résumé des Corrections

| Bug | Avant | Après | Fichier Corrigé |
|-----|-------|-------|-----------------|
| #1 | 500 sur `/admin/stats/` | 200 OK | `admin_views.py:60` |
| #2 | 500 sur `/admin/contacts/` | 200 OK | `admin_views.py:119` |
| #3 | 500 sur upload logo | 200 OK | `admin_views.py:170` |
| #4 | 500 sur login email inconnu | 400 Bad Request | `auth_serializers.py:13` |
| #5 | 500 sur participant firstName null | 201 Created | `views.py:251` |
| Bonus | Slug vide ou manuel | Auto-généré | `models.py:43-67` |

---

## 📱 Tests Frontend (après backend validé)

Une fois tous les tests backend validés, tester l'intégration frontend :

1. Ouvrir : https://platforme-photo-scan.onrender.com
2. Se connecter avec : `admin@clovis-dev.bf` / `adminpassword123`
3. Créer un événement SANS remplir le champ slug (si présent)
4. Vérifier que l'événement est créé et accessible
5. Uploader une photo de couverture
6. Créer un participant avec prénom vide

---

## 🆘 En cas de problème

Si un test échoue :

1. **Vérifier les logs Render** :
   - Dashboard → Service → Logs
   - Chercher les erreurs 500 ou tracebacks

2. **Vérifier les migrations** :
   ```bash
   # Dans Render Shell
   cd photo
   python manage.py showmigrations
   ```
   Toutes les migrations doivent avoir un `[X]`.

3. **Vérifier les variables d'environnement** :
   - Dashboard → Service → Environment
   - Confirmer que `FRONTEND_URL` existe

4. **Relancer les migrations** (si nécessaire) :
   ```bash
   cd photo
   python manage.py migrate
   ```

---

## 📊 Métriques de Succès

**Avant corrections :**
- 5 endpoints retournaient 500 errors
- Slug vide causait des problèmes de routing
- Aucune validation sur emails inconnus

**Après corrections :**
- ✅ Tous les endpoints retournent les codes HTTP appropriés
- ✅ Auto-génération des slugs avec gestion des collisions
- ✅ ValidationError explicite pour emails inconnus
- ✅ Protection contre valeurs null dans les formulaires
- ✅ Configuration HTTPS pour production (Render)

---

**Date de validation :** _________________

**Testé par :** _________________

**Résultat :** ✅ Tous les tests passent | ⚠️ Problèmes détectés
