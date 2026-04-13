# ADR-001：API 回應遵循 Django/DRF 原生慣例 + RFC 7807

- **狀態**：Accepted
- **日期**：2026-04-12
- **相關 ADR**：[ADR-002](./ADR-002-remove-repository-layer.md)

## 背景

本專案最初採用跨語言統一的 `ApiResponse` 信封格式：

```json
{ "success": true, "data": {...}, "message": null, "errors": null }
```

此格式與姊妹專案 `website-template-dotnet` 一致，動機是讓前端 SDK 可跨後端共用同一個 parser。

然而在 2026-04-12 的架構評估中發現，此設計在 Django/DRF 生態下屬於「對抗框架」：

1. `apps/core/responses.py` 需手寫信封包裝層，重複 DRF 已有能力
2. `apps/core/exceptions.py` 的 `_flatten_validation_errors()` 只是在**還原** DRF `ValidationError` 本來就會產出的結構
3. 自訂 `StandardPagination` 覆寫 DRF 預設 `PageNumberPagination`，meta 欄位重新發明 `count/next/previous/results`
4. `drf-spectacular` 生成的 OpenAPI schema 與實際回應脫節，需額外維護
5. 新進 Django 開發者的肌肉記憶（`return Response(serializer.data)`）無法直接套用，學習成本升高

## 決策

**本範本的 API 回應格式改為遵循 Django/DRF 原生慣例：**

- **成功回應**：直接回傳序列化後的物件 + 對應 HTTP 狀態碼
  ```python
  return Response(serializer.data, status=status.HTTP_200_OK)
  ```
- **錯誤回應**：採用 [RFC 7807 Problem Details for HTTP APIs](https://datatracker.ietf.org/doc/html/rfc7807)，Content-Type 為 `application/problem+json`
  ```json
  {
    "type": "https://example.com/probs/validation-error",
    "title": "Validation failed",
    "status": 400,
    "detail": "One or more fields are invalid.",
    "errors": [
      { "field": "email", "message": "Enter a valid email address." }
    ]
  }
  ```
- **分頁回應**：改用 DRF 內建 `PageNumberPagination` 預設格式
  ```json
  { "count": 42, "next": "...", "previous": null, "results": [...] }
  ```

## 考慮過的方案

### 方案 A：維持 ApiResponse 信封（原狀）
- ✅ 與 `website-template-dotnet` 跨後端一致
- ❌ 對抗 DRF 框架設計，增加維護成本
- ❌ 誤導新進 Django 開發者的學習方向
- ❌ 與 drf-spectacular、DRF 分頁器、DRF 例外處理全線脫節

### 方案 B：混合（成功原生、錯誤仍用信封）
- ✅ 錯誤處理改動最小
- ❌ 前端仍需處理兩種 shape，沒有真正簡化
- ❌ 不符合任何生態慣例（既非 REST 也非 JSON-RPC）

### 方案 C：遵循 DRF 原生 + RFC 7807（採用）
- ✅ 符合 Django/DRF 社群慣例與新人預期
- ✅ 錯誤格式採用業界標準（RFC 7807），非團隊自創
- ✅ drf-spectacular、DRF 分頁、DRF 例外處理可直接發揮
- ✅ 與 Stripe、GitHub、Twilio 等成熟 API 設計一致
- ❌ 前端契約與 .NET 範本不一致，共用 SDK 需額外適配層
- ❌ 需要一次性改造 `core/responses.py`、`core/exceptions.py`、`core/pagination.py`、`accounts/views.py`

## 採納理由

範本的價值是**示範所屬生態的最佳實踐**，而非追求跨語言機械式一致。強迫 Django 寫 .NET 風格的信封，會：

1. 讓讀者帶著錯誤的肌肉記憶進入 Django 生態
2. 在每次接新函式庫時付出「對抗框架」的維護稅
3. 傳達錯誤的訊號：「一致性 > 慣用性」

跨專案的一致性應該體現在**工程紀律**（分層、測試、CI/CD、安全、註解品質），而非**語法層**的強制統一。

姊妹專案 `website-template-dotnet` 在 [ADR-002](../../../website-template-dotnet/docs/adr/ADR-002-api-response-envelope.md) 刻意採用相反決策（信封格式），因為 .NET 生態的心理模型完全不同。**兩個選擇都對**——只是針對不同生態。

## 影響範圍

### 程式碼變更
- 移除 `apps/core/responses.py`
- 重寫 `apps/core/exceptions.py`：`custom_exception_handler` 輸出 RFC 7807 格式，`Content-Type: application/problem+json`
- 重寫 `apps/core/pagination.py`：改繼承 `rest_framework.pagination.PageNumberPagination`，移除自訂 meta
- 調整 `apps/accounts/views.py`：移除 `ApiResponse.ok(...)` 包裝
- 更新 `docs/architecture.md` 的 API 回應範例

### 前端契約
- 若有前端正在消費本 API，需同步調整 response parser
- 錯誤處理器需識別 `application/problem+json` 回應

### 測試
- `apps/accounts/tests/test_auth.py` 等測試的 assertion 需改寫
- 新增 RFC 7807 錯誤格式的契約測試

### drf-spectacular 整合
- 改用 DRF 原生格式後，drf-spectacular 的自動 schema 生成可直接正確運作，無需覆寫

## 後續行動

- [ ] 實作 `apps/core/exceptions.py` 的 RFC 7807 轉換
- [ ] 移除 `apps/core/responses.py` 並修正所有 import
- [ ] 改寫 `apps/core/pagination.py`
- [ ] 更新所有 views 與測試
- [x] 撰寫 ADR-002（Repository 層移除）
- [ ] 更新 README.md 的 API 範例

## 參考資料

- [RFC 7807 - Problem Details for HTTP APIs](https://datatracker.ietf.org/doc/html/rfc7807)
- [Django REST Framework - Responses](https://www.django-rest-framework.org/api-guide/responses/)
- [Django REST Framework - Pagination](https://www.django-rest-framework.org/api-guide/pagination/)
- [website-template-dotnet ADR-002](../../../website-template-dotnet/docs/adr/ADR-002-api-response-envelope.md)（姊妹專案的相反決策）
