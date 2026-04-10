"""標準分頁，對應前端 PaginationMeta 格式。"""
from typing import Any

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "limit"
    max_page_size = 100
    page_query_param = "page"

    def get_paginated_response(self, data: Any) -> Response:
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
