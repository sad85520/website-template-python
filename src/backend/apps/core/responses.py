"""統一 API 回傳格式。"""
from typing import Any

from rest_framework.response import Response


def success(data: Any, status: int = 200, meta: dict[str, Any] | None = None) -> Response:
    payload: dict[str, Any] = {"success": True, "data": data, "message": None, "errors": None}
    if meta:
        payload["meta"] = meta
    return Response(payload, status=status)


def created(data: Any) -> Response:
    return success(data, status=201)


def fail(
    message: str,
    errors: list[dict[str, str]] | None = None,
    status: int = 400,
) -> Response:
    return Response(
        {"success": False, "data": None, "message": message, "errors": errors},
        status=status,
    )
