"""Development settings — enables debug and verbose logging."""
from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Show SQL queries in console during development
LOGGING["loggers"]["django.db.backends"]["level"] = "DEBUG"  # noqa: F405
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


CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "showflow-cache",
    }
}