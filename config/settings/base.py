"""
Shared settings — imported by dev.py and prod.py.

Import rule (enforced here at the framework level):
  core  ←  accounts, locations, partners, catalog, lots, processing,
            inventory, procurement, sales, billing
  Dependency direction is strictly downward. Siblings never import each other;
  shared logic belongs in core. Nothing imports upward toward config or core's
  private internals.
"""
import os
from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    # local — order matches dependency direction (core first)
    'apps.core',
    'apps.accounts',
    'apps.locations',
    'apps.partners',
    'apps.catalog',
    'apps.lots',
    'apps.processing',
    'apps.inventory',
    'apps.procurement',
    'apps.sales',
    'apps.billing',
]

# Custom user model — set before the first migration ever runs.
AUTH_USER_MODEL = 'accounts.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ── Database ───────────────────────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ['DB_USER'],
        'PASSWORD': os.environ['DB_PASSWORD'],
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# ── Password validation ────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalisation ───────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kathmandu'
USE_I18N = True
USE_TZ = True

# ── Static & Media ─────────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
_media_root_env = os.environ.get('MEDIA_ROOT', '')
MEDIA_ROOT = Path(_media_root_env) if _media_root_env else BASE_DIR / 'media'

# ── REST Framework ─────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# ── JWT ────────────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=int(os.environ.get('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', 60))
    ),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        days=int(os.environ.get('JWT_REFRESH_TOKEN_LIFETIME_DAYS', 7))
    ),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# ── CORS ───────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get('CORS_ALLOWED_ORIGINS', 'http://localhost:5173').split(',')
    if o.strip()
]

# ── Celery ─────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    'low-stock-alert-hourly': {
        'task': 'inventory.low_stock_alert',
        'schedule': 3600,  # every hour
    },
    'expiry-alert-daily': {
        'task': 'lots.expiry_alert',
        'schedule': 86400,  # every 24 h
    },
    'nightly-rollup': {
        'task': 'sales.nightly_rollup',
        # run at 00:15 NPT; crontab uses UTC — NPT is UTC+5:45
        'schedule': crontab(hour=18, minute=30),  # 00:15 NPT (UTC+5:45)
    },
    'cbms-sync-every-15min': {
        'task': 'billing.cbms_sync',
        'schedule': 900,  # every 15 min
    },
}

# ── Alert / sync knobs (override per environment) ──────────────────────────────
LOW_STOCK_THRESHOLD_KG  = int(os.environ.get('LOW_STOCK_THRESHOLD_KG', 10))
LOT_EXPIRY_ALERT_DAYS   = int(os.environ.get('LOT_EXPIRY_ALERT_DAYS', 3))
CBMS_SYNC_BATCH_SIZE    = int(os.environ.get('CBMS_SYNC_BATCH_SIZE', 50))

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
