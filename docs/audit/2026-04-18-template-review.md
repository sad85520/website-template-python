# Template Audit — 2026-04-18

**Scope**: `website-template-python` (全 repo)
**Reviewers**: security-reviewer / python-reviewer / typescript-reviewer / architect
**Sibling repo**: `website-template-dotnet`（對稱性審核已完成，評分 4.2/5）

## P0 Critical — 立即修

### #1 `src/backend/.env` 被 commit
- 檔案：[src/backend/.env](../../src/backend/.env)
- 內容：`SECRET_KEY=ci-secret-key-not-used-in-production`、`DB_PASSWORD=testpassword`、`JWT_SIGNING_KEY=ci-jwt-key-not-used-in-production-32chars`
- `.gitignore:36` 已列 `src/backend/.env`，代表是在 ignore rule 加入前就 commit
- 修法：
  ```bash
  git rm --cached src/backend/.env
  # 如果曾 push 到 remote，rotate 上述所有憑證
  ```

### #2 `src/backend/.venv/` 整包被 commit
- 檔案：`src/backend/.venv/`（含 `site-packages`）
- `.gitignore` 未列 `.venv/`
- 修法：
  ```bash
  # 補 .gitignore
  echo ".venv/" >> .gitignore
  echo "src/backend/.venv/" >> .gitignore
  # 移除追蹤
  git rm -r --cached src/backend/.venv
  ```

## P1 High

### #3 所有 Dockerfile 未設 non-root USER（both repos）
- 檔案：`src/backend/Dockerfile`、`src/frontend/Dockerfile`
- 修法：runtime stage 加 `RUN useradd --no-create-home --shell /bin/false appuser` + `USER appuser`

### #4 Base image 用浮動 tag（both）
- `src/backend/Dockerfile:4` — `ghcr.io/astral-sh/uv:latest`
- `src/frontend/Dockerfile` — `node:22-alpine`、`nginx:alpine`
- 修法：pin 到 version + digest

### #5 nginx.spa.conf 缺安全 headers（both）
- 檔案：`src/frontend/nginx.spa.conf`
- 缺：CSP、HSTS、X-Frame-Options、X-Content-Type-Options
- 修法：複製 `infra/nginx/nginx.conf` L23–28 的 header block

### #6 `infra/nginx/nginx.conf` CSP 含 `unsafe-inline`（both）
- 檔案：`infra/nginx/nginx.conf:27`
- 修法：移除 `'unsafe-inline'`

### #9 `CACHES` 未設 → DRF throttling 在多 worker 下失效
- 檔案：`src/backend/config/settings/base.py`
- 問題：`health_check.cache` 在 INSTALLED_APPS、`DEFAULT_THROTTLE_RATES` 已啟用，但沒有定義 `CACHES`，預設 `LocMemCache` 在多 gunicorn worker 下各有獨立 counter
- 修法：`base.py` 加 `CACHES`（預設 LocMemCache），`production.py` override 為 `django-redis`

### #10 `production.py` 無 `ALLOWED_HOSTS` override
- 檔案：`src/backend/config/settings/production.py`
- 問題：`base.py` 有預設 `localhost,127.0.0.1`，prod 漏設時不會 fail-fast
- 修法：
  ```python
  ALLOWED_HOSTS: list[str] = config(
      "ALLOWED_HOSTS",
      cast=lambda v: [s.strip() for s in v.split(",")],
  )  # 無 default，漏設即 fail
  ```

### #11 Dockerfile 無 `HEALTHCHECK` + gunicorn workers 硬編
- 檔案：`src/backend/Dockerfile:46`
- 修法：
  ```dockerfile
  HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
      CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health/')"

  CMD ["sh", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-4} --timeout ${GUNICORN_TIMEOUT:-60}"]
  ```

### #12 前端缺 `RegisterForm.vue`
- 檔案：`src/frontend/src/components/auth/`
- 對照：dotnet 側有 `LoginForm.vue` + `RegisterForm.vue`
- 修法：從 dotnet 側移植，調整型別為 snake_case DRF 格式

### #13 ESLint 未啟用 type-checked rules（both frontend）
- 檔案：`src/frontend/eslint.config.js`
- 修法：`parserOptions.project: true` + `tsPlugin.configs['flat/recommended-type-checked']`

### #14 `@typescript-eslint/no-explicit-any` 設為 `warn`（both frontend）
- 檔案：`src/frontend/eslint.config.js:26`
- 修法：改為 `error`

