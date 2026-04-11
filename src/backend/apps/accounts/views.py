"""Auth and User API views."""
from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError

from apps.core import responses
from apps.core.pagination import StandardPagination

from . import services
from .models import User
from .repositories import UserRepository
from .serializers import (
    LoginResponseSerializer,
    LoginSerializer,
    RegisterSerializer,
    TokenRefreshResponseSerializer,
    UserSerializer,
)

REFRESH_COOKIE = getattr(settings, "REFRESH_TOKEN_COOKIE_NAME", "refreshToken")

# 模組層級的 repository 實例：所有 view 共享同一個無狀態物件，
# 此為唯一允許直接存取 DB 的入口（透過 UserRepository 封裝），views 不應直接呼叫 ORM。
_user_repo = UserRepository()


# ─── Auth Views ───────────────────────────────────────────────────────────────


class RegisterView(APIView):
    """使用者註冊端點，不需要驗證，並套用匿名流量限制。"""

    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    @extend_schema(request=RegisterSerializer, responses={201: UserSerializer})
    def post(self, request: Request) -> Response:
        """建立新使用者帳號。

        Args:
            request: 包含 email、password、display_name 的請求。

        Returns:
            HTTP 201 及新建立的使用者資料。
        """
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = services.register_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            display_name=serializer.validated_data["display_name"],
        )
        return responses.created(UserSerializer(user).data)


class LoginView(APIView):
    """使用者登入端點，驗證成功後以 HttpOnly cookie 回傳 refresh token。"""

    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    @extend_schema(request=LoginSerializer, responses={200: LoginResponseSerializer})
    def post(self, request: Request) -> Response:
        """驗證使用者憑證並回傳 access token，同時以 HttpOnly cookie 設定 refresh token。

        Args:
            request: 包含 email 與 password 的請求。

        Returns:
            HTTP 200 及 access_token、expires_in，refresh token 寫入 HttpOnly cookie。
        """
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        _user, access_token, refresh_token = services.login_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )

        cookie_opts = services.build_refresh_cookie_options(secure=not settings.DEBUG)
        response = responses.success(
            {
                "access_token": access_token,
                "expires_in": services.get_access_token_lifetime_seconds(),
            }
        )
        response.set_cookie(value=refresh_token, **cookie_opts)  # type: ignore[arg-type]
        return response


class TokenRefreshView(APIView):
    """Token 刷新端點，從 HttpOnly cookie 讀取 refresh token 並輪轉出新的 token 對。"""

    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    @extend_schema(responses={200: TokenRefreshResponseSerializer})
    def post(self, request: Request) -> Response:
        """刷新 access token 並輪轉 refresh token。

        Args:
            request: refresh token 從 HttpOnly cookie 讀取，無需 body。

        Returns:
            HTTP 200 及新的 access_token、expires_in，新的 refresh token 寫入 cookie。
        """
        # refresh token 從 HttpOnly cookie 讀取，而非 request body，
        # 前端 JavaScript 無法讀取此 cookie，防止 XSS 攻擊竊取 refresh token。
        refresh_token_str = request.COOKIES.get(REFRESH_COOKIE)
        if not refresh_token_str:
            return responses.fail("Refresh token not found.", status=status.HTTP_401_UNAUTHORIZED)

        try:
            new_access, new_refresh = services.refresh_access_token(refresh_token_str)
        except TokenError:
            return responses.fail("Invalid or expired refresh token.", status=status.HTTP_401_UNAUTHORIZED)

        cookie_opts = services.build_refresh_cookie_options(secure=not settings.DEBUG)
        response = responses.success(
            {
                "access_token": new_access,
                "expires_in": services.get_access_token_lifetime_seconds(),
            }
        )
        response.set_cookie(value=new_refresh, **cookie_opts)  # type: ignore[arg-type]
        return response


class LogoutView(APIView):
    """使用者登出端點，黑名單 refresh token 並清除 cookie。"""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: None})
    def post(self, request: Request) -> Response:
        """使 refresh token 失效並清除客戶端 cookie。

        Args:
            request: 需攜帶有效的 access token，refresh token 從 cookie 讀取。

        Returns:
            HTTP 200，同時清除 refresh token cookie。
        """
        refresh_token_str = request.COOKIES.get(REFRESH_COOKIE)
        if refresh_token_str:
            services.logout_user(refresh_token_str)

        response = responses.success(None)
        # delete_cookie 僅清除客戶端的 cookie，token 本身需透過 blacklist 使其失效；
        # 兩個步驟缺一不可：僅清除 cookie 無法使已外洩的 token 失效，僅 blacklist 無法清除 cookie。
        response.delete_cookie(REFRESH_COOKIE)
        return response


# ─── User Views ───────────────────────────────────────────────────────────────


class MeView(APIView):
    """取得目前登入使用者自身資料的端點。"""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserSerializer})
    def get(self, request: Request) -> Response:
        """回傳目前已驗證使用者的資料。

        Args:
            request: 需攜帶有效的 access token。

        Returns:
            HTTP 200 及目前使用者的序列化資料。
        """
        # assert 用於型別窄化（type narrowing）：IsAuthenticated 已保證 request.user 不是匿名使用者，
        # 此處協助靜態分析工具（mypy）推斷出正確型別，而非作為執行期防衛。
        assert isinstance(request.user, User)
        return responses.success(UserSerializer(request.user).data)


class UserListView(APIView):
    """管理員專用：分頁查詢所有使用者，支援關鍵字搜尋。"""

    permission_classes = [IsAdminUser]

    @extend_schema(responses={200: UserSerializer(many=True)})
    def get(self, request: Request) -> Response:
        """分頁回傳使用者清單，可透過 ?search= 篩選。

        Args:
            request: 需具備 Admin 權限，可帶 ?search= 與 ?page=、?limit= 查詢參數。

        Returns:
            HTTP 200 及帶分頁 meta 的使用者清單。
        """
        search = request.query_params.get("search", "")
        queryset = _user_repo.search(search)

        paginator = StandardPagination()
        # paginate_queryset() 必須先於序列化呼叫，它會對 queryset 執行 LIMIT/OFFSET，
        # 並將分頁狀態寫入 paginator 物件；get_paginated_response() 才能讀取此狀態組裝 meta。
        page = paginator.paginate_queryset(queryset, request)
        serializer = UserSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class UserDetailView(APIView):
    """管理員專用：依 ID 查詢單一使用者。"""

    permission_classes = [IsAdminUser]

    @extend_schema(responses={200: UserSerializer})
    def get(self, request: Request, pk: str) -> Response:
        """回傳指定使用者的資料。

        Args:
            request: 需具備 Admin 權限。
            pk: 使用者的 UUID 字串。

        Returns:
            HTTP 200 及使用者序列化資料；使用者不存在時回傳 404。
        """
        user = _user_repo.get_by_id(pk)
        if user is None:
            return responses.fail("User not found.", status=status.HTTP_404_NOT_FOUND)
        return responses.success(UserSerializer(user).data)
