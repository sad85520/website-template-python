"""Business logic for accounts."""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


REFRESH_TOKEN_COOKIE = getattr(settings, "REFRESH_TOKEN_COOKIE_NAME", "refreshToken")
ACCESS_TOKEN_LIFETIME: timedelta = settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]


def register_user(email: str, password: str, display_name: str) -> User:
    """建立新使用者。"""
    return User.objects.create_user(
        email=email,
        password=password,
        display_name=display_name,
    )


def login_user(email: str, password: str) -> tuple[User, str, str]:
    """
    驗證使用者並回傳 (user, access_token, refresh_token_str)。
    Raises AuthenticationFailed if credentials are invalid.
    """
    from rest_framework.exceptions import AuthenticationFailed

    user = authenticate(username=email, password=password)
    if user is None:
        raise AuthenticationFailed("Invalid email or password.")
    if not user.is_active:
        raise AuthenticationFailed("Account is disabled.")

    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    return user, access_token, refresh_token


def refresh_access_token(refresh_token_str: str) -> tuple[str, str]:
    """
    Rotate refresh token 並回傳 (new_access_token, new_refresh_token)。
    Raises TokenError if token is invalid/expired.
    """
    refresh = RefreshToken(refresh_token_str)
    new_access_token = str(refresh.access_token)
    refresh.blacklist()

    new_refresh = RefreshToken.for_user(
        User.objects.get(id=refresh["user_id"])
    )
    new_refresh_token = str(new_refresh)

    return new_access_token, new_refresh_token


def logout_user(refresh_token_str: str) -> None:
    """Blacklist refresh token。"""
    try:
        refresh = RefreshToken(refresh_token_str)
        refresh.blacklist()
    except Exception:
        pass  # 若 token 已過期或無效，靜默忽略


def get_access_token_lifetime_seconds() -> int:
    return int(ACCESS_TOKEN_LIFETIME.total_seconds())


def build_refresh_cookie_options(secure: bool) -> dict[str, object]:
    lifetime: timedelta = settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]
    return {
        "key": REFRESH_TOKEN_COOKIE,
        "httponly": True,
        "secure": secure,
        "samesite": "Strict",
        "max_age": int(lifetime.total_seconds()),
    }
