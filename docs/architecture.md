# 架構說明

## 整體架構

```
                    ┌─────────────┐
                    │   Browser   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    Nginx    │  統一入口 (port 80)
                    └──┬──────┬──┘
             /         │      │  /api/*  /admin/*
     ┌───────▼────┐    │  ┌───▼─────────────────┐
     │  Frontend  │    │  │      Backend         │
     │  (Vue SPA) │    │  │  (Django DRF)        │
     │  port 80   │    │  │  port 8000           │
     └────────────┘    │  └───────┬──────────────┘
                       │          │
                       │   ┌──────▼──────┐
                       │   │ PostgreSQL  │
                       │   │  port 5432  │
                       │   └─────────────┘
                       │
              (開發環境) Vite Dev Server port 5173
```

## 後端分層

```
HTTP Request
    ↓
Nginx
    ↓
Django Middleware Stack:
  SecurityMiddleware
  CSPMiddleware        ← Content-Security-Policy 標頭（第三方套件 django-csp）
  CorsMiddleware       ← 開發環境 CORS
  SessionMiddleware
  AuthenticationMiddleware
    ↓
DRF:
  Authentication       ← JWT Bearer token 驗證
  Permission           ← IsAuthenticated / IsAdminUser
  Throttling           ← AnonRateThrottle
  Exception Handler    ← apps/core/exceptions.py 統一格式
    ↓
View (APIView)         ← HTTP 關注點
    ↓
Service                ← 商業邏輯
    ↓
Model QuerySet / Manager ← 查詢邏輯（`User.objects.get_by_email(...)` 等）
    ↓
Django ORM             ← ORM 實作
    ↓
PostgreSQL
```

查詢邏輯集中於 Model 的 `QuerySet` / `Manager`，不另設 Repository 抽象層：
Django ORM 的 Manager/QuerySet 本身就是 Repository 模式的實作，多加一層只會造成
抽象洩漏與樣板程式碼增加，詳見 [ADR-002](adr/ADR-002-remove-repository-layer.md)。

## JWT 認證流程

與 dotnet 版完全相同邏輯：
- Access Token（15 分鐘）→ JSON body → Pinia store（記憶體）
- Refresh Token（7 天）→ httpOnly cookie（Set-Cookie）
- Rotation：每次 refresh，舊 token 加入黑名單（`rest_framework_simplejwt.token_blacklist`）

## Django Apps 結構

```
apps/
├── core/          # 共用工具（exceptions, pagination）
└── accounts/      # 使用者認證
    ├── models.py        ← Custom User + UserQuerySet / UserManager（查詢邏輯）
    ├── serializers.py   ← DRF Serializers
    ├── views.py         ← APIView
    ├── services.py      ← 商業邏輯
    └── urls/
        ├── auth.py      ← /api/v1/auth/
        └── users.py     ← /api/v1/users/
```

## 健康檢查

| 端點 | 用途 | 檢查內容 |
|------|------|---------|
| `GET /api/health/` | Liveness | 無（process 存活即回 200，不觸碰 DB/cache） |
| `GET /api/health/ready/` | Readiness | DB 連線（`health_check.Database`）＋ cache 連線（`health_check.Cache`） |

兩個端點皆以 `HealthCheckView(checks=[...])` 明確指定各自的檢查清單（見
`config/urls.py`），不依賴 django-health-check 已棄用的 `health_check.urls` /
`MainView` + `HEALTH_CHECK["SUBSETS"]` 機制。

## API 文件

開發環境（`DEBUG=True`）下才掛載，正式環境不暴露以縮小攻擊面：

| 端點 | 內容 |
|------|------|
| `GET /api/schema/` | drf-spectacular 產生的 OpenAPI schema（JSON） |
| `GET /api/scalar/` | Scalar UI，讀取上述 schema 渲染互動式 API 文件 |
