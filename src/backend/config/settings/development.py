"""Development settings."""
from .base import *  # noqa: F403, F401

DEBUG = True

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost",
]

CORS_ALLOW_CREDENTIALS = True

# 開發環境顯示詳細 SQL log
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO"},
        "django.db.backends": {"handlers": ["console"], "level": "DEBUG"},
    },
}
