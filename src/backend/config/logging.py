"""Shared structlog / stdlib logging configuration.

`structlog.configure()` 必須在任何 logger 被建立之前呼叫，否則 processor chain
不會套用到既有的 logger 實例。放 config/ 層讓 dev 與 prod settings 共用，
避免兩邊漂移（之前只有 production.py 有 structlog 相關配置，dev 完全沒有，
導致 dev 看不到結構化欄位、而 prod 的 formatter 也因為沒 configure 而噴空值）。

使用方式：settings/*.py 呼叫 `configure_structlog(json_output=...)` 並採用
`build_logging_dict(json_output=...)` 作為 `LOGGING` 值。
"""
from typing import Any

import structlog


def _shared_processors() -> list[Any]:
    """dev / prod 共用的 processor chain。

    stdlib logging 來的 log（e.g. `logging.getLogger("django").info(...)`)
    與 structlog 原生 log 共用同一條 pipeline，讓兩邊輸出結構一致。
    """
    return [
        structlog.contextvars.merge_contextvars,  # 支援 `bind_contextvars()` 傳 request_id 等
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]


def configure_structlog(*, json_output: bool) -> None:
    """Configure structlog processor chain.

    Args:
        json_output: True → JSON renderer（prod，便於 log aggregator 解析）；
                     False → ConsoleRenderer（dev，terminal 彩色可讀）。
    """
    final_renderer: Any = (
        structlog.processors.JSONRenderer()
        if json_output
        else structlog.dev.ConsoleRenderer(colors=True)
    )
    structlog.configure(
        processors=[
            *_shared_processors(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    # 把 final renderer 暫存於 module，讓 build_logging_dict 能拿到相同實例，
    # 避免 dev/prod 產生兩個獨立的 renderer 造成行為差異。
    _RENDERER_CACHE["renderer"] = final_renderer


_RENDERER_CACHE: dict[str, Any] = {}


def build_logging_dict(*, json_output: bool, level: str = "INFO") -> dict[str, Any]:
    """Build Django LOGGING dict that routes stdlib logs through structlog.

    ProcessorFormatter 負責把 stdlib LogRecord 轉成 structlog event dict，
    然後套 foreign_pre_chain（給 stdlib log 補齊 structlog 本來會加的欄位），
    最後以 final renderer 輸出。
    """
    renderer = _RENDERER_CACHE.get("renderer")
    if renderer is None:
        # 如果 caller 沒先呼 configure_structlog()，退回以 json_output 旗標自建一次
        # （避免因 import 順序造成啟動失敗）。
        renderer = (
            structlog.processors.JSONRenderer()
            if json_output
            else structlog.dev.ConsoleRenderer(colors=True)
        )

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structlog": {
                "()": "structlog.stdlib.ProcessorFormatter",
                "processor": renderer,
                "foreign_pre_chain": _shared_processors(),
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "structlog",
            },
        },
        "root": {"handlers": ["console"], "level": level},
        "loggers": {
            # Django 的 SQL log 預設 DEBUG，與 DEV 的需求一致；prod 走 root INFO 濾掉
            "django.db.backends": {
                "handlers": ["console"],
                "level": "DEBUG" if not json_output else "WARNING",
                "propagate": False,
            },
        },
    }
