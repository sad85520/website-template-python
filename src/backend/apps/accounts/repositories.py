"""Repository layer for accounts data access."""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from django.contrib.auth import get_user_model

if TYPE_CHECKING:
    from django.db import models as db_models

    from .models import User

UserModel: type[User] = get_user_model()


# ─── Protocols (optional structural typing) ────────────────────────────────────


@runtime_checkable
# IUserRepository 作為結構型別協議（Structural Typing），
# 供測試時以 Mock 物件替換真實 repository，無需繼承即可通過 isinstance 檢查（runtime_checkable）。
class IUserRepository(Protocol):
    def get_by_id(self, user_id: object) -> User | None: ...
    def get_by_email(self, email: str) -> User | None: ...
    def exists_by_email(self, email: str) -> bool: ...
    def create(self, email: str, password: str, display_name: str) -> User: ...
    def save(self, user: User) -> None: ...
    def get_all(self) -> db_models.QuerySet[User]: ...
    def search(self, query: str) -> db_models.QuerySet[User]: ...


# ─── Implementations ───────────────────────────────────────────────────────────


class UserRepository:
    """Encapsulates all ORM operations on the User model."""

    def get_by_id(self, user_id: object) -> User | None:
        # 使用 filter().first() 而非 get()，以避免在 user_id 不存在時拋出 DoesNotExist 例外，
        # 讓呼叫端統一以 None 判斷即可。
        return UserModel.objects.filter(pk=user_id).first()  # type: ignore[misc]

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

    def get_all(self) -> db_models.QuerySet[User]:
        return UserModel.objects.all()

    def search(self, query: str) -> db_models.QuerySet[User]:
        if not query:
            return self.get_all()
        # 使用 QuerySet 聯集（|）而非 Q 物件，可確保兩個 queryset 各自套用預設 ordering，
        # 但需注意聯集結果可能含重複值（同時符合 email 與 display_name 條件），若有需要應加 .distinct()。
        return (
            UserModel.objects.filter(email__icontains=query)
            | UserModel.objects.filter(display_name__icontains=query)
        )
