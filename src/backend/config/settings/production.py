"""Production settings."""

from decouple import config
from django.core.exceptions import ImproperlyConfigured

from config.logging import build_logging_dict, configure_structlog

from .base import *  # noqa: F403, F401

DEBUG = False

# WhiteNoise 專用 storage backend：collectstatic 時額外產生檔名帶 content-hash
# 的版本並壓縮（gzip/brotli），讓 WhiteNoiseMiddleware 可設定近乎永久的
# Cache-Control（檔名變了瀏覽器才會重新下載，內容沒變則永久命中快取）。
# 只在 production 覆寫、不放在 base.py：dev/test 從未執行 collectstatic，
# 沒有 staticfiles manifest 檔，若全域套用會讓任何 {% static %} 渲染直接
# 因「manifest 缺少該檔案」而炸掉。
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# ALLOWED_HOSTS 在 production 不提供 default：漏設即 fail-fast，避免
# 上線後靜默接受任意 Host header 造成 host-header attack / cache poisoning。
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    cast=lambda v: [s.strip() for s in v.split(",")],
)

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
# nginx 層雖也有設 Referrer-Policy，但繞過 nginx 的 k8s 內部測試（port-forward、curl
# 直打 pod IP）不會帶此 header；Django 層再設一次保證任何入口都有防護。
# strict-origin-when-cross-origin：同源送完整 URL、跨域降級為 origin、HTTPS→HTTP 不送。
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

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
# 預設 86400（1 天）作為起手值：夠長讓 HSTS 真的對一般使用者生效（3600 在
# 單次瀏覽 session 內就過期，等同沒設），又短到 HTTPS 誤設時一天內可復原。
# 部署穩定後將 HSTS_SECONDS 環境變數調至 31536000（1 年）並開啟 HSTS_PRELOAD。
SECURE_HSTS_SECONDS = config("HSTS_SECONDS", default=86400, cast=int)
# include_subdomains=True 會將 HSTS 擴展至所有子網域，
# 需確認所有子網域皆已部署有效的 HTTPS 憑證，否則會導致該子網域無法透過 HTTP 訪問。
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# PRELOAD 要送出，網站才有資格提交到 Chrome HSTS preload list；
# 但一旦加入就難以撤銷，確認穩定後再開啟。
SECURE_HSTS_PRELOAD = config("HSTS_PRELOAD", default=False, cast=bool)

# 生產環境 CORS 透過 Nginx 同 origin 處理，不需要 CORS headers
CORS_ALLOWED_ORIGINS: list[str] = []

# Cache override：production 必須使用 Redis 作為共享快取；
# DRF throttling / django-ratelimit 皆以 cache 後端存計數，HPA scale-out 後
# 每個 pod 各自持有 LocMemCache 會讓限流額度被 N 倍放大（等於未設限）。
# 因此這裡改為 fail-fast：REDIS_URL 未設定直接 ImproperlyConfigured，
# 避免靜默降級到 LocMemCache 讓限流 / session 等依賴 cache 的機制在 prod 失效。
_redis_url = config("REDIS_URL", default="")
if not _redis_url:
    raise ImproperlyConfigured(
        "REDIS_URL must be set in production. DRF throttling requires a shared "
        "cache backend — LocMemCache per-pod fallback would bypass rate limits."
    )
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
