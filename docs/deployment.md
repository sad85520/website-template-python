# 部署指南

## Docker Compose 生產部署

```bash
# 1. 設定環境變數
cp .env.example .env
# 填入 SECRET_KEY、DB_PASSWORD、JWT_SIGNING_KEY

# 2. 啟動生產環境
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 3. 套用 Migration（首次或有新 migration 時）
docker compose run --rm backend python manage.py migrate
```

## 容器安全與連接埠

兩個 image 皆以 **non-root** 執行，且 frontend container 對外監聽 **8080**，不是 80：

| Image | 執行使用者 | 容器埠 | Compose 映射到宿主 | 備註 |
|-------|-----------|--------|-------------------|------|
| backend | `appuser` (UID 1000) | 8000 | nginx 反代 | gunicorn 以 non-root 啟動；`GUNICORN_WORKERS` / `GUNICORN_TIMEOUT` 可用環境變數覆寫 |
| frontend | `nginx`（非 root） | 8080 | nginx 反代 | 改以 8080 讓 non-root 能 bind（1-1023 需 CAP_NET_BIND_SERVICE） |
| nginx (reverse proxy) | root | 80 | 80 | 對外入口仍是 `http://localhost` |

K8s `frontend-service` 以 `port: 80 → targetPort: 8080` 做轉發；對外 URL 不受影響。`backend` / `frontend` Deployment 皆帶 `securityContext.runAsNonRoot: true` 與 `capabilities.drop: [ALL]`；新增 Deployment 請沿用這份 template 以避免 PodSecurity `restricted` policy 拒絕調度。

**Readiness probe：**

- backend：`GET /api/health/ready/`（驗證 DB 可連線，正式流量才進來）
- frontend：`GET /`

## 生產環境變數

`config.settings.production` 的必填/可選覆寫如下，**`ALLOWED_HOSTS` 未設即 fail-fast**（避免上線後靜默接受任意 Host header）：

| 變數 | 必填 | 預設 | 用途 |
|------|------|------|------|
| `ALLOWED_HOSTS` | 是 | — | 逗號分隔；未設會在啟動時拋 `UndefinedValueError` |
| `SECRET_KEY` | 是 | — | Django SECRET_KEY |
| `JWT_SIGNING_KEY` | 是 | — | JWT 簽章 |
| `DB_*` | 是 | — | PostgreSQL 連線 |
| `REDIS_URL` | 建議 | 空字串（退回 LocMemCache） | 多 worker 下 DRF throttling 共享計數需 Redis，否則限流失效 |
| `HSTS_SECONDS` | 否 | `3600` | 首次部署預設 1 小時，穩定後再拉到 31536000（1 年） |
| `HSTS_PRELOAD` | 否 | `False` | 加入 Chrome HSTS preload list 後難以撤銷，確認無問題再設 `True` |
| `LANGUAGE_CODE` | 否 | `en-us` | 視產品語系調整 |
| `TIME_ZONE` | 否 | `UTC` | Logging / ORM 時區 |
| `GUNICORN_WORKERS` | 否 | `3` | 生產建議 `(2 × CPU) + 1` |
| `GUNICORN_TIMEOUT` | 否 | `60` | 單位秒 |

K8s ConfigMap/Secret 的分配見 `infra/k8s/configmap.yml` 與 `infra/k8s/secret.example.yml`。

## Kubernetes 部署

### 前置準備

```bash
# 1. 建立 namespace
kubectl apply -f infra/k8s/namespace.yml

# 2. 建立 Secret（從範本複製並填入 base64 值）
cp infra/k8s/secret.example.yml infra/k8s/secret.yml
# echo -n "your-value" | base64
kubectl apply -f infra/k8s/secret.yml

# 3. 套用 ConfigMap
kubectl apply -f infra/k8s/configmap.yml
```

### 部署應用程式

```bash
kubectl apply -f infra/k8s/database/
kubectl apply -f infra/k8s/backend/
kubectl apply -f infra/k8s/frontend/
kubectl apply -f infra/k8s/ingress.yml

# 查看狀態
kubectl get pods -n web-template
kubectl get services -n web-template
```

## CD 部署流程

| 階段 | 觸發方式 | Workflow |
|------|---------|---------|
| Staging | push to main 自動觸發 | `cd.yml` |
| Production | 手動觸發（QA 驗收通過後） | `cd-production.yml` |

**手動觸發 Production 部署：**
```bash
# 指定 SHA（推薦，確保部署正確版本）
gh workflow run cd-production.yml -f sha=<short-sha>

# 使用最新版本
gh workflow run cd-production.yml
```

也可在 GitHub Actions 頁面 → 選擇「CD — Deploy Production」→ 點「Run workflow」。

## GitHub Actions 設定

| Secret | 說明 |
|--------|------|
| `GITHUB_TOKEN` | 自動提供，用於 GHCR push |

## 修改 K8S Ingress 域名

編輯 [infra/k8s/ingress.yml](../infra/k8s/ingress.yml)，將 `app.example.com` 替換為實際域名。
