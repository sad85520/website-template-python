"""Project-wide pytest fixtures.

放 backend root 讓 pytest 自動往上收集，所有 apps/*/tests 皆可直接使用，
不必各自 import 或重覆宣告。
"""

import importlib

import pytest
from django.urls import clear_url_caches
from rest_framework.test import APIClient


@pytest.fixture
def client() -> APIClient:
    """共用的 DRF APIClient，未登入狀態。

    要驗證的測試自己呼叫 `client.force_authenticate(user=...)` 覆寫；
    這個 fixture 刻意不預設登入，避免把認證狀態隱式漏進「應該測未登入」的案例。
    """
    return APIClient()


@pytest.fixture
def debug_urlconf(settings):
    """讓 DEBUG-only 路由（``/api/schema/``、``/api/scalar/``）在測試中可達。

    Django 的測試環境設定（``django.test.utils.setup_test_environment``）會強制
    ``settings.DEBUG = False``，且 ``config/urls.py`` 的 ``if settings.DEBUG: ...``
    只在 URLconf 模組第一次被 import 時求值一次；單純在測試裡改 ``settings.DEBUG``
    不會讓已快取的 urlpatterns 重新產生。此 fixture 手動 reload 該模組並清除
    URL resolver 快取，測試結束後再還原，避免污染其他測試的路由解析結果。
    """
    import config.urls as urls_module

    settings.DEBUG = True
    importlib.reload(urls_module)
    clear_url_caches()
    yield
    settings.DEBUG = False
    importlib.reload(urls_module)
    clear_url_caches()
