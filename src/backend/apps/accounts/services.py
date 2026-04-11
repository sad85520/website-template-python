"""Business logic for accounts."""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .repositories import UserRepository

REFRESH_TOKEN_COOKIE = getattr(settings, "REFRESH_TOKEN_COOKIE_NAME", "refreshToken")
ACCESS_TOKEN_LIFETIME: timedelta = settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]

# Default repository instance; can be replaced in tests for isolation.
_user_repo = UserRepository()


def register_user(
    email: str,
    password: str,
    display_name: str,
    *,
    user_repo: UserRepository | None = None,
) -> User:
    """建立新使用者。"""
    repo = user_repo or _user_repo
    return repo.create(email=email, password=password, display_name=display_name)


def login_user(
    email: str,
    password: str,
    *,
    user_repo: UserRepository | None = None,
) -> tuple[User, str, str]:
    """
    驗證使用者並回傳 (user, access_token, refresh_token_str)。
    Raises AuthenticationFailed if credentials are invalid or account is locked.
    """
    from rest_framework.exceptions import AuthenticationFailed

    repo = user_repo or _user_repo

    # Check if the account exists and is currently locked before authenticating.
    candidate = repo.get_by_email_for_auth(email)
    if candidate is not None and candidate.lockout_until and candidate.lockout_until > timezone.now():
        raise AuthenticationFailed("Account is temporarily locked. Try again later.")

    user = authenticate(username=email, password=password)
    if user is None:
        # Increment failed attempts on the candidate user if they exist.
        if candidate is not None:
            candidate.failed_login_attempts += 1
            if candidate.failed_login_attempts >= 5:
                candidate.lockout_until = timezone.now() + timedelta(minutes=15)
            repo.save(candidate)
        raise AuthenticationFailed("Invalid email or password.")
    if not user.is_active:
        raise AuthenticationFailed("Account is disabled.")

    # Reset lockout state on successful authentication.
    user.failed_login_attempts = 0
    user.lockout_until = None
    repo.save(user)

    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    return user, access_token, refresh_token


def refresh_access_token(refresh_token_str: str) -> tuple[str, str]:
    """
    Rotate refresh token 並回傳 (new_access_token, new_refresh_token)。
    Raises TokenError if token is invalid/expired.
    """
    repo = _user_repo
    refresh = RefreshToken(refresh_token_str)  # type: ignore[arg-type]
    new_access_token = str(refresh.access_token)
    refresh.blacklist()

    user = repo.get_by_id(refresh["user_id"])
    if user is None:
        raise ValueError("User not found for refresh token")
    new_refresh = RefreshToken.for_user(user)
    new_refresh_token = str(new_refresh)

    return new_access_token, new_refresh_token


def logout_user(refresh_token_str: str) -> None:
    """Blacklist refresh token。"""
    try:
        refresh = RefreshToken(refresh_token_str)  # type: ignore[arg-type]
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
