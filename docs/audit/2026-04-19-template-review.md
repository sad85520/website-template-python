# Template Audit — 2026-04-19

**Scope**: `website-template-python`（全 repo，含 backend / frontend / infra / CI）
**Reviewers**: python-reviewer / typescript-reviewer / security-reviewer
**Basis**: 2026-04-18 audit 之後的 refactor（Repository 層移除、snake_case 對齊、shared structlog 等）完成後做的全新 independent scan；舊 finding 大致都已閉，本檔只列 NEW 發現
**Sibling repo**: `website-template-dotnet`（2026-04-19 audit 獨立檔）

---

## P0 Critical

（無）

---

## P1 High

### Backend

#### #1 k8s 生產環境無 Redis，DRF throttling 在 HPA scale-out 後失效
- 檔案：[infra/k8s/configmap.yml](../../infra/k8s/configmap.yml)、[src/backend/config/settings/production.py:54](../../src/backend/config/settings/production.py)
- 問題：`production.py` 的 CACHES override 以 `if _redis_url:` 判斷，空字串時靜默 fallback 回 `LocMemCache`；`configmap.yml` 與 `secret.example.yml` 均未定義 `REDIS_URL`，HPA 多 replica 各自計數，`DEFAULT_THROTTLE_RATES` 限流額度被 N 倍放大
- 修法：`configmap.yml` 加 `REDIS_URL: "redis://redis-service:6379/0"` 並補 Redis Deployment/Service；或 `production.py` 在 `REDIS_URL` 未設定時 `raise ImproperlyConfigured`

#### #2 authenticated endpoints 完全未設 throttle
- 檔案：[src/backend/apps/accounts/views.py](../../src/backend/apps/accounts/views.py) `LogoutView:117` / `MeView:139` / `UserListView:155` / `UserDetailView:174`
- 問題：僅 `RegisterView`/`LoginView`/`TokenRefreshView` 套 `AnonRateThrottle`；已驗證端點完全無限流。`DEFAULT_THROTTLE_RATES.user = 120/minute` 已設但無 `DEFAULT_THROTTLE_CLASSES` 對應
- 修法：`REST_FRAMEWORK` 加 `"DEFAULT_THROTTLE_CLASSES": ["...AnonRateThrottle", "...UserRateThrottle"]`，或各 view 明示 `throttle_classes = [UserRateThrottle]`

#### #3 Dockerfile.dev 用浮動 `uv:latest` tag
- 檔案：[src/backend/Dockerfile.dev:8](../../src/backend/Dockerfile.dev)
- 問題：prod Dockerfile 已 pin 至 `uv:0.5.11`，dev image 仍用 `ghcr.io/astral-sh/uv:latest`，dev / CI 行為可能不一致
- 修法：改為 `COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/`

#### #4 `login_user` lockout 設定路徑無 `transaction.atomic` 保護
- 檔案：[src/backend/apps/accounts/services.py:65-76](../../src/backend/apps/accounts/services.py)
- 問題：`F("failed_login_attempts") + 1` 原子遞增正確，但 `refresh_from_db` + `if >= MAX` + `update(lockout_until=...)` 三步非原子；高並發下可能覆蓋 lockout 時間
- 修法：整包 `with transaction.atomic():`，或改 `filter(...).update(lockout_until=...)` 條件式單次寫入

### Frontend

#### #5 `client.ts:64` 對 `error.config` 直接寫 `_retry`，config 可能 undefined
- 檔案：[src/frontend/src/api/client.ts:64](../../src/frontend/src/api/client.ts)
- 問題：`originalRequest._retry = true` — network error 無 response 時 `error.config` 為 `undefined`，runtime 拋 `Cannot set properties of undefined`
- 修法：`if (!originalRequest) return Promise.reject(error)` 先守；並 `as InternalAxiosRequestConfig & { _retry?: boolean }` 標註型別

#### #6 `fetchCurrentUser` 拋錯未被 `login` / `tryRefreshToken` 捕捉
- 檔案：[src/frontend/src/stores/auth.store.ts:50,95](../../src/frontend/src/stores/auth.store.ts)
- 問題：`/users/me` 失敗時 rejection bubble 到 `useAuth`，UI 無 notification；`tryRefreshToken` 路徑會誤判 refresh 失敗
- 修法：`await fetchCurrentUser()` 在 login/tryRefresh 內各自 try/catch，或讓 `fetchCurrentUser` 內部吞錯不 throw

#### #7 `authApi.register` 的 generic 型別與 store 實際回傳值不符
- 檔案：[src/frontend/src/api/auth.ts:6](../../src/frontend/src/api/auth.ts)、`src/frontend/src/components/auth/RegisterForm.vue`
- 問題：`apiClient.post<UserDto>` 但 store 層丟棄 `UserDto` 以 `AuthResult` 回傳；下游 fork 時容易誤用
- 修法：對齊 generic 到 store 實際暴露的 `AuthResult`，或補充註解說明兩層契約

