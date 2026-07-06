"""API 文件路由測試（Scalar UI + OpenAPI schema）。

鎖住 canonical 路徑 ``/api/scalar/``：三份文件（README、dev-setup.md、
init-dev.sh）曾各自宣稱不同路徑，而程式碼實際只註冊了 ``/scalar/``
（沒有 ``api/`` 前綴），透過 nginx 的 ``http://localhost`` 入口完全打不到。
本測試直接用 Django test client 驗證路由本身可達，不依賴 nginx。
"""


def test_scalar_ui_endpoint_returns_200(client, debug_urlconf):
    response = client.get("/api/scalar/")
    assert response.status_code == 200


def test_openapi_schema_endpoint_returns_200(client, debug_urlconf):
    response = client.get("/api/schema/")
    assert response.status_code == 200
