"""
Configuration principale du projet Django 'photo'.

Ce fichier centralise l'ensemble des paramètres d'exécution de la plateforme :
- Sécurité et gestion des environnements (local vs production Render)
- Modularité des applications (authentification, SaaS multi-tenant, médias, IA faciale)
- Optimisation des performances (connexions persistantes, caches mémoire)
- Intégration continue et déploiement cloud (Render, WhiteNoise, PostgreSQL)
"""

from pathlib import Path
from datetime import timedelta
import os
import dj_database_url

# ==============================================================================
# CHEMINS DU SYSTÈME DE FICHIERS
# ==============================================================================
# BASE_DIR pointe vers le dossier parent contenant manage.py et les dossiers d'apps.
# L'utilisation de resolve() garantit un chemin absolu multiplateforme (Windows/Linux).
BASE_DIR = Path(__file__).resolve().parent.parent

# ==============================================================================
# SÉCURITÉ & ENVIRONNEMENT
# ==============================================================================
# La clé secrète doit impérativement être fournie par variable d'environnement en production.
# La valeur par défaut 'django-insecure' est strictement réservée au développement local.
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-#w2pc%qmpt+x!zspx=$ipibul2j8x)+m-no*%%_5+%hsu78rsf'
)

# En production sur Render, DJANGO_DEBUG doit être positionné à 'False'
# pour éviter la fuite de données sensibles (traces d'appels, identifiants) en cas d'erreur 500.
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')

# ALLOWED_HOSTS restreint les noms d'hôtes HTTP acceptés afin de prévenir les attaques
# par empoisonnement d'en-tête Host (Host Header Injection).
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')

# URL de base de l'application Web Frontend (React, Vue, Next.js, etc.)
# Utilisée pour générer les liens d'invitation et d'activation WhatsApp/SMS.
# En production sur Render, définissez la variable d'environnement FRONTEND_URL.
FRONTEND_URL = os.environ.get('FRONTEND_URL', '').rstrip('/')

# ==============================================================================
# APPLICATIONS INSTALLÉES
# ==============================================================================
INSTALLED_APPS = [
    # Applications natives Django indispensables au fonctionnement du framework
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Bibliothèques tierces pour l'API REST, l'authentification et la documentation
    'rest_framework',              # Framework d'API REST robuste
    'rest_framework_simplejwt',    # Authentification par jetons JSON Web Token
    'corsheaders',                 # Gestion des en-têtes CORS pour les clients frontends
    'drf_spectacular',             # Génération automatique de la spécification OpenAPI 3 / Swagger

    # Applications métier internes du domaine Photo Scan
    'apps.organizations',          # Gestion SaaS multi-tenant, membres et invitations WhatsApp
    'apps.events',                 # Événements, fiches descriptives et galeries dédiées
    'apps.media',                  # Stockage, validation et métadonnées des photos/vidéos
    'apps.participants',           # Profils des usagers, selfies de référence et conformité RGPD
    'apps.faces',                  # Moteur IA de reconnaissance et indexation faciale
]

# ==============================================================================
# CHAÎNE DES MIDDLEWARES
# ==============================================================================
# L'ordre des middlewares est crucial :
# 1. SecurityMiddleware applique les règles HTTPS et XSS en tout premier.
# 2. WhiteNoiseMiddleware intercepte les requêtes de fichiers statiques sans passer par Django.
# 3. CorsMiddleware doit précéder CommonMiddleware pour renvoyer les bons en-têtes pré-vol (OPTIONS).
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Protection contre les attaques courantes du Web (Clickjacking, MIME-sniffing, XSS)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_HTTPONLY = True     # Empêche l'accès aux cookies de session via document.cookie en JavaScript
CSRF_COOKIE_HTTPONLY = True

ROOT_URLCONF = 'photo.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'photo.wsgi.application'

# ==============================================================================
# BASE DE DONNÉES (POSTGRESQL CLOUD / SQLITE LOCAL)
# ==============================================================================
# dj_database_url analyse automatiquement la variable DATABASE_URL injectée par Render.
# Si DATABASE_URL est absente (développement local), une base SQLite locale est employée.
# conn_max_age=600 maintient les connexions actives pendant 10 minutes (pooling) pour éviter
# le surcoût de négociation SSL/TCP à chaque requête API.
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}
# Sur SQLite, un timeout de 30 secondes évite l'erreur 'database is locked' lors des écritures
# concurrentes du serveur web et des workers Celery en tâche de fond.
if DATABASES['default'].get('ENGINE') == 'django.db.backends.sqlite3':
    DATABASES['default'].setdefault('OPTIONS', {})['timeout'] = 30

# ==============================================================================
# CACHE EN MÉMOIRE
# ==============================================================================
# Utilisation de LocMemCache pour stocker temporairement les réponses des listes publiques
# sans introduire de dépendance obligatoire à un serveur Redis externe en environnement léger.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'photo-scan-cache',
        'TIMEOUT': 60,  # 60 secondes par défaut pour les endpoints publics
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Ouagadougou'
USE_I18N = True
USE_TZ = True

