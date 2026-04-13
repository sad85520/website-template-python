"""全域例外處理：將錯誤轉換為 RFC 7807 Problem Details 格式。

本模組遵循 [RFC 7807 - Problem Details for HTTP APIs](https://datatracker.ietf.org/doc/html/rfc7807)，
輸出 Content-Type 為 ``application/problem+json`` 的標準錯誤格式，
符合 Django/DRF 生態慣例（見 docs/adr/ADR-001-drf-native-response-format.md）。

成功回應則直接由 view 透過 ``return Response(serializer.data, status=200)`` 產出 DRF 原生格式，
本模組僅負責錯誤路徑。
"""
from __future__ import annotations

import logging
from typing import Any

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)

# RFC 7807 的 "type" URI 應為穩定識別碼，不必是可存取的 URL。
# 使用 "about:blank" 代表「無額外語意類型」，符合 RFC 7807 §4.2。
# 若日後需要為特定錯誤類型提供文件頁面，可改為 https://example.com/probs/<slug>。
PROBLEM_TYPE_BLANK = "about:blank"

PROBLEM_CONTENT_TYPE = "application/problem+json"


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """將所有例外統一格式化為 RFC 7807 Problem Details。

    DRF 已處理的例外會被格式化並保留原始 HTTP 狀態碼；
    Http404/ObjectDoesNotExist 回傳 404；其他未預期例外回傳 500。

    Args:
        exc: 被攔截的例外物件。
        context: DRF 傳入的 view context，含 request 與 view 資訊。

    Returns:
        格式化後的 Response（Content-Type 為 application/problem+json），
        或 None（交由 Django 預設處理）。
    """
    response = exception_handler(exc, context)

    if response is not None:
        return _build_problem_from_drf(exc, response)

    # 未被 DRF 處理的例外
    if isinstance(exc, (Http404, ObjectDoesNotExist)):
        return _problem_response(
            title="Not Found",
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested resource was not found.",
        )

    # 其他未預期例外 → 500
    # logger.exception 會自動附加完整 traceback，便於 Sentry 等聚合器定位問題。
    logger.exception("Unhandled exception: %s", exc)
    return _problem_response(
        title="Internal Server Error",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred.",
    )


def _build_problem_from_drf(exc: Exception, response: Response) -> Response:
    """將 DRF 產生的 response 改寫為 RFC 7807 Problem Details 格式。"""
    status_code: int = response.status_code
    title = "Error"
    detail: str | None = None
    errors: list[dict[str, str]] | None = None

    if isinstance(exc, ValidationError):
        title = "Validation Failed"
        detail = "One or more fields failed validation."
        errors = _flatten_validation_errors(exc.detail)
    elif isinstance(exc, NotAuthenticated):
        title = "Authentication Required"
        detail = "Authentication credentials were not provided."
    elif isinstance(exc, AuthenticationFailed):
        title = "Authentication Failed"
        detail = str(exc.detail) if exc.detail else "Invalid authentication credentials."
    elif isinstance(exc, PermissionDenied):
        title = "Permission Denied"
        detail = "You do not have permission to perform this action."
    elif hasattr(response, "data") and response.data is not None:
        # 兜底：擷取 DRF 回傳的 detail 欄位
        data = response.data
        detail = str(data["detail"]) if isinstance(data, dict) and "detail" in data else str(data)

    return _problem_response(title=title, status_code=status_code, detail=detail, errors=errors)


def _problem_response(
    *,
    title: str,
    status_code: int,
    detail: str | None = None,
    errors: list[dict[str, str]] | None = None,
    type_uri: str = PROBLEM_TYPE_BLANK,
) -> Response:
    """組裝 RFC 7807 Problem Details Response。

    欄位對應：
    - ``type``：問題類型的 URI（RFC 7807 §3.1）。
    - ``title``：人類可讀的簡短描述（不應隨狀態變動）。
    - ``status``：HTTP 狀態碼。
    - ``detail``：針對此次發生狀況的具體說明（可選）。
    - ``errors``：擴充欄位，承載欄位級驗證錯誤陣列（非 RFC 7807 標準，但為業界常見擴充）。
    """
    payload: dict[str, Any] = {
        "type": type_uri,
        "title": title,
        "status": status_code,
    }
    if detail is not None:
        payload["detail"] = detail
    if errors:
        payload["errors"] = errors

    return Response(payload, status=status_code, content_type=PROBLEM_CONTENT_TYPE)


def _flatten_validation_errors(detail: Any, field_prefix: str = "") -> list[dict[str, str]]:
    """將 DRF ValidationError 的巢狀 detail 結構展平為前端可直接使用的扁平陣列。

    DRF 的 ValidationError.detail 結構因情境而異：
    - 欄位錯誤為 dict（``{field: [ErrorDetail, ...]}``）
    - 非欄位錯誤（``non_field_errors``）為 list
    - 巢狀 Serializer 會產生多層 dict，需遞迴展平。

    Args:
        detail: ValidationError.detail 或其遞迴子結構。
        field_prefix: 遞迴時累積的欄位名稱前綴。

    Returns:
        扁平化的 ``{"field": str, "message": str}`` 字典清單。
    """
    errors: list[dict[str, str]] = []
    if isinstance(detail, dict):
        for field, messages in detail.items():
            errors.extend(_flatten_validation_errors(messages, field_prefix=str(field)))
    elif isinstance(detail, list):
        for item in detail:
            if isinstance(item, str):
                errors.append({"field": field_prefix, "message": item})
            else:
                errors.extend(_flatten_validation_errors(item, field_prefix=field_prefix))
    else:
        errors.append({"field": field_prefix, "message": str(detail)})
    return errors
