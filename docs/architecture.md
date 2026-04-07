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
Django ORM             ← 資料存取
    ↓
PostgreSQL
```

## JWT 認證流程

與 dotnet 版完全相同邏輯：
- Access Token（15 分鐘）→ JSON body → Pinia store（記憶體）
- Refresh Token（7 天）→ httpOnly cookie（Set-Cookie）
- Rotation：每次 refresh，舊 token 加入黑名單（`rest_framework_simplejwt.token_blacklist`）

## Django Apps 結構

```
apps/
├── core/          # 共用工具（responses, exceptions, pagination）
└── accounts/      # 使用者認證
    ├── models.py      ← Custom User（email-based）
    ├── serializers.py ← DRF Serializers
    ├── views.py       ← APIView
    ├── services.py    ← 商業邏輯
    └── urls/
        ├── auth.py    ← /api/v1/auth/
        └── users.py   ← /api/v1/users/
```
