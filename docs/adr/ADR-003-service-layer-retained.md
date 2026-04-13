# ADR-003：保留 Service 層，負責跨 Model 業務邏輯

- **狀態**：Accepted
- **日期**：2026-04-12
- **相關 ADR**：[ADR-002](./ADR-002-remove-repository-layer.md)

## 背景

[ADR-002](./ADR-002-remove-repository-layer.md) 決定移除 Repository 抽象層。自然衍生的問題是：**Service 層是否也該一併移除？**

Django 社群對 Service 層有兩種主流觀點：

1. **Fat Model 派**：業務邏輯放 Model 或自訂 Manager，View 直接呼叫 Model 方法
2. **Service 層派**：跨 Model 的協調邏輯放 Service，View 呼叫 Service

兩派都有大型生產案例支持，需明確記錄本範本的選擇。

## 決策

**保留 Service 層**，負責以下職責：

### Service 層職責
1. **跨 Model 的業務邏輯**：如「註冊使用者 + 建立歡迎 email 任務 + 發送通知」
2. **事務邊界控制**：使用 `transaction.atomic()` 包裝多步驟操作
3. **外部服務整合**：呼叫 email 服務、支付 gateway、第三方 API
4. **複雜業務規則**：如帳號鎖定邏輯、登入失敗計數、token rotation
5. **權限/存取控制檢查**（補強 DRF permissions 的細粒度判斷）

### 不屬於 Service 層的職責
- 簡單 CRUD → 直接在 View 用 `User.objects.xxx()` 或 Generic Views
- 單一 Model 的查詢邏輯 → 自訂 Manager / QuerySet 方法
- 欄位層級驗證 → Serializer 的 `validate_xxx` 方法
- HTTP 層的參數解析 → View 本身

## 考慮過的方案

### 方案 A：Fat Model（移除 Service 層）
```python
class User(AbstractBaseUser):
    def login(self, password):
        if self.is_locked():
            raise AccountLockedError()
        if not self.check_password(password):
            self.record_failed_attempt()
            raise InvalidCredentialsError()
        self.reset_failed_attempts()
        return generate_tokens(self)
```
- ✅ Django 傳統做法，新手熟悉
- ✅ 程式碼更少
- ❌ 單一 Model 塞入太多業務邏輯，違反 SRP
- ❌ 跨 Model 邏輯（如 User + RefreshToken 協調）無處安放
- ❌ 事務邊界與業務邏輯混雜
- ❌ 難以測試（需 mock Django ORM）

### 方案 B：View 層直接處理業務邏輯
```python
class LoginView(APIView):
    def post(self, request):
        # 驗證、登入、生成 token、回應 全部在這裡
        ...
```
- ✅ 最少抽象
- ❌ View 膨脹，違反 SRP
- ❌ 業務邏輯與 HTTP 層耦合，無法在其他情境（CLI、background job）重用
- ❌ 測試需透過 HTTP client，較慢

### 方案 C：保留 Service 層（採用）
- ✅ 業務邏輯與 Model 解耦，可重用於 HTTP、CLI、Celery task
- ✅ 測試容易：Service 是純 Python class，可直接實例化
- ✅ 事務邊界清晰（`@transaction.atomic` 裝飾 Service 方法）
- ✅ View 只負責 HTTP concerns，Serializer 只負責序列化，責任分明
- ❌ 比 Fat Model 多一層抽象
- ❌ 對極簡專案可能過度設計

## 採納理由

Service 層的價值與 Repository 層不同：

- **Repository 層**：Django ORM 已實作，重複多餘 → 移除
- **Service 層**：Django 未提供「跨 Model 業務邏輯協調」的明確位置 → 需要

本範本的 `AuthService` 是最佳例子。它需要：
1. 驗證密碼（User 相關）
2. 檢查帳號鎖定（User 相關）
3. 更新失敗計數（User 相關）
4. 生成 JWT（不屬於任何 Model）
5. 建立 RefreshToken 並處理舊 token rotation（RefreshToken 相關）
6. 包裝成事務

這些邏輯**無法合理放入任何單一 Model**。若強行塞進 `User.login()`，`User` Model 會變成上帝物件，且無法處理跨 Model 事務。

Service 層提供了「**比 Model 更高一層的業務協調點**」，這是 Django 刻意留白的設計空間。

## 影響範圍

### 保留
- `apps/accounts/services.py` 完整保留
- `AuthService`、`UserService`、`TokenService` 類別
- Service 的依賴注入機制（不過實際上 Django 不太需要 DI 容器，直接 import 即可）

### 調整
- Service 內部移除 Repository 呼叫，改為直接 `Model.objects.xxx()`
- Service 方法明確標註 `@transaction.atomic` 於需要事務的地方
- Service 構造不再接受 Repository 參數

### 測試策略
```python
@pytest.mark.django_db
class TestAuthService:
    def test_login_success(self):
        user = UserFactory(email="test@example.com", password="pass123")
        service = AuthService()
        access, refresh = service.login(email="test@example.com", password="pass123")
        assert access is not None
        assert refresh is not None
```
使用真實 Model + transactional test，無需 mock。

## 什麼時候應該重新考慮此決策？

1. 若專案僅有單純 CRUD，Service 層會退化為「只呼叫一個 Model 方法」的薄層 → 可移除
2. 若團隊偏好 Fat Model 風格且專案規模小 → 可移除
3. 若改用 Django Ninja 或 FastAPI 等框架，業務邏輯組織方式會不同 → 需重新評估

## 後續行動

- [ ] 重構 `apps/accounts/services.py` 移除 Repository 依賴
- [ ] 為 Service 方法明確標註事務邊界
- [ ] 新增 Service 層單元測試（使用 `@pytest.mark.django_db`）
- [ ] 在 `docs/architecture.md` 更新分層圖，移除 Repository，保留 Service

## 參考資料

- [Hacksoft: Django Styleguide - Services](https://github.com/HackSoftware/Django-Styleguide#services)
- [Two Scoops of Django: Business Logic](https://www.feldroy.com/books/two-scoops-of-django-3-x)
- [ADR-002](./ADR-002-remove-repository-layer.md)
