"""Development settings."""
from config.logging import build_logging_dict, configure_structlog

from .base import *  # noqa: F403, F401

DEBUG = True

# Scalar CSP 透過 urls.py 的 @csp_update decorator 個別套用，不在此全域覆寫。

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost",
]

CORS_ALLOW_CREDENTIALS = True

# dev 走 ConsoleRenderer（彩色、可讀），與 prod 共用同一條 processor chain，
# 差別只在最後的 renderer。不把 LOGGING 寫死在此，避免與 prod 漂移。
configure_structlog(json_output=False)
LOGGING = build_logging_dict(json_output=False, level="INFO")
