"""Production settings."""
from .base import *  # noqa: F403, F401

DEBUG = False

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
# HSTS 一旦設定，瀏覽器會在指定秒數內強制使用 HTTPS。
# 初次部署時應先用較短的值（如 3600），確認無問題後再提升至 31536000，
# 否則一旦 HTTPS 設定有誤，使用者在 HSTS 有效期內將無法訪問網站。
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# 生產環境 CORS 透過 Nginx 同 origin 處理，不需要 CORS headers
CORS_ALLOWED_ORIGINS: list[str] = []

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "structlog.stdlib.ProcessorFormatter",
            "processor": "structlog.processors.JSONRenderer",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
