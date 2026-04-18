# 開發環境設定指南

## 前置需求

| 工具 | 版本 | 用途 |
|------|------|------|
| Docker Desktop | 4.x+ | 執行所有服務 |
| make | any | 指令捷徑 |
| Git | 2.x+ | 版本控制 |
| uv | latest | Python 套件管理（首次初始化用） |
| pnpm | 9+ | 前端套件管理（首次初始化用） |

## 快速啟動

```bash
# 1. 設定環境變數
cp .env.example .env
# 填入 SECRET_KEY、DB_PASSWORD、JWT_SIGNING_KEY

# 2. 初始化 lockfiles（首次，確保 CI frozen install 可正常運行）
cd src/backend && uv sync && cd ../..
cd src/frontend && pnpm install && cd ../..

# 3. 啟動服務
make dev-build

# 3. 套用 Migration（首次啟動）
make migrate
```

## 服務端點

| 服務 | URL |
|------|-----|
| 應用程式 | http://localhost |
| API Swagger | http://localhost/api/schema/swagger-ui/ |
| Django Admin | http://localhost/admin/ |
| 健康檢查 | http://localhost/api/health/ |

## 常用指令

```bash
make dev           # 啟動開發環境
make dev-build     # 重新 build 後啟動
make stop          # 停止服務
make clean         # 停止並清除 volumes（慎用！）
make test          # 執行所有測試
make migrate       # 套用 Migration
make migration APP=accounts NAME=add_field  # 新增 Migration
make superuser     # 建立 Django 超級使用者
make lint          # Ruff + Mypy 檢查
make logs          # 查看即時 logs
```

## 環境變數說明

| 變數 | 必填 | 說明 |
|------|------|------|
| `SECRET_KEY` | 是 | Django SECRET_KEY，50 字元以上隨機字串 |
| `DB_PASSWORD` | 是 | PostgreSQL 密碼 |
| `JWT_SIGNING_KEY` | 是 | JWT 簽署金鑰，至少 32 字元 |
| `ALLOWED_HOSTS` | 開發預設 `localhost,127.0.0.1` | 生產未設即 fail-fast（避免 host-header 攻擊） |

> 生產專用覆寫（`REDIS_URL` / `HSTS_SECONDS` / `HSTS_PRELOAD` / `LANGUAGE_CODE` / `TIME_ZONE` / `GUNICORN_WORKERS` / `GUNICORN_TIMEOUT`）見 [deployment.md](deployment.md#生產環境變數)。

## 新增 Django App

```bash
# 在 apps/ 下新增 app
docker compose run --rm backend python manage.py startapp myapp apps/myapp

# 加入 LOCAL_APPS（config/settings/base.py）
LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.myapp",   # 新增
]

# 建立 Migration
make migration APP=myapp NAME=initial
make migrate
```
