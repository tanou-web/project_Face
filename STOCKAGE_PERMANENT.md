# 📦 Guide : Stockage Permanent des Médias (Photos & Logos)

## ⚠️ Problème Actuel

Sur **Render Gratuit**, le système de fichiers est **éphémère** :
- ✅ Les photos uploadées fonctionnent
- ❌ **Mais sont supprimées à chaque redéploiement !**
- ❌ **Disparaissent aussi après 7 jours d'inactivité** (hibernation)

### Ce Qui Est Perdu

```
media/
├── photos/          ← Toutes les photos événements
├── organizers/      ← Logos organisateurs
├── covers/          ← Couvertures événements
└── thumbs/          ← Miniatures générées
```

---

## ✅ Solutions Recommandées

### **Option 1 : Cloudflare R2 (Gratuit 10GB)** ⭐ RECOMMANDÉ

**Avantages** :
- ✅ 10 GB gratuits
- ✅ Pas de frais de sortie (egress)
- ✅ Compatible S3 (boto3)
- ✅ CDN intégré ultra-rapide
- ✅ Pas de limite de requêtes

**Prix** :
- Gratuit jusqu'à 10 GB
- Ensuite : $0.015/GB/mois

**Installation** :

```bash
# 1. Installer le package
pip install django-storages boto3

# 2. Ajouter à requirements.txt
echo "django-storages>=1.14" >> requirements.txt
echo "boto3>=1.28" >> requirements.txt
```

**Configuration Django (settings.py)** :

```python
# Ajouter dans INSTALLED_APPS
INSTALLED_APPS = [
    ...
    'storages',
]

# Configuration R2
if not DEBUG or os.environ.get('USE_R2', 'False').lower() == 'true':
    # Cloudflare R2
    AWS_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME')
    AWS_S3_ENDPOINT_URL = os.environ.get('R2_ENDPOINT_URL')  # https://xxxxx.r2.cloudflarestorage.com
    
    AWS_S3_REGION_NAME = 'auto'
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    
    # Utiliser R2 pour les médias
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    
    # URL publique
    MEDIA_URL = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/"
```

**Variables d'Environnement Render** :

```env
USE_R2=True
R2_ACCESS_KEY_ID=votre_access_key_id
R2_SECRET_ACCESS_KEY=votre_secret_access_key
R2_BUCKET_NAME=photo-scan-media
R2_ENDPOINT_URL=https://xxxxx.r2.cloudflarestorage.com
```

**Étapes de Configuration R2** :

1. **Créer un compte Cloudflare** : https://dash.cloudflare.com/sign-up
2. **Aller dans R2** : https://dash.cloudflare.com/?to=/:account/r2
3. **Créer un bucket** : `photo-scan-media`
4. **Créer une API Token** :
   - Aller dans "Manage R2 API Tokens"
   - "Create API Token"
   - Permissions : Read & Write
   - Copier Access Key ID et Secret Access Key
5. **Récupérer l'Endpoint URL** : Affiché dans les détails du bucket

---

### **Option 2 : Cloudinary (Gratuit 25GB)** 

**Avantages** :
- ✅ 25 GB gratuits
- ✅ Optimisation d'images automatique
- ✅ Transformations à la volée
- ✅ CDN global
- ✅ Interface simple

**Prix** :
- Gratuit jusqu'à 25 GB
- 25 000 transformations/mois

**Installation** :

```bash
pip install django-cloudinary-storage
```

**Configuration Django (settings.py)** :

```python
INSTALLED_APPS = [
    ...
    'cloudinary_storage',
    'cloudinary',
]

# Configuration Cloudinary
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY'),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET'),
}

if not DEBUG:
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
```

**Variables d'Environnement Render** :

```env
CLOUDINARY_CLOUD_NAME=votre_cloud_name
CLOUDINARY_API_KEY=votre_api_key
CLOUDINARY_API_SECRET=votre_api_secret
```

**Étapes** :

1. Créer un compte : https://cloudinary.com/users/register/free
2. Copier les identifiants depuis le Dashboard
3. Ajouter les variables sur Render

---

### **Option 3 : AWS S3 (Payant mais Scalable)**

**Avantages** :
- ✅ Scalabilité illimitée
- ✅ Très fiable (99.999999999%)
- ✅ Intégration avec autres services AWS

**Prix** :
- $0.023/GB/mois (stockage)
- $0.09/GB (transfert sortant)

**Installation** : Identique à R2 (boto3)

**Configuration** :

```python
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_BUCKET_NAME')
AWS_S3_REGION_NAME = 'us-east-1'

DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
```

---

## 📊 Comparaison des Solutions

