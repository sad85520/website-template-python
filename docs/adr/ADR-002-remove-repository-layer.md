# ADR-002：移除 Repository 抽象層，採用 Django 習慣用法

- **狀態**：Accepted
- **日期**：2026-04-12
- **相關 ADR**：[ADR-001](./ADR-001-drf-native-response-format.md), [ADR-003](./ADR-003-service-layer-retained.md)

## 背景

本專案最初引入 Repository 抽象層（`apps/accounts/repositories.py`），包含 `IUserRepository` Protocol 與 `UserRepository` 實作。此設計從 .NET/Java 生態借鑒，動機是：

1. 讓 Service 層與 ORM 解耦
2. 測試時可 mock Repository
3. 集中查詢邏輯

然而在實際使用中浮現幾個問題：

1. **抽象洩漏**：`get_all()` 回傳 `QuerySet`，呼叫端仍可 `.filter().annotate()` 繞過 Repository 邊界
2. **重新發明輪子**：Django ORM 的 Manager/QuerySet 本身就是 Repository 模式的實作
3. **社群慣例衝突**：Django 社群標準做法是自訂 Manager（`User.objects.active()`），非獨立 Repository 類
4. **測試價值有限**：Django 測試生態（pytest-django + factory_boy）已優化為直接使用真實 ORM + transactional test，mock Repository 反而降低測試真實度
5. **樣板程式碼增加**：每個 Model 需多寫一個 Protocol + 一個 Class，新人看了困惑

## 決策

**移除所有 Repository 類別與 Protocol，改用 Django 習慣用法：**

### 1. 簡單查詢直接用 Manager
```python
# Service 層
user = User.objects.filter(email=email).first()
users = User.objects.active()  # 若有自訂 Manager
```

### 2. 複雜查詢定義為自訂 Manager / QuerySet 方法
```python
# apps/accounts/models.py
class UserQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True, lockout_until__isnull=True)

    def locked(self):
        return self.filter(lockout_until__gt=timezone.now())

class UserManager(BaseUserManager.from_queryset(UserQuerySet)):
    pass

class User(AbstractBaseUser):
    # ...
    objects = UserManager()
```

### 3. 跨 Model 的業務邏輯放在 Service 層
見 [ADR-003](./ADR-003-service-layer-retained.md)。

## 考慮過的方案

### 方案 A：維持 Repository 抽象層
- ✅ 與 .NET 範本結構一致
- ✅ Service 層可透過介面 mock
- ❌ 對抗 Django 框架設計
- ❌ 抽象洩漏（QuerySet 回傳）
- ❌ 新手困惑（Django 讀者不期待此模式）
- ❌ 樣板程式碼多 40%

### 方案 B：Repository 僅為「查詢集中地」，不試圖抽象 ORM
- ✅ 保留「集中查詢邏輯」的優點
- ❌ 與自訂 Manager 功能重複，選擇其一即可
- ❌ 在 Django 生態，Manager 是更自然的集中點

### 方案 C：移除 Repository，改用 Manager/QuerySet（採用）
- ✅ 符合 Django 社群慣例
- ✅ 查詢邏輯仍集中於 Model 相關位置
- ✅ 新人立刻看懂
- ✅ 測試可直接使用 factory_boy + transactional test
- ✅ 樣板程式碼減少
- ❌ 與 .NET 範本結構不同
- ❌ 現有程式碼需重構

## 採納理由

Django ORM 的設計哲學是「Model 即是業務物件 + 資料存取點」。Active Record 模式深植於 Django 的每個角落——從 `Model.objects.create()` 到 `Model.save()`，從 signals 到 Admin。強行套一層 Repository 等同於**用 .NET 的思維寫 Django**，不僅不會讓程式碼更乾淨，反而與整個生態的工具鏈（Django Admin、Django signals、DRF ModelSerializer、Django REST Framework viewsets）產生摩擦。

**更重要的是**，Django 測試生態已演化出比「mock Repository」更好的方案：

1. `pytest-django` 的 `@pytest.mark.django_db` 提供 transactional test，每個 test 自動 rollback
2. `factory_boy` 生成真實 Model 實例
3. In-memory SQLite 或 PostgreSQL 的測試 schema 提供近乎即時的測試速度

在此生態下，**直接測試真實 ORM 比 mock 更可靠、更快、更符合實際行為**。Repository mock 的價值在此被大幅削弱。

**一句話總結**：Django 已經幫你想好資料存取層的最佳實踐，不要再加一層。

## 影響範圍

### 移除
- `apps/accounts/repositories.py`（整檔刪除）
- `apps/accounts/tests/test_repositories.py`（如有）

### 修改
- `apps/accounts/models.py`：新增 `UserQuerySet` 與 `UserManager`
- `apps/accounts/services.py`：所有 `self._user_repo.xxx()` 呼叫改為 `User.objects.xxx()`
- `apps/accounts/services.py`：移除 Repository 依賴注入，Service 可直接存取 Model
- `config/urls.py` 或相關 DI 設定：移除 Repository 註冊

### 測試調整
- Service 單元測試改為 `@pytest.mark.django_db` 的整合風格測試
- 使用 `UserFactory` 建立真實 User 實例
- 不再需要 mock Repository

### 保留
- Service 層完整保留（見 ADR-003）
- Serializer 層完整保留
- 例外處理、分頁、認證等機制完整保留

## 什麼時候應該重新考慮此決策？

若專案出現以下情況，可重新評估：

1. 需同時支援 Django ORM + 外部資料源（如 MongoDB、REST API）
2. 有多個儲存後端需動態切換
3. 團隊決定完全脫離 Django ORM

上述情境下 Repository 模式仍有價值，但屬於「特殊需求」而非「預設做法」。

## 後續行動

- [ ] 刪除 `apps/accounts/repositories.py`
- [ ] 將 `UserRepository` 的查詢邏輯搬到 `UserQuerySet` / `UserManager`
- [ ] 重構 `apps/accounts/services.py` 移除 Repository 依賴
- [ ] 重寫 Service 層測試改為 `@pytest.mark.django_db` 風格
- [ ] 更新 `docs/architecture.md` 的分層圖
- [ ] README.md 移除「Repository」相關描述

## 參考資料

- [Django Docs: Making queries](https://docs.djangoproject.com/en/5.0/topics/db/queries/)
- [Django Docs: Managers](https://docs.djangoproject.com/en/5.0/topics/db/managers/)
- [Two Scoops of Django: Best Practices for Model Methods & Managers](https://www.feldroy.com/books/two-scoops-of-django-3-x)
- [website-template-dotnet ADR-001](../../../website-template-dotnet/docs/adr/ADR-001-module-based-architecture.md)（.NET 生態的相反決策）
