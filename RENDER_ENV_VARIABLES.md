# 🔧 Variables d'Environnement Render

## Variables Obligatoires

Ajoutez ces variables dans **Render Dashboard** → Votre Service → **Environment** :

```env
# Django Core
DJANGO_SECRET_KEY=changez-cette-cle-par-une-valeur-secrete-longue-et-aleatoire
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=photo-scan-api-9o78.onrender.com

# Base de Données (Automatique sur Render PostgreSQL)
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Frontend URL
FRONTEND_URL=https://votre-frontend.onrender.com

# CORS (Optionnel si CORS_ALLOW_ALL_ORIGINS=True)
CORS_ALLOWED_ORIGINS=https://votre-frontend.onrender.com,https://autre-domaine.com

# Celery / Redis (Si vous utilisez Redis)
CELERY_BROKER_URL=redis://red-xxxxx:6379/0
CELERY_RESULT_BACKEND=redis://red-xxxxx:6379/0
```

---

## Variables Optionnelles (SMS/Email/WhatsApp)

```env
# SMS Aqilas (Burkina Faso)
AQILAS_API_TOKEN=votre-token-aqilas
AQUILAS_SENDER_ID=VOTREAPP

# Email SMTP
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=votre-email@gmail.com
EMAIL_HOST_PASSWORD=votre-mot-de-passe-application
DEFAULT_FROM_EMAIL=Votre App <noreply@votre-app.com>

# WhatsApp Twilio (Optionnel)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxx
TWILIO_WHATSAPP_NUMBER=+14155238886
```

---

## Commande de Démarrage Render

Dans **Render Dashboard** → **Settings** → **Start Command** :

```bash
cd photo && gunicorn photo.wsgi:application
```

---

## Build Command

```bash
./photo/build.sh
```

Ou si le script est à la racine :

```bash
./build.sh
```

---

## 🔐 Générer une SECRET_KEY Sécurisée

```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copiez la clé générée et utilisez-la comme `DJANGO_SECRET_KEY`.

---

## ✅ Vérification

Après configuration, vos endpoints doivent :

1. ✅ Retourner des URLs en `https://` (pas `http://`)
2. ✅ Servir les médias depuis `/media/`
3. ✅ Permettre les connexions CORS depuis votre frontend
4. ✅ Générer des liens d'invitation pointant vers `FRONTEND_URL`

---

## 🐛 Dépannage

### **Erreur : "DisallowedHost"**
→ Vérifiez `DJANGO_ALLOWED_HOSTS=photo-scan-api-9o78.onrender.com`

### **Erreur : "CSRF verification failed"**
→ Ajoutez `CSRF_TRUSTED_ORIGINS=https://photo-scan-api-9o78.onrender.com`

### **Les médias ne s'affichent pas (404)**
→ Vérifiez que le dossier `media/` est créé et que les corrections dans `urls.py` sont appliquées

### **Les liens sont en http:// au lieu de https://**
→ Vérifiez que `SECURE_PROXY_SSL_HEADER` est dans `settings.py`
