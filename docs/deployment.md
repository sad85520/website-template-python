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
