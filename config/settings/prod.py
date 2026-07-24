import os

from .base import *  # noqa: F401, F403

DEBUG = False

ALLOWED_HOSTS = [h.strip() for h in os.environ['ALLOWED_HOSTS'].split(',') if h.strip()]

# Origins (scheme + host) trusted for CSRF-protected requests, e.g. the
# Django admin behind HTTPS. Defaults to https:// on each allowed host.
CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        'CSRF_TRUSTED_ORIGINS', ','.join(f'https://{h}' for h in ALLOWED_HOSTS)
    ).split(',')
    if o.strip()
]

# TLS terminates at the reverse proxy; trust its forwarded-proto header so
# Django knows the original request was secure.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# One proxy (nginx) sits in front, so the real client IP is the last entry it
# appended to X-Forwarded-For. Tell DRF's throttling to key on that rather than the
# proxy's address or a spoofable first XFF entry (EF-09). Raise if extra proxies exist.
REST_FRAMEWORK = {**REST_FRAMEWORK, 'NUM_PROXIES': int(os.environ.get('NUM_PROXIES', 1))}  # noqa: F405

# HTTPS enforcement. Default on; set SECURE_SSL_REDIRECT=false only for
# LAN-only outlet deployments where no TLS certificate exists.
_https_on = os.environ.get('SECURE_SSL_REDIRECT', 'true').lower() != 'false'
SECURE_SSL_REDIRECT = _https_on
SECURE_HSTS_SECONDS = 31536000 if _https_on else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = _https_on
SECURE_HSTS_PRELOAD = _https_on
SECURE_REFERRER_POLICY = 'same-origin'
SESSION_COOKIE_SECURE = _https_on
CSRF_COOKIE_SECURE = _https_on

# Persistent DB connections between requests.
DATABASES['default']['CONN_MAX_AGE'] = int(os.environ.get('DB_CONN_MAX_AGE', 60))  # noqa: F405

# Shared cache — required so login throttling counts across gunicorn workers.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/1'),
    }
}

# Whitenoise serves collected static files (Django admin assets) straight
# from gunicorn — no separate static file server needed.
MIDDLEWARE = MIDDLEWARE[:1] + ['whitenoise.middleware.WhiteNoiseMiddleware'] + MIDDLEWARE[1:]  # noqa: F405
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}

_sentry_dsn = os.environ.get('SENTRY_DSN', '')
if _sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(dsn=_sentry_dsn, integrations=[DjangoIntegration()], traces_sample_rate=0.1)