#### #8 `AppHeader` 內部的 `useAuth()` 每次 mount 重建 router reference（低優先）
- 檔案：[src/frontend/src/components/layout/AppHeader.vue:49](../../src/frontend/src/components/layout/AppHeader.vue)
- 問題：`useAuth` 內部呼叫 `useRouter`/`useRoute`；`AppHeader` 只需 `isAuthenticated` + `logout`
- 修法：直接用 `useAuthStore` 取 `isAuthenticated`，`logout` 以事件向外 emit

### Security / Infra

#### #9 GitHub Actions 第三方 action 全部 semver tag，未 pin SHA
- 檔案：[.github/workflows/ci.yml](../../.github/workflows/ci.yml)、[cd.yml](../../.github/workflows/cd.yml)、[cd-production.yml](../../.github/workflows/cd-production.yml)
- 問題：`actions/checkout@v4` 等 mutable tag 若被 force-push 覆蓋（惡意或誤操作），CI 會自動執行被竄改的 action，可讀 `secrets.*`
- 修法：改為 `uses: actions/checkout@11bd71901bbe... # v4.2.2` 形式固定完整 SHA；用 `pinact` 或 Dependabot 自動維護

#### #10 k8s backend/frontend pod `readOnlyRootFilesystem: false`
- 檔案：[infra/k8s/backend/deployment.yml:25](../../infra/k8s/backend/deployment.yml)、[infra/k8s/frontend/deployment.yml:26](../../infra/k8s/frontend/deployment.yml)
- 問題：容器 root fs 可寫，RCE 後攻擊者可持久化工具。Django runtime 不需寫 `/app`，`/tmp` 可用 emptyDir
- 修法：設 `readOnlyRootFilesystem: true` + 必要路徑 emptyDir volume

#### #11 k8s pod 全部未設 `seccompProfile`
- 檔案：`infra/k8s/backend/deployment.yml`、`infra/k8s/frontend/deployment.yml`、`infra/k8s/database/deployment.yml`
- 問題：容器可呼叫全部 Linux syscall；k8s 1.27+ 雖預設 `RuntimeDefault`，明示才能保證跨叢集一致
- 修法：`spec.template.spec.securityContext.seccompProfile: { type: RuntimeDefault }`

#### #12 k8s database pod 完全無 securityContext（root 執行）
- 檔案：[infra/k8s/database/deployment.yml](../../infra/k8s/database/deployment.yml)
- 問題：postgres pod 以 root 執行。雖文件建議 managed service，k8s manifest 仍作為 template 被複製
- 修法：加 `securityContext: { runAsNonRoot: true, runAsUser: 999, allowPrivilegeEscalation: false, capabilities: { drop: [ALL] } }`

#### #13 k8s Ingress 無 TLS 設定、無 HTTPS redirect
- 檔案：[infra/k8s/ingress.yml](../../infra/k8s/ingress.yml)
- 問題：只有 HTTP rules，`nginx.conf` 發的 HSTS header 在 HTTP 上無效。downstream 使用者可能誤以為 TLS 已處理
- 修法：加 `tls` 區段引用 cert-manager Secret + `nginx.ingress.kubernetes.io/ssl-redirect: "true"`

---

## P2 Medium

### Backend

- **#14 CI Postgres 18 vs dev/k8s 16 版本不一致** — [ci.yml:64](../../.github/workflows/ci.yml) vs [docker-compose.yml:3](../../docker-compose.yml)；統一 `postgres:16-alpine`
- **#15 k8s backend 缺 migrate initContainer** — rolling deploy 時新 pod 直接啟 gunicorn；加 `initContainers` 跑 `migrate --noinput`
- **#16 Django 未設 `SECURE_REFERRER_POLICY`** — nginx 有設但繞過 nginx 的 k8s 內部測試會漏；[production.py](../../src/backend/config/settings/production.py) 加 `SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"`
- **#17 `refresh_access_token` 未驗證 `is_active`** — [services.py:112-115](../../src/backend/apps/accounts/services.py)：停用帳號持有效 refresh token 仍能換新 access token（最多 7 天）；加 `if user is None or not user.is_active: raise ValueError`
- **#18 `display_name` 未 strip 驗證** — [serializers.py:23](../../src/backend/apps/accounts/serializers.py)：`"  "` 可通過；`validate_display_name` 做 strip + empty check
- **#19 `structlog.configure` 的 `cache_logger_on_first_use=True` 鎖定 processor chain** — [config/logging.py:51](../../src/backend/config/logging.py)：下游若重 configure 會被靜默忽略；加 `if not structlog.is_configured()` guard

