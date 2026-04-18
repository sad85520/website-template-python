"""User endpoint tests.

成功路徑為 DRF 原生格式；分頁採 PageNumberPagination 預設格式：
``{count, next, previous, results}``。
"""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User

from .factories import UserFactory

# `client` fixture 來自 src/backend/conftest.py（project-wide）。


@pytest.mark.django_db
class TestMe:
    """GET /users/me 端點測試。"""

    def test_get_me_authenticated(self, client: APIClient) -> None:
        """已驗證使用者應回傳 200 與自身的帳號資料。"""
        user = UserFactory()
        client.force_authenticate(user=user)
        response = client.get(reverse("user-me"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == user.email

    def test_get_me_unauthenticated(self, client: APIClient) -> None:
        """未驗證的請求應回傳 401。"""
        response = client.get(reverse("user-me"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserList:
    """GET /users/ 端點測試（管理員專用）。"""

    def test_admin_can_list_users(self, client: APIClient) -> None:
        """Admin 應可取得分頁使用者清單，回應格式為 DRF PageNumberPagination 原生格式。"""
        admin = UserFactory(role=User.Role.ADMIN, is_staff=True, is_superuser=True)
        UserFactory.create_batch(5)
        client.force_authenticate(user=admin)
        response = client.get(reverse("user-list"))

        assert response.status_code == status.HTTP_200_OK
        # DRF PageNumberPagination 原生格式：count / next / previous / results。
        assert response.data["count"] >= 6
        assert isinstance(response.data["results"], list)

    def test_admin_can_search_users(self, client: APIClient) -> None:
        """Admin 使用 ?search= 參數應只回傳符合 email 或 display_name 的使用者。"""
        admin = UserFactory(role=User.Role.ADMIN, is_staff=True, is_superuser=True)
        UserFactory(email="alice@example.com", display_name="Alice")
        UserFactory(email="bob@example.com", display_name="Bob")
        client.force_authenticate(user=admin)
        response = client.get(reverse("user-list"), {"search": "alice"})

        assert response.status_code == status.HTTP_200_OK
        emails = [u["email"] for u in response.data["results"]]
        assert "alice@example.com" in emails
        assert "bob@example.com" not in emails

    def test_regular_user_cannot_list_users(self, client: APIClient) -> None:
        """一般使用者存取應回傳 403 Forbidden。"""
        user = UserFactory()
        client.force_authenticate(user=user)
        response = client.get(reverse("user-list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN
