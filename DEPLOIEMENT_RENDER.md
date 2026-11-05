# 🚀 Guide de Déploiement sur Render

## Étape 1 : Préparer les Changements

### 1.1 - Vérifier les Fichiers Modifiés

```bash
cd c:\Users\DELL\Projet
git status
```

**Fichiers modifiés** :
- ✅ `photo/apps/events/models.py` (génération slug)
- ✅ `photo/apps/events/serializers.py` (slug optionnel)
- ✅ `photo/apps/events/admin_views.py` (bugs corrigés)
- ✅ `photo/apps/events/auth_serializers.py` (email validation)
- ✅ `photo/apps/participants/views.py` (firstName null)
- ✅ `photo/photo/settings.py` (SECURE_PROXY_SSL_HEADER, médias)
- ✅ `photo/photo/urls.py` (médias en production)

**Fichiers créés** :
- ✅ Migrations (0005_alter_event...)
- ✅ `fix_empty_slugs.py` (commande correction)
- ✅ Documentation mise à jour

---

## Étape 2 : Commit et Push

### 2.1 - Ajouter Tous les Changements

```bash
git add .
```

### 2.2 - Créer le Commit

```bash
git commit -m "fix: Corrections production - slugs auto, migrations, médias persistants

- Génération automatique des slugs depuis le nom (évite slugs vides)
- Correction bugs admin (stats, contacts, logo) avec get_user_organization()
- Correction login email inconnu (ValidationError au lieu de 500)
- Correction participants firstName null
- SECURE_PROXY_SSL_HEADER pour URLs HTTPS
- Médias servis en production (DEBUG=False)
- Migrations générées (events, media, organizations)
- Commande fix_empty_slugs pour corriger slugs existants
- Documentation API enrichie avec exemples réels"
```

### 2.3 - Pousser sur GitHub

```bash
git push origin main
```

ou si votre branche est différente :

```bash
git push origin master
```

---

## Étape 3 : Render Redéploie Automatiquement

### 3.1 - Vérifier le Déploiement

1. **Aller sur** : https://dashboard.render.com
2. **Sélectionner** votre service backend
3. **Onglet "Events"** : Vous verrez "Deploy started"
4. **Attendre** 5-10 minutes

### 3.2 - Suivre les Logs

Cliquez sur le déploiement en cours pour voir les logs en temps réel :

```
==> Cloning from https://github.com/...
==> Running build command: ./photo/build.sh
==> Installation des dépendances Python...
==> Collecte des fichiers statiques pour WhiteNoise...
==> Application des migrations de base de données...
Running migrations:
  Applying events.0005_alter_event_options_alter_event_city_and_more... OK
  Applying media.0003_alter_faceindex_options_alter_photo_options_and_more... OK
  Applying organizations.0003_alter_organization_is_active_alter_organization_name... OK
==> Injection des données de démonstration initiales (seed_data)...
✅ Build terminé avec succès !
==> Starting service...
```

---

## Étape 4 : Ajouter Variables d'Environnement

### 4.1 - Aller dans Environment

1. **Dashboard Render** → Votre service backend
2. **Onglet "Environment"**
3. **Cliquer "Add Environment Variable"**

### 4.2 - Ajouter FRONTEND_URL

```
Key: FRONTEND_URL
Value: https://platforme-photo-scan.onrender.com
```

**Cliquer "Save Changes"** → Render redéploiera automatiquement

### 4.3 - Vérifier les Autres Variables

Assurez-vous que ces variables existent :

```env
✅ DJANGO_SECRET_KEY=...
✅ DJANGO_DEBUG=False
✅ DJANGO_ALLOWED_HOSTS=photo-scan-api-9o78.onrender.com
✅ DATABASE_URL=postgresql://... (auto par Render PostgreSQL)
✅ FRONTEND_URL=https://platforme-photo-scan.onrender.com (⚠️ À AJOUTER)
```

---

## Étape 5 : Corriger les Slugs Vides (Une Fois)

### 5.1 - Accéder au Shell Render

**Option A : Via Dashboard**
1. Render Dashboard → Votre service
2. Onglet "Shell"
3. Cliquer "Launch Shell"

**Option B : Via Render CLI**
```bash
render shell
```

### 5.2 - Exécuter la Commande de Correction

```bash
cd photo
python manage.py fix_empty_slugs
```

**Résultat Attendu** :
```
🔍 Trouvé 2 événement(s) avec slug vide
✅ Événement 'DEMS' (ID: 2): '(vide)' → 'dems'
✅ Événement 'Test Événement' (ID: 3): '' → 'test-evenement'

🎉 2 événement(s) corrigé(s) avec succès !
```

Si aucun slug vide :
```
✅ Aucun événement avec slug vide trouvé
```

---

## Étape 6 : Tests de Validation

### 6.1 - Test Backend Accessible

Ouvrez dans votre navigateur :
```
https://photo-scan-api-9o78.onrender.com/api/v1/events/
```

✅ **Attendu** : Liste JSON des événements  
❌ **Si erreur 500** : Voir logs Render

### 6.2 - Test Création Événement Sans Slug

Dans Postman :

```http
POST https://photo-scan-api-9o78.onrender.com/api/v1/admin/events/
Authorization: Bearer VOTRE_TOKEN
Content-Type: application/json

{
  "name": "Test Slug Auto",
  "city": "Ouagadougou",
  "venue": "Test",
  "date": "2027-06-15",
  "organizer_name": "Test Org"
}
```

✅ **Attendu** : Réponse avec `"slug": "test-slug-auto"`  
❌ **Si slug vide** : Problème avec la méthode save()

### 6.3 - Test URL d'Invitation

Créez une invitation d'équipe et vérifiez que `setPasswordUrl` commence par :
```
✅ https://platforme-photo-scan.onrender.com/auth/set-password?token=...
❌ Pas http:// ni None
```

### 6.4 - Test Médias

1. Uploadez une photo
2. Vérifiez l'URL retournée :
   ```
   ⚠️ Si local: /media/photos/2026/11/photo.jpg
   ✅ Après R2: https://xxxxx.r2.cloudflarestorage.com/.../photo.jpg
   ```

---

## Étape 7 : Configuration R2 (Recommandé)

### 7.1 - Créer Compte Cloudflare

1. Aller sur https://dash.cloudflare.com/sign-up
2. Créer un compte gratuit
3. Aller dans **R2** : https://dash.cloudflare.com/?to=/:account/r2

### 7.2 - Créer Bucket

1. Cliquer **"Create bucket"**
2. Nom : `photo-scan-media`
3. Région : Automatic
4. Cliquer **"Create bucket"**

### 7.3 - Créer API Token

1. **"Manage R2 API Tokens"**
2. **"Create API Token"**
3. Nom : `photo-scan-backend`
4. Permissions : **Read & Write**
5. **"Create API Token"**
6. ⚠️ **COPIER** Access Key ID et Secret Access Key (affiché une seule fois !)

### 7.4 - Récupérer Endpoint URL

Dans les détails du bucket, copier l'**Endpoint URL** :
```
https://xxxxxxxxxxxxx.r2.cloudflarestorage.com
```

### 7.5 - Modifier requirements.txt

Ajoutez dans `photo/requirements.txt` :

```
django-storages>=1.14
boto3>=1.28
```

### 7.6 - Modifier settings.py

Ajoutez à la fin de `photo/photo/settings.py` :

```python
# ==============================================================================
# STOCKAGE PERMANENT DES MÉDIAS (Cloudflare R2)
# ==============================================================================
if os.environ.get('USE_R2', 'False').lower() == 'true':
    # Configuration Cloudflare R2
    AWS_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME')
    AWS_S3_ENDPOINT_URL = os.environ.get('R2_ENDPOINT_URL')
    
    AWS_S3_REGION_NAME = 'auto'
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    
    # Utiliser R2 pour les médias
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    
    # URL publique des médias
    MEDIA_URL = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/"
```

### 7.7 - Commit et Push

```bash
git add photo/requirements.txt photo/photo/settings.py
git commit -m "feat: Configuration Cloudflare R2 pour stockage permanent des médias"
git push origin main
```

### 7.8 - Ajouter Variables Render

Dans Render Dashboard → Environment :

```env
USE_R2=True
R2_ACCESS_KEY_ID=votre_access_key_id
R2_SECRET_ACCESS_KEY=votre_secret_access_key
R2_BUCKET_NAME=photo-scan-media
R2_ENDPOINT_URL=https://xxxxx.r2.cloudflarestorage.com
```

**Save Changes** → Render redéploiera

### 7.9 - Tester R2

1. Uploadez une nouvelle photo
2. Vérifiez que l'URL commence par R2
3. Redéployez l'app
4. Vérifiez que la photo est toujours accessible ✅

---

## Étape 8 : Vérification Finale

### Checklist Complète

- [x] Code poussé sur GitHub
- [x] Render a redéployé automatiquement
- [x] Migrations appliquées (visible dans logs)
- [x] Variable `FRONTEND_URL` ajoutée
- [x] Commande `fix_empty_slugs` exécutée
- [ ] R2 configuré (optionnel mais recommandé)
- [ ] Tests validés :
  - [ ] Backend accessible
  - [ ] Création événement sans slug fonctionne
  - [ ] URLs HTTPS dans invitations
  - [ ] Médias persistants (si R2)

---

## 🆘 Dépannage

### Erreur 500 Après Déploiement

1. **Voir les logs** : Render Dashboard → Logs
2. **Rechercher** : "ERROR" ou "Traceback"
3. **Erreur courante** : Migration échouée
   ```bash
   # Dans Render Shell
   cd photo
   python manage.py migrate --fake-initial
   ```

### Migrations Non Appliquées

```bash
# Dans Render Shell
cd photo
python manage.py migrate
```

### Variables d'Environnement Non Prises en Compte

1. Vérifier qu'elles sont bien ajoutées dans Render Dashboard
2. Sauvegarder → Redéploiement automatique
3. Attendre 5-10 minutes

### R2 : "Unable to locate credentials"

1. Vérifier que toutes les 4 variables R2 sont définies
2. Vérifier qu'il n'y a pas d'espaces dans les valeurs
3. Redéployer après ajout

### Slugs Toujours Vides

1. Vérifier que le code est bien poussé :
   ```bash
   git log --oneline -1
   # Devrait montrer le commit récent
   ```
2. Vérifier que Render a bien redéployé
3. Re-exécuter `fix_empty_slugs`

---

## 📊 Résumé Temps Estimé

| Étape | Durée | Priorité |
|-------|-------|----------|
| 1-2. Commit et Push | 5 min | 🔴 Haute |
| 3. Déploiement Render | 5-10 min | 🔴 Haute (automatique) |
| 4. Variables Render | 2 min | 🔴 Haute |
| 5. fix_empty_slugs | 2 min | 🔴 Haute |
| 6. Tests | 5 min | 🔴 Haute |
| 7. Configuration R2 | 15-20 min | 🟡 Moyenne (recommandé) |
| 8. Vérification | 5 min | 🔴 Haute |

**Total sans R2** : ~20-25 minutes  
**Total avec R2** : ~35-45 minutes

---

## ✅ Félicitations !

Une fois toutes ces étapes complétées :

🎉 **Votre système est prêt pour production !**

- ✅ Slugs générés automatiquement
- ✅ Tous les bugs corrigés
- ✅ Migrations à jour
- ✅ URLs en HTTPS
- ✅ Documentation complète
- ✅ (Optionnel) Médias persistants avec R2

**Support** : Consultez les autres guides pour plus de détails :
- `CORRECTIONS_FINALES.md` - Résumé des corrections
- `STOCKAGE_PERMANENT.md` - Guide complet R2/Cloudinary
- `BUGS_CORRIGES.md` - Liste des 5 bugs corrigés
- `GUIDE_COMPLET_API.md` - Documentation API complète
