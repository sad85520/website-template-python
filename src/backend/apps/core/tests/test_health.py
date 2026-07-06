"""Health check 端點測試。

鎖住 config/urls.py 的路由不再漂移——曾經因為使用已棄用的
``health_check.urls`` 且未設定 ``HEALTH_CHECK["SUBSETS"]``，
導致 ``/api/health/ready/`` 對任何 subset 名稱都回傳 404，
k8s readinessProbe 因此永遠卡在 0/2 Ready。
"""

import pytest


def test_liveness_endpoint_returns_200(client):
    """Liveness 端點回 200，且不需要資料庫連線即可判斷存活。"""
    response = client.get("/api/health/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_readiness_endpoint_returns_200(client):
    """Readiness 端點在 DB／cache 皆可用時回 200，對齊 k8s readinessProbe 語意。"""
    response = client.get("/api/health/ready/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_readiness_endpoint_reports_database_status_as_json(client):
    """帶 ``?format=json`` 時可看到各 plugin 的檢查結果，方便除錯用。"""
    response = client.get("/api/health/ready/", {"format": "json"})
    assert response.status_code == 200
    payload = response.json()
    assert any("Database" in key for key in payload)
