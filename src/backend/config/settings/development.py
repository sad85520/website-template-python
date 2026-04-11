"""Development settings."""
from .base import *  # noqa: F403, F401

DEBUG = True

# Scalar CSP 透過 urls.py 的 @csp_update decorator 個別套用，不在此全域覆寫。

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost",
]

CORS_ALLOW_CREDENTIALS = True

# 開發環境顯示詳細 SQL log
LOGGING = {
    "version": 1,
    # disable_existing_loggers=False 保留 Django 及第三方套件的預設 logger，
    # 避免覆寫後遺失重要的框架警告訊息。
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO"},
        "django.db.backends": {"handlers": ["console"], "level": "DEBUG"},
    },
}
