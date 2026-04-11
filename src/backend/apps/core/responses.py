"""統一 API 回傳格式。"""
from typing import Any

from rest_framework.response import Response


def success(data: Any, status: int = 200, meta: dict[str, Any] | None = None) -> Response:
    """建立代表操作成功的標準 API 回應。

    Args:
        data: 要回傳的資料酬載。
        status: HTTP 狀態碼，預設為 200。
        meta: 可選的分頁中繼資料字典。

    Returns:
        success=True 的標準格式 Response。
    """
    payload: dict[str, Any] = {"success": True, "data": data, "message": None, "errors": None}
    if meta:
        payload["meta"] = meta
    return Response(payload, status=status)


def created(data: Any) -> Response:
    """建立代表資源建立成功（HTTP 201）的標準 API 回應。

    Args:
        data: 已建立的資源資料。

    Returns:
        status=201、success=True 的標準格式 Response。
    """
    return success(data, status=201)


def fail(
    message: str,
    errors: list[dict[str, str]] | None = None,
    status: int = 400,
) -> Response:
    """建立代表操作失敗的標準 API 回應。

    Args:
        message: 描述失敗原因的訊息。
        errors: 可選的欄位層級驗證錯誤清單。
        status: HTTP 狀態碼，預設為 400。

    Returns:
        success=False 的標準格式 Response。
    """
    return Response(
        {"success": False, "data": None, "message": message, "errors": errors},
        status=status,
    )
