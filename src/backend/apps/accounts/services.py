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
    """建立並儲存新使用者帳號。

    Args:
        email: 使用者電子郵件（登入帳號）。
        password: 明文密碼，由 UserManager 雜湊後儲存。
        display_name: 使用者顯示名稱。
        user_repo: 可替換的 repository 實例，主要供測試注入使用。

    Returns:
        已建立的 User 實例。
    """
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

    # 鎖定檢查必須在 authenticate() 之前進行：若先呼叫 authenticate()，
    # Django 內建機制會在密碼正確時放行，導致已鎖定帳號仍能登入。
    candidate = repo.get_by_email_for_auth(email)
    if candidate is not None and candidate.lockout_until and candidate.lockout_until > timezone.now():
        raise AuthenticationFailed("Account is temporarily locked. Try again later.")

    user = authenticate(username=email, password=password)
    if user is None:
        # 無論是帳號不存在還是密碼錯誤，統一回傳相同訊息，
        # 防止攻擊者透過錯誤訊息的差異來枚舉有效帳號。
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
    # 必須先取出 access_token，再呼叫 blacklist()，
    # 因為 blacklist() 會讓此 refresh token 物件失效，後續存取 claims 可能拋出例外。
    refresh.blacklist()

    # 重新查詢使用者以確保帳號仍然存在且有效（例如帳號可能已在 token 發出後被停用）。
    # refresh["user_id"] 是從已驗證的 JWT claims 中取出，對應 SIMPLE_JWT["USER_ID_CLAIM"] 設定值。
    user = repo.get_by_id(refresh["user_id"])
    if user is None:
        raise ValueError("User not found for refresh token")
    new_refresh = RefreshToken.for_user(user)
    new_refresh_token = str(new_refresh)

    return new_access_token, new_refresh_token


def logout_user(refresh_token_str: str) -> None:
    """將 refresh token 加入黑名單使其立即失效。

    靜默忽略無效或已失效的 token：logout 是使用者主動發起的操作，
    token 已失效視同已登出，不需要向前端回報錯誤。

    Args:
        refresh_token_str: 客戶端持有的原始 refresh token 字串。
    """
    try:
        refresh = RefreshToken(refresh_token_str)  # type: ignore[arg-type]
        refresh.blacklist()
    except Exception:
        # 靜默忽略：logout 是使用者主動發起的操作，
        # 若 token 已失效或不合法，視同已登出，不需要向前端回報錯誤。
        pass


def get_access_token_lifetime_seconds() -> int:
    """回傳 access token 有效期秒數（由 SIMPLE_JWT 設定決定）。

    Returns:
        ACCESS_TOKEN_LIFETIME 換算後的整數秒數。
    """
    return int(ACCESS_TOKEN_LIFETIME.total_seconds())


def build_refresh_cookie_options(secure: bool) -> dict[str, object]:
    """建立 refresh token cookie 的安全選項字典。

    max_age 與 REFRESH_TOKEN_LIFETIME 保持一致，確保 cookie 不會比 token 早或晚過期。

    Args:
        secure: 是否設定 Secure 旗標（生產環境應為 True，強制 HTTPS 傳輸）。

    Returns:
        可直接傳入 response.set_cookie(**opts) 的選項字典。
    """
    lifetime: timedelta = settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]
    return {
        "key": REFRESH_TOKEN_COOKIE,
        "httponly": True,
        "secure": secure,
        "samesite": "Strict",
        # max_age 與 REFRESH_TOKEN_LIFETIME 保持一致，確保 cookie 不會比 token 早或晚過期，
        # 否則 cookie 可能已消失但 token 黑名單中仍保留舊記錄，造成邏輯不一致。
        "max_age": int(lifetime.total_seconds()),
    }
