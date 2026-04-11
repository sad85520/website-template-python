"""Repository layer for accounts data access."""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from django.contrib.auth import get_user_model

if TYPE_CHECKING:
    from django.db import models as db_models

    from .models import User

UserModel: type[User] = get_user_model()  # type: ignore[assignment]


# ─── Protocols (optional structural typing) ────────────────────────────────────


@runtime_checkable
class IUserRepository(Protocol):
    def get_by_id(self, user_id: object) -> User | None: ...
    def get_by_email(self, email: str) -> User | None: ...
    def exists_by_email(self, email: str) -> bool: ...
    def create(self, email: str, password: str, display_name: str) -> User: ...
    def save(self, user: User) -> None: ...
    def get_all(self) -> db_models.QuerySet: ...
    def search(self, query: str) -> db_models.QuerySet: ...


# ─── Implementations ───────────────────────────────────────────────────────────


class UserRepository:
    """Encapsulates all ORM operations on the User model."""

    def get_by_id(self, user_id: object) -> User | None:
        return UserModel.objects.filter(pk=user_id).first()

    def get_by_email(self, email: str) -> User | None:
        return UserModel.objects.filter(email=email).first()

    def get_by_email_for_auth(self, email: str) -> User | None:
        """
        Fetch a user by email, including those that are inactive.
        Used specifically during authentication to inspect lockout state.
        """
        try:
            return UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            return None

    def exists_by_email(self, email: str) -> bool:
        return UserModel.objects.filter(email=email).exists()

    def create(self, email: str, password: str, display_name: str) -> User:
        return UserModel.objects.create_user(
            email=email,
            password=password,
            display_name=display_name,
        )

    def save(self, user: User) -> None:
        user.save()

    def get_all(self) -> db_models.QuerySet:
        return UserModel.objects.all()

    def search(self, query: str) -> db_models.QuerySet:
        if not query:
            return self.get_all()
        return (
            UserModel.objects.filter(email__icontains=query)
            | UserModel.objects.filter(display_name__icontains=query)
        )
