"""Auth endpoint tests."""
import pytest
from django.urls import reverse
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


@pytest.mark.django_db
class TestLogout:
    def test_logout_success(self, client: APIClient, user: User) -> None:
        client.post(
            reverse("auth-login"),
            {"email": user.email, "password": "Password123!"},
            format="json",
        )
        client.force_authenticate(user=user)
        response = client.post(reverse("auth-logout"))

        assert response.status_code == status.HTTP_200_OK