### #15 k8s readinessProbe 路徑不符
- 檔案：`infra/k8s/backend/deployment.yml`
- 問題：`readinessProbe.path` 仍為 `/api/health/`，README L354 宣告為 `/api/health/ready/`
- 修法：改為 `/api/health/ready/`

### Extra: `fetchCurrentUser` 無 null guard（frontend）
- 檔案：`src/frontend/src/stores/auth.store.ts:83`
- 對照：dotnet 版有 `if (response.data.success && response.data.data)` guard
- 修法：補 guard

## P2 Medium

### `get_by_email` / `get_by_email_for_auth` 重複且誤導
- 檔案：`src/backend/apps/accounts/models.py:18-29`
- 問題：兩方法行為相同但 docstring 聲稱不同（一個跳過 disabled users 但未實作）
- 修法：要麼 `get_by_email` 加 `is_active=True` filter，要麼合併

### `SECURE_HSTS_PRELOAD = True` 缺失
- 檔案：`src/backend/config/settings/production.py:27-30`
- 修法：加 `SECURE_HSTS_PRELOAD = True`

### `SECURE_HSTS_SECONDS` 預設 1 年過長
- 檔案：`src/backend/config/settings/production.py:27`
- 修法：`int(config("HSTS_SECONDS", default=3600))`，註解指示穩定後調高

### `structlog` 僅在 production.py 配置
- 檔案：`src/backend/pyproject.toml:14`、`config/settings/*.py`
- 修法：把 `structlog.configure()` 抽到 shared logging 模組，dev/prod 共用

### `conftest.py` 缺失，fixtures 重複
- 檔案：`src/backend/` 根
- 問題：`test_auth.py:19` 與 `test_users.py:17` 各有 `client` fixture
- 修法：抽到 `conftest.py`

### `bandit` / `pre-commit` 缺失
- 檔案：`src/backend/pyproject.toml:20`、根目錄 `.pre-commit-config.yaml`
- 修法：加 `bandit` 到 dev deps；加 `.pre-commit-config.yaml`（ruff + ruff-format + mypy）

### `assert isinstance(request.user, User)` 用於 production 控制流
- 檔案：`src/backend/apps/accounts/views.py:149`
- 問題：`python -O` 下會被移除
- 修法：改 `if not isinstance(...): raise AuthenticationFailed(...)` 或用 `cast()`

### `UserFactory` 預設密碼硬編於多處
- 檔案：`src/backend/apps/accounts/tests/factories.py:18` + `test_auth.py:35,46,73`
- 修法：抽 `DEFAULT_PASSWORD` 常數

### GitHub Actions `contents: write` 過寬（both）
- 檔案：`.github/workflows/cd.yml:73`、`cd-production.yml:26`
- 修法：branch protection + 拆 job

### CI test credentials 明文在 workflow（python）
- 檔案：`.github/workflows/ci.yml:68-76`
- 修法：移到 GitHub Actions secrets 或 `test.env`，或加 `.gitleaksignore`

### `tsconfig.node.json` include 含不存在檔案（both frontend）
- 檔案：`src/frontend/tsconfig.node.json:17`
- 修法：移除 `tailwind.config.ts`、`postcss.config.js`

### `vitest.config.ts` coverage 無 threshold（both frontend）
- 修法：加 `coverage.thresholds.lines: 80`

## P3 Low

### `migration 0001_initial` `created_at` 缺 `db_index`
- 檔案：`src/backend/apps/accounts/migrations/0001_initial.py:29`
- 問題：`Meta.ordering = ["-created_at"]` 每次查詢都排序
- 修法：model 加 `db_index=True`，生 migration

### `ruff format` 未設定
- 檔案：`src/backend/pyproject.toml:31`
- 修法：加 `[tool.ruff.format]` 區塊

### `LANGUAGE_CODE = "zh-hant"` 硬編
- 檔案：`src/backend/config/settings/base.py:129`
- 修法：改 env var driven，或預設 `en-us`

### `uvicorn` 缺失但有 `ASGI_APPLICATION`
- 檔案：`src/backend/config/asgi.py`、`pyproject.toml:16`
- 修法：擇一 — 移除 `ASGI_APPLICATION`，或加 `uvicorn[standard]` + 切換 CMD

### HSTS 送在 HTTP-only 監聽器（both）
- 檔案：`infra/nginx/nginx.conf:28`
- 修法：移到 `:443` block 或註解說明上游 TLS

### `Dockerfile.dev` 非獨立可運行（both）
- 修法：加註解或 `VOLUME` 指令
