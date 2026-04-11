"""Auth endpoint tests."""
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User

from .factories import UserFactory


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db: object) -> User:
    return UserFactory(email="test@example.com")


@pytest.mark.django_db
class TestRegister:
    def test_register_success(self, client: APIClient) -> None:
        url = reverse("auth-register")
        data = {"email": "new@example.com", "password": "Password123!", "display_name": "New User"}
        response = client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["success"] is True
        assert response.data["data"]["email"] == "new@example.com"
        assert User.objects.filter(email="new@example.com").exists()

    def test_register_duplicate_email(self, client: APIClient, user: User) -> None:
        url = reverse("auth-register")
        data = {"email": user.email, "password": "Password123!", "display_name": "Dup"}
        response = client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["success"] is False

    def test_register_weak_password(self, client: APIClient) -> None:
        url = reverse("auth-register")
        data = {"email": "weak@example.com", "password": "123", "display_name": "Weak"}
        response = client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLogin:
    def setup_method(self) -> None:
        self.url = reverse("auth-login")

    def test_login_success(self, client: APIClient, user: User) -> None:
        url = reverse("auth-login")
        response = client.post(url, {"email": user.email, "password": "Password123!"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert "access_token" in response.data["data"]
        assert "refreshToken" in response.cookies

    def test_login_wrong_password(self, client: APIClient, user: User) -> None:
        url = reverse("auth-login")
        response = client.post(url, {"email": user.email, "password": "WrongPass!"}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["success"] is False

    def test_login_nonexistent_user(self, client: APIClient) -> None:
        url = reverse("auth-login")
        response = client.post(url, {"email": "noone@example.com", "password": "Pass123!"}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_locked_account(self, client: APIClient) -> None:
        """Locked account cannot login"""
        user = UserFactory()
        user.lockout_until = timezone.now() + timedelta(minutes=15)
        user.save()
        response = client.post(self.url, {"email": user.email, "password": "testpass123"})
        assert response.status_code == 401
        assert "locked" in response.data["message"].lower()

    def test_login_increments_failed_attempts(self, client: APIClient) -> None:
        """Failed login increments counter"""
        user = UserFactory()
        client.post(self.url, {"email": user.email, "password": "wrongpassword"})
        user.refresh_from_db()
        assert user.failed_login_attempts == 1

    def test_login_locks_after_five_failures(self, client: APIClient) -> None:
        """Account locked after 5 failed attempts"""
        user = UserFactory()
        for _ in range(5):
            client.post(self.url, {"email": user.email, "password": "wrongpassword"})
        user.refresh_from_db()
        assert user.lockout_until is not None

    def test_login_resets_failed_attempts_on_success(self, client: APIClient) -> None:
        """Successful login resets counter"""
        user = UserFactory(password="testpass123")
        user.failed_login_attempts = 3
        user.save()
        client.post(self.url, {"email": user.email, "password": "testpass123"})
        user.refresh_from_db()
        assert user.failed_login_attempts == 0


@pytest.mark.django_db
class TestTokenRefresh:
    def test_refresh_success(self, client: APIClient, user: User) -> None:
        # 先登入取得 cookie
        login_resp = client.post(
            reverse("auth-login"),
            {"email": user.email, "password": "Password123!"},
            format="json",
        )
        assert login_resp.status_code == 200

        # 使用 cookie 呼叫 refresh
        response = client.post(reverse("auth-refresh"))
        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.data["data"]

    def test_refresh_without_cookie(self, client: APIClient) -> None:
        response = client.post(reverse("auth-refresh"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_with_expired_token(self, client: APIClient) -> None:
        """Expired refresh token is rejected"""
        # Use an obviously invalid/expired token string
        client.cookies["refresh_token"] = "expiredtokenvalue"
        response = client.post(reverse("auth-refresh"))
        assert response.status_code == 401


@pytest.mark.django_db
class TestLogout:
    def test_logout_success(self, client: APIClient, user: User) -> None:
        client.post(
            reverse("auth-login"),
            {"email": user.email, "password": "Password123!"},
            format="json",
        )
        # force_authenticate 覆寫請求的認證狀態，繞過 JWT 驗證，
        # 確保測試聚焦在 logout 邏輯本身，而非 JWT 的有效性。
        client.force_authenticate(user=user)
        response = client.post(reverse("auth-logout"))

        assert response.status_code == status.HTTP_200_OK