### Frontend

- **#20 `HomeView.vue:7` 副標誤寫 "Vue 3 + .NET 9"**（從 dotnet template 複製忘改）— 應為 "Vue 3 + Django REST Framework"
- **#21 API docs 連結 `/scalar/` trailing slash 與 dotnet 不一致** — [HomeView.vue:26](../../src/frontend/src/views/HomeView.vue)
- **#22 `vite.config.ts:15` `host: '0.0.0.0'` 無 `allowedHosts`** — Vite 5+ 的 DNS rebinding 保護未啟用
- **#23 `NotificationContainer.vue:11` dismiss button 無 `aria-label`** — 螢幕閱讀器只念 `✕`
- **#24 `BaseInput.vue` `required` prop 未宣告**（靠 `$attrs` 傳遞）— 應在 Props 介面明示
- **#25 `tests/unit/stores/auth.test.ts` 大量 `as any` 繞過 mock 型別** — 改 `satisfies AxiosResponse<LoginResponse>` 型別守門
- **#26 `notification.store.ts:23` `setTimeout` ID 未保存** — 無法 `clearTimeout` 造成 SPA timer leak
- **#27 `ui.store.ts:17` 對 `document.documentElement` 直接存取，SSR 不安全** — 加 `typeof document !== 'undefined'` guard
- **#28 `router/index.ts` `RouteMeta` 未 augmentation** — `to.meta.requiresAuth` 為 `unknown`，下游開發無型別提示；補 `declare module 'vue-router'`
- **#29 `BaseInput.vue` 錯誤訊息無 `aria-describedby` 連到 input** — 螢幕閱讀器不會念錯誤

### Security / Infra

- **#30 `.env` 存在 working tree 且值為固定字串（非 placeholder）** — dev key 若被多人共用變相成「已知 key」；README 要求以 `python -c "import secrets; print(secrets.token_hex(32))"` 個人產生
- **#31 nginx HSTS header 設在 `listen 80` server block（RFC 6797 §8.1 瀏覽器會忽略）** — [nginx.conf:38](../../infra/nginx/nginx.conf)；移到 ingress/CDN 或 `:443` block，HTTP 層刪除
- **#32 `production.py:39` `SECURE_HSTS_SECONDS` 預設 3600（1 小時）過低** — 起手值改 86400，comment 說明穩定後調至 31536000
- **#33 k8s backend 無 `fsGroup`** — 未來 volume 掛載時 root 擁有造成 uid 1000 `appuser` 無法寫入；pod-level `securityContext.fsGroup: 1000`

---

## P3 Low

- **#34 進一步 runtime hardening**：`readOnlyRootFilesystem: true`（同 #10）
- **#35 `Dockerfile.dev` base image 未 pin digest** — [Dockerfile.dev:8](../../src/backend/Dockerfile.dev) `python:3.12-slim` 無 digest；用 Dependabot/Renovate，或至少 pin `bookworm`
- **#36 `pyproject.toml` 依賴版本區間過寬** — `structlog>=24.0,<25.0` 等；收窄至 minor+patch，與 `uv.lock` 對齊
- **#37 `urls.py:27` Scalar UI CDN script 無 SRI** — 加 `integrity=...` 或固定到含版本號的 URL
- **#38 `.gitignore` 中 `.mypy_cache/` 未以 `**/.mypy_cache/` 涵蓋子目錄**
- **#39 `gitleaks-action@v2` tag 未固定**（同 #9 子問題）

---

## Cross-repo shared issues（與 website-template-dotnet 共通）

- **C1** GitHub Actions SHA pin（#9）
- **C2** k8s `readOnlyRootFilesystem: false` + 無 seccomp（#10/#11）
- **C3** Ingress 無 TLS（#13）
- **C4** nginx HSTS on :80（#31）
- **C5** `.env.example` 使用明文示範密碼（#30）
- **C6** `client.ts` `_retry` / `fetchCurrentUser` 錯誤處理（frontend #5/#6）
- **C7** `vite.config.ts` 無 `allowedHosts`（#22）
- **C8** `BaseInput` / `NotificationContainer` a11y / RouteMeta / ui.store SSR（#23–#28）

---

## 統計

| 嚴重度 | 件數 |
|--------|------|
| P0 | 0 |
| P1 | 13（backend 4 / frontend 4 / security 5） |
| P2 | 20（backend 6 / frontend 10 / security 4） |
| P3 | 6 |

**建議優先**：#17（安全語意錯誤）→ #1/#2（throttling 空洞）→ #5/#6（frontend runtime 崩潰）→ #9（supply chain）→ #4（TOCTOU）→ #15（migrate 空窗）
