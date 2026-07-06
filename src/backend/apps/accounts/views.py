"""Auth and User API views.

回應格式：所有成功路徑直接回傳 DRF 原生格式（``Response(serializer.data, status=...)``），
錯誤路徑由 ``apps.core.exceptions.custom_exception_handler`` 統一轉為 RFC 7807 Problem Details。
理由見 ``docs/adr/ADR-001-drf-native-response-format.md``。
"""

from typing import TYPE_CHECKING

from django.conf import settings
from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError

from apps.core.pagination import StandardPagination

from . import services
from .models import User
from .serializers import (
    LoginResponseSerializer,
    LoginSerializer,
    RegisterSerializer,
    TokenRefreshResponseSerializer,
    UserSerializer,
)

if TYPE_CHECKING:
    from rest_framework.request import Request

REFRESH_COOKIE = getattr(settings, "REFRESH_TOKEN_COOKIE_NAME", "refreshToken")


# ─── Auth Views ───────────────────────────────────────────────────────────────


class RegisterView(APIView):
    """使用者註冊端點，不需要驗證，並套用匿名流量限制。"""

    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    @extend_schema(request=RegisterSerializer, responses={201: UserSerializer})
    def post(self, request: Request) -> Response:
        """建立新使用者帳號並回傳 HTTP 201 與新建使用者資料。"""
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.register_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            display_name=serializer.validated_data["display_name"],
        )
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """使用者登入端點，驗證成功後以 HttpOnly cookie 回傳 refresh token。"""

    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    @extend_schema(request=LoginSerializer, responses={200: LoginResponseSerializer})
    def post(self, request: Request) -> Response:
        """驗證使用者憑證並回傳 access token，同時以 HttpOnly cookie 設定 refresh token。"""
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        _user, access_token, refresh_token = services.login_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )

        response = Response(
            {
                "access_token": access_token,
                "expires_in": services.get_access_token_lifetime_seconds(),
            },
            status=status.HTTP_200_OK,
        )
        cookie_opts = services.build_refresh_cookie_options(secure=not settings.DEBUG)
        response.set_cookie(value=refresh_token, **cookie_opts)  # type: ignore[arg-type]
        return response


class TokenRefreshView(APIView):
    """Token 刷新端點，從 HttpOnly cookie 讀取 refresh token 並輪轉出新的 token 對。"""

    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    @extend_schema(responses={200: TokenRefreshResponseSerializer})
    def post(self, request: Request) -> Response:
        """刷新 access token 並輪轉 refresh token。"""
        # refresh token 從 HttpOnly cookie 讀取，而非 request body，
        # 前端 JavaScript 無法讀取此 cookie，防止 XSS 攻擊竊取 refresh token。
        refresh_token_str = request.COOKIES.get(REFRESH_COOKIE)
        if not refresh_token_str:
            raise AuthenticationFailed("Refresh token not found.")

        try:
            new_access, new_refresh = services.refresh_access_token(refresh_token_str)
        except TokenError as exc:
            raise AuthenticationFailed("Invalid or expired refresh token.") from exc

        response = Response(
            {
                "access_token": new_access,
                "expires_in": services.get_access_token_lifetime_seconds(),
            },
            status=status.HTTP_200_OK,
        )
        cookie_opts = services.build_refresh_cookie_options(secure=not settings.DEBUG)
        response.set_cookie(value=new_refresh, **cookie_opts)  # type: ignore[arg-type]
        return response


class LogoutView(APIView):
    """使用者登出端點，黑名單 refresh token 並清除 cookie。"""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={204: None})
    def post(self, request: Request) -> Response:
        """使 refresh token 失效並清除客戶端 cookie，回傳 HTTP 204。"""
        refresh_token_str = request.COOKIES.get(REFRESH_COOKIE)
        if refresh_token_str:
            services.logout_user(refresh_token_str)

        response = Response(status=status.HTTP_204_NO_CONTENT)
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
        """回傳目前已驗證使用者的資料。"""
        # IsAuthenticated 已保證 request.user 不是匿名使用者；此處顯式 guard 同時做
        # 型別窄化（讓 mypy 推斷出 User）並保留 runtime 防衛 — assert 在 `python -O`
        # 會被移除，不適合作為 production control flow。
        if not isinstance(request.user, User):
            raise AuthenticationFailed("Authenticated user is required.")
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)


class UserListView(APIView):
    """管理員專用：分頁查詢所有使用者，支援關鍵字搜尋。"""

    permission_classes = [IsAdminUser]

    @extend_schema(responses={200: UserSerializer(many=True)})
    def get(self, request: Request) -> Response:
        """分頁回傳使用者清單，可透過 ?search= 篩選。"""
        search = request.query_params.get("search", "")
        queryset = User.objects.search(search)

        paginator = StandardPagination()
        # paginate_queryset() 必須先於序列化呼叫，它會對 queryset 執行 LIMIT/OFFSET，
        # 並將分頁狀態寫入 paginator 物件；get_paginated_response() 才能讀取此狀態組裝 DRF 原生分頁格式。
        page = paginator.paginate_queryset(queryset, request)
        serializer = UserSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class UserDetailView(APIView):
    """管理員專用：依 ID 查詢單一使用者。"""

    permission_classes = [IsAdminUser]

    @extend_schema(responses={200: UserSerializer})
    def get(self, request: Request, pk: str) -> Response:
        """回傳指定使用者的資料；找不到時由例外處理器轉為 RFC 7807 404。"""
        user = User.objects.filter(pk=pk).first()
        if user is None:
            raise Http404("User not found.")
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