| Critère | R2 ⭐ | Cloudinary | AWS S3 |
|---------|-------|------------|--------|
| **Gratuit** | 10 GB | 25 GB | Non |
| **Prix** | $0.015/GB | $0/25GB | $0.023/GB |
| **Egress** | Gratuit | Gratuit | Payant |
| **Simplicité** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Optimisation Images** | ❌ | ✅ | Avec Lambda |
| **CDN** | ✅ Inclus | ✅ Inclus | Payant (CloudFront) |

---

## 🚀 Migration des Médias Existants

Une fois le stockage configuré, migrez les médias existants :

```bash
# Script de migration (à exécuter une fois)
python manage.py shell

from apps.media.models import Photo
from apps.events.models import Event
from django.core.files.storage import default_storage

# Ré-upload toutes les photos vers R2/Cloudinary
for photo in Photo.objects.all():
    if photo.file:
        # Django va automatiquement uploader vers le nouveau storage
        photo.save()
```

---

## ⚙️ Configuration Render Complète

### **Build Command** (build.sh)

Pas de changement nécessaire :

```bash
#!/usr/bin/env bash
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

if [ -f "manage.py" ]; then
    python manage.py collectstatic --noinput
    python manage.py migrate
    python manage.py seed_data
elif [ -f "photo/manage.py" ]; then
    python photo/manage.py collectstatic --noinput
    python photo/manage.py migrate
    python photo/manage.py seed_data
fi
```

### **Start Command**

```bash
cd photo && gunicorn photo.wsgi:application
```

### **Environment Variables (R2 Example)**

```env
# Django Core
DJANGO_SECRET_KEY=votre-clé-secrète
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=photo-scan-api-9o78.onrender.com

# Base de Données (Auto par Render PostgreSQL)
DATABASE_URL=postgresql://...

# Frontend
FRONTEND_URL=https://platforme-photo-scan.onrender.com

# Stockage R2
USE_R2=True
R2_ACCESS_KEY_ID=xxxxxxxxxxxx
R2_SECRET_ACCESS_KEY=yyyyyyyyyyyy
R2_BUCKET_NAME=photo-scan-media
R2_ENDPOINT_URL=https://xxxxx.r2.cloudflarestorage.com

# Celery/Redis (Optionnel)
CELERY_BROKER_URL=redis://...
```

---

## ✅ Vérification Post-Installation

Après configuration, testez :

```python
# Dans Django shell
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

# Test d'upload
content = ContentFile(b"Test content")
path = default_storage.save('test.txt', content)
print(f"✅ Fichier sauvegardé : {path}")

# Test d'URL
url = default_storage.url(path)
print(f"✅ URL publique : {url}")

# Test de suppression
default_storage.delete(path)
print(f"✅ Fichier supprimé")
```

Si tout fonctionne, vous verrez des URLs R2/Cloudinary au lieu de `/media/...`

---

## 📝 Checklist de Déploiement

- [ ] Choisir la solution (R2 recommandé)
- [ ] Créer le compte et le bucket
- [ ] Récupérer les identifiants
- [ ] Installer `django-storages` et `boto3`
- [ ] Ajouter la configuration dans `settings.py`
- [ ] Ajouter les variables d'environnement sur Render
- [ ] Redéployer l'application
- [ ] Tester l'upload d'une photo
- [ ] Vérifier que l'URL commence par R2/Cloudinary
- [ ] (Optionnel) Migrer les médias existants

---

## 🆘 Dépannage

### **Erreur : "No module named 'storages'"**

```bash
pip install django-storages boto3
# Ajouter à requirements.txt
```

### **Erreur : "Unable to locate credentials"**

Vérifiez que les variables d'environnement sont définies sur Render :
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`

### **Erreur : "Access Denied"**

Vérifiez les permissions de l'API Token R2 (Read & Write requis)

### **Les anciennes photos ne marchent plus**

Normal si elles étaient stockées localement. Deux solutions :
1. Ré-uploader les photos via l'interface admin
2. Exécuter le script de migration ci-dessus

---

## 💡 Recommandation Finale

**Pour ce projet** : Utilisez **Cloudflare R2**

✅ **Raisons** :
1. 10 GB gratuits suffisants pour démarrer
2. Pas de frais de bande passante (important pour un site photo)
3. Compatible S3 (migration facile vers AWS si besoin)
4. CDN global inclus (rapidité mondiale)
5. Configuration simple

**Coût estimé** (1000 événements, 50 photos/événement = 50 000 photos) :
- Photos : ~25 GB
- Coût : **~$0.40/mois** (après les 10 GB gratuits)

C'est négligeable comparé au coût d'hébergement Render !
