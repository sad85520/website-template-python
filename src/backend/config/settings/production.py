"""Production settings."""
from .base import *  # noqa: F403, F401

DEBUG = False

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# 強制 HTTPS：任何 HTTP 連線都會被 301 重導向至 HTTPS。
# 若部署於反向代理（Nginx、ALB）之後，務必搭配 SECURE_PROXY_SSL_HEADER 讓 Django 正確辨識協定，
# 否則會造成無限重導向迴圈。
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# 所有 session / csrf cookie 僅透過 HTTPS 傳輸，
# 避免被中間人在 HTTP 連線上竊取 session token。
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # CSRF token 必須可由前端 JS 讀取以帶入 header
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
# HSTS 一旦設定，瀏覽器會在指定秒數內強制使用 HTTPS。
# 初次部署時應先用較短的值（如 3600），確認無問題後再提升至 31536000，
# 否則一旦 HTTPS 設定有誤，使用者在 HSTS 有效期內將無法訪問網站。
SECURE_HSTS_SECONDS = 31536000
# include_subdomains=True 會將 HSTS 擴展至所有子網域，
# 需確認所有子網域皆已部署有效的 HTTPS 憑證，否則會導致該子網域無法透過 HTTP 訪問。
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
