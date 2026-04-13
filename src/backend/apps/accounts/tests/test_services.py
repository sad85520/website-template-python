"""Service layer unit tests.

以 ``@pytest.mark.django_db`` 搭配真實 ORM 驗證 service 行為，
避免 mock Repository 帶來的「測試通過但行為漂移」風險（見 ADR-002）。
"""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed

from apps.accounts import services
from apps.accounts.models import User

from .factories import UserFactory


@pytest.mark.django_db
class TestRegisterUser:
    """register_user() 服務函式測試。"""

    def test_creates_user_with_hashed_password(self) -> None:
        """應建立使用者並以雜湊形式儲存密碼，而非明文。"""
        user = services.register_user(
            email="new@example.com", password="Password123!", display_name="New"
        )
        assert user.pk is not None
        assert user.email == "new@example.com"
        # 確認密碼已雜湊：check_password 為 True，原文比對為 False。
        assert user.check_password("Password123!")
        assert user.password != "Password123!"


@pytest.mark.django_db
class TestLoginUser:
    """login_user() 服務函式測試，含暴力破解防護邏輯。"""

    def test_returns_tokens_on_success(self) -> None:
        """正確憑證應回傳 (user, access_token, refresh_token) 三元組，且 failed_login_attempts 為 0。"""
        UserFactory(email="ok@example.com", password="testpass123")
        user, access, refresh = services.login_user("ok@example.com", "testpass123")
        assert user.email == "ok@example.com"
        assert access and refresh
        assert user.failed_login_attempts == 0

    def test_wrong_password_raises_and_increments_counter(self) -> None:
        """錯誤密碼應拋出 AuthenticationFailed 並將失敗計數加一。"""
        u = UserFactory(email="bad@example.com", password="testpass123")
        with pytest.raises(AuthenticationFailed):
            services.login_user("bad@example.com", "wrong")
        u.refresh_from_db()
        assert u.failed_login_attempts == 1

    def test_five_failures_sets_lockout(self) -> None:
        """連續失敗達 MAX_LOGIN_ATTEMPTS 次後應設定 lockout_until。"""
        u = UserFactory(email="lockme@example.com", password="testpass123")
        for _ in range(services.MAX_LOGIN_ATTEMPTS):
            with pytest.raises(AuthenticationFailed):
                services.login_user("lockme@example.com", "wrong")
        u.refresh_from_db()
        assert u.lockout_until is not None

    def test_locked_account_rejected_even_with_correct_password(self) -> None:
        """lockout_until 未過期時，即使密碼正確也應拋出含 locked 訊息的 AuthenticationFailed。"""
        u = UserFactory(email="locked@example.com", password="testpass123")
        u.lockout_until = timezone.now() + timedelta(minutes=15)
        u.save()
        with pytest.raises(AuthenticationFailed, match="locked"):
            services.login_user("locked@example.com", "testpass123")

    def test_nonexistent_user_raises_generic_error(self) -> None:
        """不存在的帳號應拋出通用錯誤訊息（防止帳號枚舉）。"""
        with pytest.raises(AuthenticationFailed, match="Invalid"):
            services.login_user("ghost@example.com", "whatever")

    def test_success_resets_failed_attempts(self) -> None:
        """登入成功後應將 failed_login_attempts 重置為 0。"""
        u = UserFactory(email="reset@example.com", password="testpass123")
        u.failed_login_attempts = 3
        u.save()
        services.login_user("reset@example.com", "testpass123")
        u.refresh_from_db()
        assert u.failed_login_attempts == 0


@pytest.mark.django_db
class TestRefreshAccessToken:
    """refresh_access_token() 服務函式測試。"""

    def test_rotates_token_pair(self) -> None:
        """應回傳新的 access/refresh token，且新 refresh token 與舊的不同（輪換機制）。"""
        UserFactory(email="rt@example.com", password="testpass123")
        _, _, refresh = services.login_user("rt@example.com", "testpass123")
        new_access, new_refresh = services.refresh_access_token(refresh)
        assert new_access and new_refresh
        assert new_refresh != refresh


@pytest.mark.django_db
class TestLogoutUser:
    """logout_user() 服務函式測試。"""

    def test_silently_ignores_invalid_token(self) -> None:
        """無效 token 不應拋出例外（靜默忽略，視同已登出）。"""
        # 不應拋出：logout 是使用者主動操作，token 已失效視同已登出。
        services.logout_user("not-a-real-token")


@pytest.mark.django_db
class TestUserQuerySet:
    """UserQuerySet 自訂查詢方法測試。"""

    def test_search_by_email(self) -> None:
        """search() 應能依 email 關鍵字過濾，只回傳符合的使用者。"""
        UserFactory(email="findme@example.com", display_name="X")
        UserFactory(email="other@example.com", display_name="Y")
        results = list(User.objects.search("findme"))
        assert len(results) == 1
        assert results[0].email == "findme@example.com"

    def test_search_by_display_name(self) -> None:
        """search() 應能依 display_name 關鍵字過濾。"""
        UserFactory(email="a@x.com", display_name="Alice Smith")
        UserFactory(email="b@x.com", display_name="Bob Jones")
        results = list(User.objects.search("alice"))
        assert len(results) == 1

    def test_empty_search_returns_all(self) -> None:
        """空字串查詢應回傳全部使用者。"""
        UserFactory.create_batch(3)
        assert User.objects.search("").count() >= 3

    def test_get_by_email_for_auth_returns_inactive_user(self) -> None:
        """get_by_email_for_auth() 應回傳已停用帳號（供 lockout 檢查使用）。"""
        u = UserFactory(email="inactive@example.com", is_active=False)
        assert User.objects.get_by_email_for_auth("inactive@example.com") == u
