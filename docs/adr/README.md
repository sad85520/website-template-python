# Architecture Decision Records

本目錄記錄 `website-template-python` 範本的重要架構決策。每份 ADR 採用 MADR 簡化格式，包含背景、決策、考慮過的方案、採納理由與影響範圍。

## 為何範本需要 ADR

範本的讀者是「**即將用它起新專案的 Django 開發者**」。若範本只有程式碼沒有決策記錄，讀者會：

- 不知道哪些設計是刻意的、哪些只是隨手寫的
- 難以判斷哪些部分該保留、哪些該依自身專案調整
- 重複踩過相同的設計陷阱

ADR 讓範本從「可執行的起手式」升級為「帶有設計脈絡的教材」。

## ADR 索引

| 編號 | 標題 | 狀態 |
|---|---|---|
| [ADR-001](./ADR-001-drf-native-response-format.md) | API 回應遵循 DRF 原生慣例 + RFC 7807 | Accepted |
| [ADR-002](./ADR-002-remove-repository-layer.md) | 移除 Repository 抽象層，採用 Django 習慣用法 | Accepted |
| [ADR-003](./ADR-003-service-layer-retained.md) | 保留 Service 層，負責跨 Model 業務邏輯 | Accepted |

## 新增 ADR

1. 複製既有 ADR 作為樣板
2. 編號遞增（ADR-00N）
3. 狀態：`Proposed` → `Accepted` → 可能 `Deprecated` 或 `Superseded by ADR-XXX`
4. 更新本 README 的索引
