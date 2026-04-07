"""User endpoint tests."""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User

from .factories import UserFactory


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.mark.django_db
class TestMe:
    def test_get_me_authenticated(self, client: APIClient) -> None:
        user = UserFactory()
        client.force_authenticate(user=user)
        response = client.get(reverse("user-me"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["data"]["email"] == user.email

    def test_get_me_unauthenticated(self, client: APIClient) -> None:
        response = client.get(reverse("user-me"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserList:
    def test_admin_can_list_users(self, client: APIClient) -> None:
        admin = UserFactory(role=User.Role.ADMIN, is_staff=True, is_superuser=True)
        UserFactory.create_batch(5)
        client.force_authenticate(user=admin)
        response = client.get(reverse("user-list"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert response.data["meta"]["total"] >= 6

    def test_regular_user_cannot_list_users(self, client: APIClient) -> None:
        user = UserFactory()
        client.force_authenticate(user=user)
        response = client.get(reverse("user-list"))

        assert response.status_code == status.HTTP_403_FORBIDDEN
