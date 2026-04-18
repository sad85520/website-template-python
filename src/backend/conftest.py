"""Project-wide pytest fixtures.

放 backend root 讓 pytest 自動往上收集，所有 apps/*/tests 皆可直接使用，
不必各自 import 或重覆宣告。
"""
import pytest
from rest_framework.test import APIClient


@pytest.fixture
def client() -> APIClient:
    """共用的 DRF APIClient，未登入狀態。

    要驗證的測試自己呼叫 `client.force_authenticate(user=...)` 覆寫；
    這個 fixture 刻意不預設登入，避免把認證狀態隱式漏進「應該測未登入」的案例。
    """
    return APIClient()
