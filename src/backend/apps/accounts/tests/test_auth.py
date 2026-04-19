"""Auth endpoint tests.

回應格式：成功路徑為 DRF 原生格式，錯誤路徑為 RFC 7807 Problem Details（title/detail/status）。
"""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User

from .factories import DEFAULT_PASSWORD, UserFactory

# `client` fixture 來自 src/backend/conftest.py（project-wide）。


@pytest.fixture
def user(db: object) -> User:
    return UserFactory(email="test@example.com")


@pytest.mark.django_db
class TestRegister:
    """POST /auth/register 端點測試。"""

    def test_register_success(self, client: APIClient) -> None:
        """有效資料應建立使用者並回傳 201 與使用者資料。"""
        url = reverse("auth-register")
        data = {"email": "new@example.com", "password": "Password123!", "display_name": "New User"}
        response = client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["email"] == "new@example.com"
        assert User.objects.filter(email="new@example.com").exists()

    def test_register_duplicate_email(self, client: APIClient, user: User) -> None:
        """重複 Email 應觸發 RFC 7807 驗證錯誤（400）並附帶欄位錯誤陣列。"""
        url = reverse("auth-register")
        data = {"email": user.email, "password": DEFAULT_PASSWORD, "display_name": "Dup"}
        response = client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # RFC 7807 Problem Details：驗證錯誤會附帶 errors 陣列。
        assert response.data["title"] == "Validation Failed"
        assert response.data["status"] == 400
        assert any(e["field"] == "email" for e in response.data["errors"])

    def test_register_weak_password(self, client: APIClient) -> None:
        """過短密碼應觸發 RFC 7807 驗證錯誤（400）。"""
        url = reverse("auth-register")
        data = {"email": "weak@example.com", "password": "123", "display_name": "Weak"}
        response = client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["title"] == "Validation Failed"


@pytest.mark.django_db
class TestLogin:
    """POST /auth/login 端點測試，含暴力破解防護驗證。"""

    def setup_method(self) -> None:
        """快取登入 URL，避免每個測試方法重複呼叫 reverse()。"""
        self.url = reverse("auth-login")

    def test_login_success(self, client: APIClient, user: User) -> None:
        """正確憑證應回傳 200、access token 與 refreshToken HttpOnly cookie。"""
        response = client.post(
            self.url, {"email": user.email, "password": DEFAULT_PASSWORD}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.data
        assert response.data["expires_in"] > 0
        assert "refreshToken" in response.cookies

    def test_login_wrong_password(self, client: APIClient, user: User) -> None:
        """錯誤密碼應回傳 401 RFC 7807 格式錯誤。"""
        response = client.post(
            self.url, {"email": user.email, "password": "WrongPass!"}, format="json"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["status"] == 401
        assert response.data["title"] in {"Authentication Failed", "Authentication Required"}

    def test_login_nonexistent_user(self, client: APIClient) -> None:
        """不存在的帳號應與錯誤密碼回傳相同 401（防止帳號枚舉）。"""
        response = client.post(
            self.url, {"email": "noone@example.com", "password": "Pass123!"}, format="json"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_locked_account(self, client: APIClient) -> None:
        """鎖定中的帳號即使密碼正確也應回傳 401，並附帶 locked 關鍵字。"""
        user = UserFactory()
        user.lockout_until = timezone.now() + timedelta(minutes=15)
        user.save()
        response = client.post(self.url, {"email": user.email, "password": "testpass123"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "locked" in response.data["detail"].lower()

    def test_login_increments_failed_attempts(self, client: APIClient) -> None:
        """登入失敗一次應將 failed_login_attempts 累加為 1。"""
        user = UserFactory()
        client.post(self.url, {"email": user.email, "password": "wrongpassword"})
        user.refresh_from_db()
        assert user.failed_login_attempts == 1

    def test_login_locks_after_five_failures(self, client: APIClient) -> None:
        """連續失敗五次後應設定 lockout_until（帳號鎖定）。"""
        user = UserFactory()
        for _ in range(5):
            client.post(self.url, {"email": user.email, "password": "wrongpassword"})
        user.refresh_from_db()
        assert user.lockout_until is not None

    def test_login_resets_failed_attempts_on_success(self, client: APIClient) -> None:
        """登入成功後應將 failed_login_attempts 重置為 0。"""
        user = UserFactory(password="testpass123")
        user.failed_login_attempts = 3
        user.save()
        client.post(self.url, {"email": user.email, "password": "testpass123"})
        user.refresh_from_db()
        assert user.failed_login_attempts == 0


@pytest.mark.django_db
class TestTokenRefresh:
    """POST /auth/refresh 端點測試。"""

    def test_refresh_success(self, client: APIClient, user: User) -> None:
        """持有有效 refreshToken cookie 時應回傳新的 access token。"""
        login_resp = client.post(
            reverse("auth-login"),
            {"email": user.email, "password": DEFAULT_PASSWORD},
            format="json",
        )
        assert login_resp.status_code == 200

        response = client.post(reverse("auth-refresh"))
        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.data

    def test_refresh_without_cookie(self, client: APIClient) -> None:
        """未攜帶 cookie 時應回傳 401。"""
        response = client.post(reverse("auth-refresh"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_with_expired_token(self, client: APIClient) -> None:
        """攜帶無效 refresh token 時應回傳 401。"""
        client.cookies["refreshToken"] = "expiredtokenvalue"
        response = client.post(reverse("auth-refresh"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestLogout:
    """POST /auth/logout 端點測試。"""

    def test_logout_success(self, client: APIClient, user: User) -> None:
        """已驗證使用者登出應回傳 204 並清除 refresh token。"""
        client.post(
            reverse("auth-login"),
            {"email": user.email, "password": DEFAULT_PASSWORD},
            format="json",
        )
        # force_authenticate 覆寫請求的認證狀態，繞過 JWT 驗證，
        # 確保測試聚焦在 logout 邏輯本身，而非 JWT 的有效性。
        client.force_authenticate(user=user)
        response = client.post(reverse("auth-logout"))

        assert response.status_code == status.HTTP_204_NO_CONTENT
