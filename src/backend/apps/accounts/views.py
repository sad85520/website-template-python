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

from . import services
from .models import User
from .serializers import (
    LoginResponseSerializer,
    LoginSerializer,
    RegisterSerializer,
    TokenRefreshResponseSerializer,
    UserSerializer,
)

REFRESH_COOKIE = getattr(settings, "REFRESH_TOKEN_COOKIE_NAME", "refreshToken")


# ─── Auth Views ───────────────────────────────────────────────────────────────


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    @extend_schema(request=RegisterSerializer, responses={201: UserSerializer})
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = services.register_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            display_name=serializer.validated_data["display_name"],
        )
        return responses.created(UserSerializer(user).data)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    @extend_schema(request=LoginSerializer, responses={200: LoginResponseSerializer})
    def post(self, request: Request) -> Response:
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
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    @extend_schema(responses={200: TokenRefreshResponseSerializer})
    def post(self, request: Request) -> Response:
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
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: None})
    def post(self, request: Request) -> Response:
        refresh_token_str = request.COOKIES.get(REFRESH_COOKIE)
        if refresh_token_str:
            services.logout_user(refresh_token_str)

        response = responses.success(None)
        response.delete_cookie(REFRESH_COOKIE)
        return response


# ─── User Views ───────────────────────────────────────────────────────────────


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserSerializer})
    def get(self, request: Request) -> Response:
        return responses.success(UserSerializer(request.user).data)


class UserListView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(responses={200: UserSerializer(many=True)})
    def get(self, request: Request) -> Response:
        search = request.query_params.get("search", "")
        queryset = User.objects.all()
        if search:
            queryset = queryset.filter(email__icontains=search) | queryset.filter(
                display_name__icontains=search
            )

        from apps.core.pagination import StandardPagination
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = UserSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class UserDetailView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(responses={200: UserSerializer})
    def get(self, request: Request, pk: str) -> Response:
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return responses.fail("User not found.", status=status.HTTP_404_NOT_FOUND)
        return responses.success(UserSerializer(user).data)
