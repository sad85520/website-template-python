from csp.decorators import csp_update
from django.conf import settings
from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView


# Scalar UI 專用 CSP：只對此 view 放寬，全域嚴格 CSP 不受影響。
@csp_update(
    SCRIPT_SRC=["https://cdn.jsdelivr.net", "'unsafe-inline'"],
    STYLE_SRC=["https://cdn.jsdelivr.net", "'unsafe-inline'"],
    IMG_SRC=["'self'", "data:", "https:"],
    FONT_SRC=["https://cdn.jsdelivr.net"],
)
def scalar_view(request: HttpRequest) -> HttpResponse:
    """Scalar API 文件 UI（僅開發環境）。"""
    html = """<!doctype html>
<html>
  <head>
    <title>WebTemplate API Reference</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
  </head>
  <body>
    <script id="api-reference" data-url="/api/schema/"></script>
    <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
  </body>
</html>"""
    return HttpResponse(html)


urlpatterns = [
    path("admin/", admin.site.urls),
    # API v1
    path("api/v1/auth/", include("apps.accounts.urls.auth")),
    path("api/v1/users/", include("apps.accounts.urls.users")),
    # Health Check
    path("api/health/", include("health_check.urls")),
    # OpenAPI schema（drf-spectacular 產生 JSON）
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
]

# Scalar API 文件 UI，僅開發環境掛載
if settings.DEBUG:
    urlpatterns += [
        path("scalar/", scalar_view, name="scalar"),
    ]
