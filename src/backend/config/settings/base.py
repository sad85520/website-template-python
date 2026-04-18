"""
Base settings shared across all environments.
"""
from datetime import timedelta
from pathlib import Path

from decouple import config

# django-stubs 的 runtime patch：讓 ``QuerySet[Model]``、``Manager[Model]`` 等
# 泛型型別在執行期可被 subscript，使同一份型別標註可同時被 mypy 與 Python runtime 接受。
# 必須在載入任何應用程式 model 之前呼叫，放在 settings 最上方最安全。
try:
    import django_stubs_ext

    django_stubs_ext.monkeypatch()
except ImportError:
    # 正式環境不安裝 dev 依賴時 django_stubs_ext 可能不存在，忽略即可。
    pass

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY: str = config("SECRET_KEY")

DEBUG: bool = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS: list[str] = config(
    "ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=lambda v: [s.strip() for s in v.split(",")]
)

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
    "health_check",
    "health_check.db",
    "health_check.cache",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # CSPMiddleware 必須緊接在 SecurityMiddleware 之後、CorsMiddleware 之前，
    # 才能確保 Content-Security-Policy header 在所有回應中都被設定。
    "csp.middleware.CSPMiddleware",
    # CorsMiddleware 必須排在 SessionMiddleware 之前，
    # 才能在 OPTIONS preflight 請求上直接回傳 CORS headers，不觸發 session 開啟。
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Content Security Policy（django-csp）
# 全域嚴格 CSP，純 API 不需要任何 script/style。
# Scalar UI 路徑透過 urls.py 的 @csp_update decorator 個別放寬。
CSP_DEFAULT_SRC = ("'none'",)
CSP_SCRIPT_SRC = ("'none'",)
CSP_STYLE_SRC = ("'none'",)
CSP_IMG_SRC = ("'self'", "data:")
CSP_FONT_SRC = ("'none'",)
CSP_CONNECT_SRC = ("'self'",)
CSP_FRAME_ANCESTORS = ("'none'",)

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="website_template"),
        "USER": config("DB_USER", default="postgres"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST", default="postgres"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

# Custom User Model
AUTH_USER_MODEL = "accounts.User"

# Password Validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = config("LANGUAGE_CODE", default="en-us")
TIME_ZONE = config("TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

# Static Files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Cache
# DRF throttling 以 cache 為狀態儲存；DEFAULT_THROTTLE_RATES 已設定，
# 若未定義 CACHES，Django 會退回 per-process LocMemCache，在多 gunicorn worker
# 下各 worker 有獨立計數器，使限流額度實質變成 N 倍。
# 預設以 LocMemCache 撐開發環境；production.py 必須 override 為共享快取（Redis/Memcached）。
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "web-template-dev",
    }
}

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    # Throttle classes 在 view 中以 AnonRateThrottle / UserRateThrottle 宣告，
    # 但實際速率必須在此處以 scope → rate 的對應表設定，否則 DRF 會完全跳過限流。
    # 格式：'<n>/<period>'，period 支援 'second' | 'minute' | 'hour' | 'day'。
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/minute",
        "user": "120/minute",
    },
}

# JWT Settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=config("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", default=15, cast=int)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=config("JWT_REFRESH_TOKEN_LIFETIME_DAYS", default=7, cast=int)
    ),
    # 每次換發 refresh token 時，舊 token 必須同步加入黑名單，
    # 否則舊 token 在過期前仍可換發新 token，造成 token 無法真正撤銷。
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    # 不更新 last_login，以避免每次 token 刷新都觸發一次 DB write，
    # 對高頻 API 服務會產生不必要的寫入壓力。
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    # 使用獨立的 JWT_SIGNING_KEY 可讓 JWT 簽名密鑰與 Django SECRET_KEY 解耦；
    # 若只有 SECRET_KEY 洩漏，攻擊者仍無法偽造 JWT。
    # 不提供 default：未設定時立即在啟動階段失敗，避免 production 誤用 SECRET_KEY 作為簽章密鑰。
    "SIGNING_KEY": config("JWT_SIGNING_KEY"),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# drf-spectacular（產生 OpenAPI JSON，由 Scalar UI 渲染）
SPECTACULAR_SETTINGS = {
    "TITLE": "WebTemplate API",
    "DESCRIPTION": "Vue 3 + Django REST Framework Website Template",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# Refresh Token Cookie
# refresh token 存放於 HttpOnly cookie，而非 localStorage，
# 可防止 XSS 腳本直接讀取 token；SameSite=Strict 則進一步阻擋 CSRF 跨站請求攜帶此 cookie。
REFRESH_TOKEN_COOKIE_NAME = "refreshToken"
# 開發環境（DEBUG=True）不強制 Secure，讓 http://localhost 也能正常運作。
REFRESH_TOKEN_COOKIE_SECURE = not DEBUG
REFRESH_TOKEN_COOKIE_HTTPONLY = True
REFRESH_TOKEN_COOKIE_SAMESITE = "Strict"
