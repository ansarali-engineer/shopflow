"""Production settings — hardened for deployment."""
from .base import *  # noqa: F401, F403

DEBUG = False
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")  # noqa: F405

# Security headers
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Stricter CORS
CORS_ALLOWED_ORIGINS = [  # noqa: F405
    origin.strip()
    for origin in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")  # noqa: F405
    if origin.strip()
]

# Tighter throttle rates
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "config.schema.ShopFlowAutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.authentication.backends.ShopFlowJWTAuthentication",
    ),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],

    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/min",
        "user": "100/min",
        "login": "5/min",
        "password_reset": "3/min",
        "otp": "5/min",
    },
}

# Minimal logging
LOGGING["loggers"]["django.db.backends"]["level"] = "ERROR"  # noqa: F405
LOGGING["loggers"]["shopflow"]["level"] = "WARNING"  # noqa: F405
LOGGING["root"]["level"] = "WARNING"  # noqa: F405

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "TIMEOUT": 60,
    }
}