# ==============================================================================
# GESTION DES FICHIERS STATIQUES ET MÉDIAS
# ==============================================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise permet à l'application Python de servir elle-même ses fichiers statiques
# compilés et compressés (gzip/brotli) en production, sans nécessiter de serveur Nginx séparé.
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==============================================================================
# LIMITES D'UPLOAD POUR LES ÉVÉNEMENTS
# ==============================================================================
# Les appareils photo professionnels (reflex, hybrides) génèrent des images volumineuses.
# Ces plafonds autorisent l'envoi de fichiers haute définition et de lots (batch) de photos
# tout en évitant l'épuisement mémoire du serveur (Out-Of-Memory) grâce au streaming sur disque.
DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100 Mo max pour la requête globale multipart
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024   # 50 Mo max par photo unitaire
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000             # Nombre de champs form-data acceptés par lot

# ==============================================================================
# CONFIGURATION CORS (CROSS-ORIGIN RESOURCE SHARING)
# ==============================================================================
# Autorise les requêtes provenant des applications frontend (Single Page Applications).
# En développement local, les serveurs de dev Vite s'exécutent typiquement sur les ports 5173, 5174, 5175.
CORS_ALLOW_ALL_ORIGINS = os.environ.get('CORS_ALLOW_ALL_ORIGINS', 'True').lower() in ('true', '1', 'yes')
_extra_origins = [o.strip() for o in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if o.strip()]
CORS_ALLOWED_ORIGINS = list(set([
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
] + _extra_origins))
CORS_ALLOW_CREDENTIALS = True  # Permet l'envoi de cookies et d'en-têtes d'autorisation sécurisés
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# ==============================================================================
# DJANGO REST FRAMEWORK : AUTHENTIFICATION, SÉCURITÉ & THROTTLING
# ==============================================================================
REST_FRAMEWORK = {
    # JWT pour les clients API mobiles/frontends, SessionAuthentication pour le Django Admin
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
    # Génération du schéma OpenAPI 3 par drf-spectacular
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',

    # Limitation du débit de requêtes (Throttling) :
    # Essentiel pour protéger l'API contre les attaques par force brute (sur la connexion)
    # et contre les dénis de service (DoS) sur le calcul intensif de reconnaissance faciale.
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '120/min',         # Limite standard pour les visiteurs anonymes
        'user': '300/min',        # Limite confortable pour les utilisateurs authentifiés
        'auth': '10/min',         # Protection anti-brute-force stricte sur /auth/login/
        'face_upload': '20/min',   # Protection anti-surcharge CPU/GPU sur l'analyse de selfies
        'admin_media': '60/min',   # Débit maîtrisé lors de l'envoi de lots de photos
    },
}

# ==============================================================================
# CONFIGURATION SWAGGER / OPENAPI (DRF-SPECTACULAR)
# ==============================================================================
# Génère la documentation interactive consultable sur /api/docs/ et /api/schema/
SPECTACULAR_SETTINGS = {
    'TITLE': 'Plateforme Photo Scan API',
    'DESCRIPTION': (
        'Documentation interactive de l\'API backend Django REST Framework '
        'pour la plateforme événementielle avec reconnaissance faciale (Burkina Faso).\n\n'
        'Fonctionnalités principales :\n'
        '- Gestion des événements et galeries médias\n'
        '- Upsert des participants via numéro WhatsApp\n'
        '- Ingestion sécurisée de selfie de référence & matching facial 512D\n'
        '- Endpoints RGPD de suppression et droit à l\'oubli\n'
        '- Administration sécurisée via token JWT'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'TAGS': [
        {'name': 'Authentification', 'description': 'Connexion et rafraîchissement des tokens JWT'},
        {'name': 'Événements', 'description': 'Consultation publique des événements et galeries'},
        {'name': 'Participants', 'description': 'Enregistrement, selfies de référence et RGPD'},
        {'name': 'Administration', 'description': 'Statistiques, upload médias et gestion des organisateurs'},
    ],
    'ENUM_NAME_OVERRIDES': {
        'EventStatusEnum': 'apps.events.models.Event.STATUS_CHOICES',
        'ParticipantMatchStatusEnum': 'apps.participants.models.Participant.MATCH_STATUS',
    },
}

# ==============================================================================
# AUTHENTIFICATION SIMPLEJWT
# ==============================================================================
# Durée de vie du token d'accès fixée à 1 jour pour une bonne expérience utilisateur mobile/web.
# Le refresh token (7 jours) dispose d'une rotation automatique : chaque renouvellement
# invalide l'ancien refresh token pour limiter l'impact d'une interception.
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ==============================================================================
# TRAITEMENTS ASYNCHRONES CELERY (RECONNAISSANCE FACIALE)
# ==============================================================================
# L'extraction des visages et le calcul des similarités étant coûteux en CPU,
# ces traitements sont délégués à des files d'attente (broker Redis) consommées par des workers.
# CELERY_TASK_ALWAYS_EAGER est à False pour garantir un traitement non-bloquant en production.
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_ALWAYS_EAGER = False

# ==============================================================================
# LOGGING STRUCTURÉ POUR LA PRODUCTION
# ==============================================================================
# La sortie console (StreamHandler) est capturée nativement par Render et les conteneurs Docker.
# Les modules critiques (faces, participants) sont en niveau INFO pour tracer le pipeline IA,
# tandis que les requêtes standards sont filtrées pour ne pas saturer les fichiers journaux.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'apps.faces': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.participants': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.media': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}
