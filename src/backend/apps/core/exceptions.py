"""全域例外處理。"""
from typing import Any

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    # DRF 預設處理先跑
    response = exception_handler(exc, context)

    if response is not None:
        # 已被 DRF 處理的例外，統一格式化
        errors = None
        message = "An error occurred."

        if isinstance(exc, ValidationError):
            message = "Validation failed."
            errors = _flatten_validation_errors(exc.detail)
        elif isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
            message = "Authentication required."
        elif isinstance(exc, PermissionDenied):
            message = "You do not have permission to perform this action."
        elif hasattr(response, "data"):
            if isinstance(response.data, dict) and "detail" in response.data:
                message = str(response.data["detail"])
            else:
                message = str(response.data)

        response.data = {
            "success": False,
            "data": None,
            "message": message,
            "errors": errors,
        }
        return response

    # 未被 DRF 處理的例外
    if isinstance(exc, (Http404, ObjectDoesNotExist)):
        return Response(
            {"success": False, "data": None, "message": "The requested resource was not found.", "errors": None},
            status=status.HTTP_404_NOT_FOUND,
        )

    # 其他未預期例外 → 500
    import logging
    logger = logging.getLogger(__name__)
    logger.exception("Unhandled exception: %s", exc)
    return Response(
        {"success": False, "data": None, "message": "An unexpected error occurred.", "errors": None},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _flatten_validation_errors(detail: Any, field_prefix: str = "") -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if isinstance(detail, dict):
        for field, messages in detail.items():
            errors.extend(_flatten_validation_errors(messages, field_prefix=field))
    elif isinstance(detail, list):
        for item in detail:
            if isinstance(item, str):
                errors.append({"field": field_prefix, "message": item})
            else:
                errors.extend(_flatten_validation_errors(item, field_prefix=field_prefix))
    else:
        errors.append({"field": field_prefix, "message": str(detail)})
    return errors
