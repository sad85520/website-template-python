from csp.decorators import csp_update
from django.conf import settings
from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.urls import URLPattern, URLResolver, include, path
from drf_spectacular.views import SpectacularAPIView
from health_check.views import HealthCheckView


# Scalar UI 專用 CSP：只對此 view 放寬，全域嚴格 CSP 不受影響。
@csp_update(  # type: ignore[untyped-decorator]
    SCRIPT_SRC=["https://cdn.jsdelivr.net", "'unsafe-inline'"],
    STYLE_SRC=["https://cdn.jsdelivr.net", "'unsafe-inline'"],
    IMG_SRC=["'self'", "data:", "https:"],
    FONT_SRC=["https://cdn.jsdelivr.net"],
)
def scalar_view(request: HttpRequest) -> HttpResponse:
    """Scalar API 文件 UI（僅開發環境）。

    安全考量：
    - 腳本來源固定到 ``@scalar/api-reference@1``（major 版本鎖），避免 jsdelivr
      預設的滾動 latest tag 在 supply chain 事件發生時把惡意 bundle 推到所有部署。
    - 若要更嚴格（擋住 minor/patch 被竄改），請將 URL 改為具體版本例如
      ``@scalar/api-reference@1.25.100/dist/browser/standalone.js`` 並加上
      ``integrity="sha384-..." crossorigin="anonymous"``；SRI hash 可用
      ``curl -sL <url> | openssl dgst -sha384 -binary | openssl base64 -A`` 計算。
    - 即便鎖版本，此 view 也僅在 ``settings.DEBUG`` 下掛載（見 urlpatterns 條件分支），
      production 不會暴露此端點。
    """
    html = """<!doctype html>
<html>
  <head>
    <title>WebTemplate API Reference</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
  </head>
  <body>
    <script id="api-reference" data-url="/api/schema/"></script>
    <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference@1"></script>
  </body>
</html>"""
    return HttpResponse(html)


urlpatterns: list[URLPattern | URLResolver] = [
    path("admin/", admin.site.urls),
    # API v1
    path("api/v1/auth/", include("apps.accounts.urls.auth")),
    path("api/v1/users/", include("apps.accounts.urls.users")),
    # Health Check：兩個獨立 view 各自帶自己的 checks 清單，不依賴
    # HEALTH_CHECK["SUBSETS"] 設定，也不透過已棄用的 health_check.urls /
    # MainView（該路由需要額外設定 SUBSETS 才會動作，漏設會讓 subset 路由永遠
    # 回 404，導致 k8s readinessProbe 永遠卡在 0/2 Ready）。
    # Liveness：不帶任何 check，純粹確認 process 存活、不觸碰 DB/cache，
    # 避免 DB 短暫抖動時被 kubelet 誤判為 process 掛掉而重啟 Pod。
    path("api/health/", HealthCheckView.as_view(checks=()), name="health_check_live"),
    # Readiness：檢查 DB 與 cache 連線，只有兩者皆可用才回 200，
    # 對齊 k8s readinessProbe 語意（尚未就緒的 Pod 不該收到流量）。
    path(
        "api/health/ready/",
        HealthCheckView.as_view(checks=("health_check.Database", "health_check.Cache")),
        name="health_check_ready",
    ),
]

# OpenAPI schema JSON + Scalar UI，僅開發環境掛載，且統一放在 /api/ 前綴下，
# 讓 nginx 既有的 /api/ location 自然涵蓋，不需要另外新增 proxy 規則。
# 生產環境不掛載是為了避免 API 結構對外暴露，減少攻擊面。
if settings.DEBUG:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/scalar/", scalar_view, name="scalar"),
    ]
