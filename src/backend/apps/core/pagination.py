"""標準分頁類別，採用 DRF 原生格式。

本模組直接使用 DRF 內建的 ``PageNumberPagination``，輸出格式為：

.. code-block:: json

    {
        "count": 42,
        "next": "http://.../?page=3",
        "previous": "http://.../?page=1",
        "results": [...]
    }

選擇 DRF 原生格式的理由見 ``docs/adr/ADR-001-drf-native-response-format.md``：
- 與 ``drf-spectacular`` 的 OpenAPI schema 生成完全相容
- 符合 Django/DRF 社群慣例，新進開發者無需學習自訂格式
- 避免手寫 ``get_paginated_response_schema`` 的維護成本
"""
from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """預設分頁類別：每頁 20 筆，可透過 ``?limit=`` 參數調整，上限 100 筆。

    前端客戶端透過 ``count`` 計算總頁數，``next`` / ``previous`` 取得上下頁 URL。
    不覆寫 ``get_paginated_response`` —— 保留 DRF 預設格式。
    """

    page_size = 20
    # 透過 ?limit= 自訂每頁筆數；max_page_size 防止客戶端要求過大頁面導致效能問題。
    page_size_query_param = "limit"
    max_page_size = 100
    page_query_param = "page"
