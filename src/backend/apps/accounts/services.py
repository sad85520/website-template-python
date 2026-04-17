"""Business logic for accounts.

本模組直接使用 ``User.objects`` 查詢介面（透過 ``UserQuerySet`` 封裝常用查詢），
不再透過額外的 Repository 層，理由見 ``docs/adr/ADR-002-remove-repository-layer.md``：
- Django ORM 已提供 QuerySet 抽象，Repository 只會形成冗餘包裝
- Service 層測試改以 ``@pytest.mark.django_db`` 搭配真實 ORM，避免 mock 與實際行為漂移
"""
import contextlib
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User

REFRESH_TOKEN_COOKIE = getattr(settings, "REFRESH_TOKEN_COOKIE_NAME", "refreshToken")
ACCESS_TOKEN_LIFETIME: timedelta = settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]

# 連續登入失敗上限與鎖定時長；提取為常數以便單元測試與未來調整。
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)


def register_user(email: str, password: str, display_name: str) -> User:
    """建立並儲存新使用者帳號。

    Args:
        email: 使用者電子郵件（登入帳號）。
        password: 明文密碼，由 UserManager 雜湊後儲存。
        display_name: 使用者顯示名稱。

    Returns:
        已建立的 User 實例。
    """
    return User.objects.create_user(email=email, password=password, display_name=display_name)


def login_user(email: str, password: str) -> tuple[User, str, str]:
    """驗證使用者並回傳 access token 與 refresh token。

    Args:
        email: 使用者電子郵件。
        password: 明文密碼。

    Returns:
        (user, access_token, refresh_token_str) 三元組。

    Raises:
        AuthenticationFailed: 帳密錯誤、帳號停用或仍處於鎖定期間時拋出。
    """
    # 鎖定檢查必須在 authenticate() 之前進行：若先呼叫 authenticate()，
    # Django 內建機制會在密碼正確時放行，導致已鎖定帳號仍能登入。
    candidate = User.objects.get_by_email_for_auth(email)
    if candidate is not None and candidate.lockout_until and candidate.lockout_until > timezone.now():
        raise AuthenticationFailed("Account is temporarily locked. Try again later.")

    user = authenticate(username=email, password=password)
    if user is None:
        # 無論是帳號不存在還是密碼錯誤，統一回傳相同訊息，
        # 防止攻擊者透過錯誤訊息的差異來枚舉有效帳號。
        if candidate is not None:
            # 以 F expression 進行原子遞增，避免多個並發登入失敗請求之間的
            # read-modify-write race condition（先讀舊值、本機 +1 再寫回會覆蓋彼此遞增）。
            User.objects.filter(pk=candidate.pk).update(
                failed_login_attempts=F("failed_login_attempts") + 1
            )
            candidate.refresh_from_db(fields=["failed_login_attempts"])
            if candidate.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
                User.objects.filter(pk=candidate.pk).update(
                    lockout_until=timezone.now() + LOCKOUT_DURATION
                )
        raise AuthenticationFailed("Invalid email or password.")
    if not user.is_active:
        raise AuthenticationFailed("Account is disabled.")

    # Reset lockout state on successful authentication.
    user.failed_login_attempts = 0
    user.lockout_until = None
    user.save(update_fields=["failed_login_attempts", "lockout_until"])

    refresh = RefreshToken.for_user(user)
    return user, str(refresh.access_token), str(refresh)


def refresh_access_token(refresh_token_str: str) -> tuple[str, str]:
    """輪轉 refresh token 並回傳新的 token 對。

    Args:
        refresh_token_str: 目前有效的 refresh token 字串（JWT 格式）。

    Returns:
        (new_access_token, new_refresh_token) 二元組。

    Raises:
        TokenError: Token 不合法或已過期（由 simplejwt 拋出）。
        ValueError: Token 對應的使用者已不存在。
    """
    refresh = RefreshToken(refresh_token_str)  # type: ignore[arg-type]
    new_access_token = str(refresh.access_token)
    # 必須先取出 access_token，再呼叫 blacklist()，
    # 因為 blacklist() 會讓此 refresh token 物件失效，後續存取 claims 可能拋出例外。
    refresh.blacklist()

    # blacklist() 使此 token 失效，但不清除 Python 物件本身的 payload；
    # refresh["user_id"] 是直接讀取已解碼的 JWT claims（對應 SIMPLE_JWT["USER_ID_CLAIM"]），
    # 此時仍可安全存取，無需重新解碼。
    # 重新查詢確保帳號在 token 發出後未被停用或刪除。
    user = User.objects.filter(pk=refresh["user_id"]).first()
    if user is None:
        raise ValueError("User not found for refresh token")
    new_refresh = RefreshToken.for_user(user)
    return new_access_token, str(new_refresh)


def logout_user(refresh_token_str: str) -> None:
    """將 refresh token 加入黑名單使其立即失效。

    靜默忽略無效或已失效的 token：logout 是使用者主動發起的操作，
    token 已失效視同已登出，不需要向前端回報錯誤。

    Args:
        refresh_token_str: 要撤銷的 refresh token 字串（JWT 格式）。
    """
    with contextlib.suppress(Exception):
        RefreshToken(refresh_token_str).blacklist()  # type: ignore[arg-type]


def get_access_token_lifetime_seconds() -> int:
    """回傳 access token 有效期秒數（由 SIMPLE_JWT 設定決定）。"""
    return int(ACCESS_TOKEN_LIFETIME.total_seconds())


def build_refresh_cookie_options(secure: bool) -> dict[str, object]:
    """建立 refresh token cookie 的安全選項字典。

    max_age 與 REFRESH_TOKEN_LIFETIME 保持一致，確保 cookie 不會比 token 早或晚過期，
    否則 cookie 可能已消失但 token 黑名單中仍保留舊記錄，造成邏輯不一致。

    Args:
        secure: 是否啟用 Secure 屬性（生產環境應傳 True，開發環境可傳 False）。

    Returns:
        可直接傳入 ``Response.set_cookie(**opts)`` 的關鍵字引數字典。
    """
    lifetime: timedelta = settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]
    return {
        "key": REFRESH_TOKEN_COOKIE,
        "httponly": True,
        "secure": secure,
        "samesite": "Strict",
        "max_age": int(lifetime.total_seconds()),
    }
