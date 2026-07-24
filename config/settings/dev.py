from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

INSTALLED_APPS = INSTALLED_APPS + ['debug_toolbar']  # noqa: F405

MIDDLEWARE = [  # noqa: F405
    'debug_toolbar.middleware.DebugToolbarMiddleware',
] + MIDDLEWARE  # noqa: F405

INTERNAL_IPS = ['127.0.0.1']

# Local dev and the test suite log in freely; the brute-force throttles only
# make sense against the public internet. Both login buckets are lifted.
REST_FRAMEWORK = {  # noqa: F405
    **REST_FRAMEWORK,  # noqa: F405
    'DEFAULT_THROTTLE_RATES': {'login': '1000/min', 'login_user': '1000/min'},
}

# Mock gateway is dev/test only — it settles payments on command.
PAYMENT_GATEWAYS = ['fonepay', 'mock']
