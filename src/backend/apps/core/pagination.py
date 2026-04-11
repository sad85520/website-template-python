"""標準分頁，對應前端 PaginationMeta 格式。"""
from typing import Any

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """專案統一分頁類別，將 DRF 分頁回應格式化為標準 ApiResponse 結構。

    覆寫 get_paginated_response 與 get_paginated_response_schema，
    確保回應格式與 drf-spectacular 產生的 OpenAPI schema 一致。
    """

    page_size = 20
    # page_size_query_param 允許客戶端透過 ?limit= 自訂每頁筆數，
    # max_page_size 設定上限防止大量資料一次性回傳造成效能問題。
    page_size_query_param = "limit"
    max_page_size = 100
    page_query_param = "page"

    def get_paginated_response(self, data: Any) -> Response:
        """回傳符合專案統一 ApiResponse 格式的分頁回應。

        覆寫此方法以產生含 meta 中繼資料的標準結構；
        同時必須覆寫 get_paginated_response_schema，使 drf-spectacular 產生正確的 OpenAPI schema。

        Args:
            data: 已序列化的當前頁資料。

        Returns:
            包含 success、data、meta 的統一格式 Response。
        """
        assert self.page is not None
        return Response(
            {
                "success": True,
                "data": data,
                "message": None,
                "errors": None,
                "meta": {
                    "total": self.page.paginator.count,
                    "page": self.page.number,
                    "limit": self.get_page_size(self.request),  # type: ignore[arg-type]
                    "totalPages": self.page.paginator.num_pages,
                },
            }
        )

    def get_paginated_response_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """回傳 drf-spectacular 用於產生分頁回應 OpenAPI schema 的結構描述。

        Args:
            schema: 資料項目的 OpenAPI schema。

        Returns:
            包含 success、data、meta 欄位的完整 OpenAPI schema 字典。
        """
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "data": schema,
                "message": {"type": "string", "nullable": True},
                "errors": {"type": "array", "nullable": True},
                "meta": {
                    "type": "object",
                    "properties": {
                        "total": {"type": "integer"},
                        "page": {"type": "integer"},
                        "limit": {"type": "integer"},
                        "totalPages": {"type": "integer"},
                    },
                },
            },
        }
