"""Production settings."""
from decouple import config

from config.logging import build_logging_dict, configure_structlog

from .base import *  # noqa: F403, F401

DEBUG = False

# ALLOWED_HOSTS 在 production 不提供 default：漏設即 fail-fast，避免
# 上線後靜默接受任意 Host header 造成 host-header attack / cache poisoning。
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    cast=lambda v: [s.strip() for s in v.split(",")],
)

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
# 初次部署預設用 1 小時（3600）讓誤設可快速復原，確認無問題後再透過
# HSTS_SECONDS 環境變數調高至 31536000（1 年）；否則 HTTPS 設定有誤時，
# 使用者在 HSTS 有效期內將無法訪問網站。
SECURE_HSTS_SECONDS = config("HSTS_SECONDS", default=3600, cast=int)
# include_subdomains=True 會將 HSTS 擴展至所有子網域，
# 需確認所有子網域皆已部署有效的 HTTPS 憑證，否則會導致該子網域無法透過 HTTP 訪問。
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# PRELOAD 要送出，網站才有資格提交到 Chrome HSTS preload list；
# 但一旦加入就難以撤銷，確認穩定後再開啟。
SECURE_HSTS_PRELOAD = config("HSTS_PRELOAD", default=False, cast=bool)

# 生產環境 CORS 透過 Nginx 同 origin 處理，不需要 CORS headers
CORS_ALLOWED_ORIGINS: list[str] = []

# Cache override：production 使用 Redis 作為共享快取，避免多 worker 下
# LocMemCache 各自計數造成 DRF throttling 失效。
# REDIS_URL 未設定時退回 LocMemCache 並在啟動時印 warning，方便本地
# 模擬 production settings；但真正部署必須透過 env var 指定。
_redis_url = config("REDIS_URL", default="")
if _redis_url:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _redis_url,
        }
    }

# prod 走 JSONRenderer，方便 log aggregator（Loki、CloudWatch、Stackdriver）
# 按 key 查詢；processor chain 與 dev 共用，避免兩邊欄位集合漂移。
# `MinimumLevel__Default` 透過環境變數覆寫（Serilog 命名沿用，僅示意對照）：
# 若需臨時壓低雜訊，改 `LOGGING["root"]["level"]` 或在 docker-compose.prod.yml
# 加 `LOG_LEVEL` env 再讀入。
configure_structlog(json_output=True)
LOGGING = build_logging_dict(
    json_output=True,
    level=config("LOG_LEVEL", default="INFO"),
)
