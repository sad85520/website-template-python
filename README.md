# website-template-python

現代前後端分離架構網站起手式 Template（Python 版）。

## 技術棧

| 層級 | 技術 |
|------|------|
| 前端 | Vue 3, TypeScript, Vite, Vue Router 4, Pinia, Tailwind CSS v4, Axios, Zod |
| 後端 | Python 3.12, Django 6.0, Django REST Framework |
| 資料庫 | PostgreSQL 16 |
| 認證 | JWT + Refresh Token (httpOnly cookie) |
| API 文件 | Scalar / drf-spectacular (OpenAPI) |
| 套件管理 | uv (Python), pnpm (前端) |
| 程式碼品質 | ESLint, Prettier, Vitest, Ruff, Mypy, pytest |
| 基礎設施 | Docker Compose, Nginx, GitHub Actions, Kubernetes |

## 快速啟動

### 前置需求

- Docker Desktop
- make（Windows：[GnuWin32](http://gnuwin32.sourceforge.net/packages/make.htm) 或 WSL）

### 步驟

```bash
# 1. 複製環境變數範本
cp .env.example .env

# 2. 編輯 .env 填入設定（至少修改 SECRET_KEY、DB_PASSWORD、JWT_SIGNING_KEY）

# 3. 啟動所有服務
make dev-build

# 4. 套用資料庫 Migration（首次啟動）
make migrate
```

開啟瀏覽器：
- 應用程式：http://localhost
- API 文件（Scalar）：http://localhost/api/scalar/
- 健康檢查：http://localhost/api/health/

## 目錄結構

```
website-template-python/
│
├── src/
│   ├── frontend/                        # Vue 3 前端（Vite + TypeScript）
│   └── backend/
│       ├── config/
│       │   ├── settings/
│       │   │   ├── base.py              # 共用設定（安裝的 App、Middleware、DRF 等）
│       │   │   ├── development.py       # 開發環境覆寫
│       │   │   └── production.py        # 正式環境覆寫
│       │   ├── urls.py                  # 全域路由入口（include 各 App urls）
│       │   └── wsgi.py / asgi.py
│       └── apps/
│           ├── core/                    # 跨 App 共用工具（不含業務邏輯）
│           │   ├── exceptions.py        # custom_exception_handler（RFC 7807 Problem Details）
│           │   └── pagination.py        # 共用分頁類別
│           └── accounts/               # 使用者與認證模組
│               ├── models.py            # Custom User + UserQuerySet / UserManager（查詢邏輯）
│               ├── serializers.py       # DRF Serializer（Request 驗證 / Response 格式）
│               ├── services.py          # 業務邏輯（登入、登出、refresh token）
│               ├── views.py             # DRF APIView（HTTP 端點）
│               ├── urls/
│               │   ├── auth.py          # /api/v1/auth/ 路由
│               │   └── users.py         # /api/v1/users/ 路由
│               ├── tests/               # pytest 測試
│               └── migrations/          # Django 自動產生的 Migration 檔
│
├── infra/
│   ├── nginx/                           # Nginx reverse proxy 設定
│   └── k8s/                             # Kubernetes manifests
├── .github/workflows/                   # GitHub Actions CI/CD
├── docs/                                # 架構、部署、開發環境說明文件
└── scripts/                             # 工具腳本
```

## 常用指令

```bash
make dev           # 啟動開發環境（前景）
make dev-d         # 啟動開發環境（背景）
make dev-build     # 重新 build 後啟動
make stop          # 停止服務
make clean         # 停止並清除 volumes（慎用！會刪除 DB 資料）
make test          # 執行所有測試
make migrate       # 套用 DB Migration
make migration APP=accounts NAME=add_field  # 新增 Migration
make superuser     # 建立 Django 超級使用者
make lint          # Ruff + Mypy 程式碼檢查
make logs          # 查看即時 logs
make ps            # 查看服務狀態
```

詳細說明請參考 [docs/dev-setup.md](docs/dev-setup.md)。

---

## 分層職責

```
HTTP Request
    ↓
Django Middleware Stack:
  SecurityMiddleware           ← HTTPS、安全標頭
  CSPMiddleware                ← Content-Security-Policy
  CorsMiddleware               ← 開發環境 CORS
  AuthenticationMiddleware     ← Session / JWT 識別
    ↓
DRF:
  Authentication               ← JWT Bearer token 驗證
  Permission                   ← IsAuthenticated / IsAdminUser
  Throttling                   ← 速率限制
  Exception Handler            ← 統一例外格式（apps/core/exceptions.py）
    ↓
View (APIView)                 ← 路由、參數驗證、呼叫 Service、回傳格式
    ↓
Service                        ← 業務邏輯（驗證規則、資料組合、計算）
    ↓
Model Manager / QuerySet       ← 查詢邏輯（User.objects.get_by_email(...) 等）
    ↓
Django ORM
    ↓
PostgreSQL
```

| 層 | 檔案 | 放什麼 | 不放什麼 |
|----|------|--------|---------|
| HTTP 層 | `views.py` | DRF APIView、權限、呼叫 Service、回傳格式 | 業務邏輯、ORM 查詢 |
| 業務邏輯 | `services.py` | 驗證規則、資料組合、計算 | 直接回 HTTP Response |
| 查詢邏輯 | `models.py` 的 `QuerySet` / `Manager` | 可鏈結的 ORM 查詢（`get_by_email`、`search`...） | 業務判斷 |
| 序列化 | `serializers.py` | Request 驗證、Response 格式 | 業務邏輯 |
| 資料模型 | `models.py` | Django Model（對應資料表） | 業務邏輯 |
| 路由 | `urls/` | URL 對應 View | 其他 |
| 共用工具 | `apps/core/` | 通用例外、分頁 | 業務邏輯 |

**規則：**
- View 不直接寫 ORM 查詢，統一呼叫 Service
- 查詢邏輯集中在 Model 的 `QuerySet` / `Manager`，不另設 Repository 層（見 [ADR-002](docs/adr/ADR-002-remove-repository-layer.md)）
- Service 不直接回傳 HTTP Response

## 共用工具

| 工具 | 位置 | 用途 |
|------|------|------|
| `custom_exception_handler` | `apps/core/exceptions.py` | 全域例外處理，輸出 RFC 7807 Problem Details |
| `StandardPagination` | `apps/core/pagination.py` | 分頁（`?page=1&page_size=20`） |
| `UserQuerySet` / `UserManager` | `apps/accounts/models.py` | 使用者查詢入口（`User.objects.get_by_email(...)`、`.search(...)`） |
| 登入 / 登出 / Refresh | `apps/accounts/services.py` | 業務邏輯（範本已實作） |

> 成功回傳採用 DRF 原生慣例、不再額外包 envelope；錯誤回傳採用 RFC 7807 Problem Details。詳見 [ADR-001](docs/adr/ADR-001-drf-native-response-format.md)。

```python
from rest_framework.exceptions import NotFound
from apps.accounts.models import User

# View 直接回傳 DRF Response，格式維持 DRF 原生慣例
return Response({"items": data, "total": count})

# 在 Service 中拋出 DRF 標準例外，由 custom_exception_handler 統一轉換為 Problem Details
raise NotFound("查無資料")

# 直接透過 Manager / QuerySet 查詢，不需另行注入 Repository
user = User.objects.get_by_email("test@example.com")
matches = User.objects.search("alice")
```

### QuerySet + `from_queryset()` 寫法

查詢邏輯寫在 `UserQuerySet`，再由 `BaseUserManager.from_queryset(UserQuerySet)` 自動複製到 Manager，避免手動 delegate 的樣板程式碼。`config/settings/base.py` 啟動時呼叫 `django_stubs_ext.monkeypatch()`，讓 `QuerySet[User]` 等泛型在執行期可訂閱，配合 django-stubs 讓 `User.objects.get_by_email(...)` 具備型別推導。

```python
class UserQuerySet(models.QuerySet["User"]):
    def get_by_email(self, email: str) -> "User | None":
        return self.filter(email=email).first()

class UserManager(BaseUserManager["User"].from_queryset(UserQuerySet)):  # type: ignore[misc]
    def create_user(self, email: str, password: str, **extra): ...
```

## 如何擴充這個專案

### 新增小功能（現有 App 內）

在 `accounts` app 新增「更新使用者頭像」為例：

**1. 新增 Serializer**（`apps/accounts/serializers.py`）
```python
class AvatarUpdateSerializer(serializers.Serializer):
    avatar_url = serializers.URLField()
```

**2. 擴充查詢邏輯**（`apps/accounts/models.py`，若需要新的可鏈結查詢方法）
```python
class UserQuerySet(models.QuerySet["User"]):
    # 在現有 QuerySet 內新增：
    def update_avatar(self, user_id, avatar_url: str) -> int:
        return self.filter(id=user_id).update(avatar=avatar_url)
```
> 若只是單次 `filter().update()`，通常可直接寫在 Service 裡，不需另外包方法。

**3. 新增 Service 函式**（`apps/accounts/services.py`）
```python
def update_avatar(user_id, avatar_url: str) -> bool:
    return User.objects.update_avatar(user_id, avatar_url) > 0
```

**4. 新增 View**（`apps/accounts/views.py`）
```python
class AvatarUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = AvatarUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        update_avatar(request.user.id, serializer.validated_data["avatar_url"])
        return Response({"message": "頭像已更新"})
```

**5. 新增路由**（`apps/accounts/urls/users.py`）
```python
path("me/avatar/", AvatarUpdateView.as_view(), name="avatar-update"),
```

### 新增大型功能（獨立 Django App）

若功能夠大（例如「訂單管理」），應建立新的 App：

**1. 建立 App**
```bash
# 在 Docker 環境內執行
docker compose exec backend python manage.py startapp orders
# 將產生的目錄移到 apps/orders/
mv orders src/backend/apps/orders
```

**2. 建立標準目錄結構**
```
apps/orders/
├── models.py            ← Model + OrderQuerySet / OrderManager
├── serializers.py
├── services.py
├── views.py
├── urls/
│   ├── __init__.py
│   └── orders.py
├── tests/
│   ├── __init__.py
│   └── test_orders.py
├── migrations/
│   └── __init__.py
└── apps.py
```

**3. 在 `config/settings/base.py` 加入**
```python
INSTALLED_APPS = [
    ...
    "apps.orders",
]
```

**4. 在 `config/urls.py` 加入路由**
```python
path("api/v1/orders/", include("apps.orders.urls.orders")),
```

**5. 建立 Migration**
```bash
make migration APP=orders NAME=initial
make migrate
```

### 寫測試

```bash
# 執行所有測試（後端 + 前端）
make test

# 只跑後端
docker compose exec backend pytest

# 只跑前端
cd src/frontend && pnpm test

make lint           # Ruff + Mypy 程式碼檢查
```

#### 後端測試

測試放在各 App 的 `tests/` 目錄下，參考 `apps/accounts/tests/test_auth.py` 作為範本：

```python
@pytest.mark.django_db
def test_login_success(client):
    user = UserFactory(email="test@example.com")
    res = client.post("/api/v1/auth/login/", {"email": "test@example.com", "password": "..."})
    assert res.status_code == 200


@pytest.mark.django_db
def test_login_wrong_password_returns_401(client):
    UserFactory(email="test@example.com")
    res = client.post("/api/v1/auth/login/", {"email": "test@example.com", "password": "wrong"})
    assert res.status_code == 401
```

**測試分層原則：**

| 測試對象 | 測試方式 | 原因 |
|---------|---------|------|
| Service | `@pytest.mark.django_db` + 真實 ORM | 業務邏輯在此，直接驗最有價值；Django 的 transactional test 已足夠快，mock ORM 反而讓測試與實際行為漂移 |
| QuerySet / Manager 方法 | `@pytest.mark.django_db` | 純查詢語意，連 DB 直接驗才有意義 |
| View | 整合測試（`pytest-django` client） | View 是薄的 HTTP 層，應測 routing、permission、throttling 的整體行為，而非 mock 後測呼叫順序 |

一個 `def test_xxx` 只驗一件事。

#### 前端測試

```bash
cd src/frontend
pnpm test        # 執行一次
pnpm test:watch  # 監看模式
```

測試放在 `src/frontend/tests/`，目錄結構鏡像 `src/` 下的程式碼位置：

```
tests/
├── setup.ts                    # 測試環境初始化
└── unit/
    └── stores/                 # 對應 src/stores/
        └── auth.test.ts
# 未來依需求建立：
# unit/api/          對應 src/api/（Axios client 行為）
# unit/composables/  對應 src/composables/（組合式函式邏輯）
# components/auth/   對應 src/components/auth/（@vue/test-utils render 測試）
```

> 測試目錄依需求新增，不預先建立空目錄。

---

## 健康檢查

| 端點 | 用途 |
|------|------|
| `GET /api/health/` | Liveness — 服務是否存活 |
| `GET /api/health/ready/` | Readiness — 資料庫是否可連線 |

> 兩個 image 皆 non-root（backend `appuser` UID 1000、frontend `nginx`），且 frontend container 對外監聽 8080（k8s Service 仍映射到 80）。生產環境變數（`ALLOWED_HOSTS` fail-fast、`REDIS_URL`、`HSTS_SECONDS` 等）與 k8s `securityContext` 細節見 [docs/deployment.md](docs/deployment.md)。

## API 文件

開發環境下，Scalar UI 可在 `/api/scalar/` 查看所有 API（由 drf-spectacular 自動產生 OpenAPI schema）。
