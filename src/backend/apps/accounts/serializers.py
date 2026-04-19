"""Serializers for accounts app."""

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer[User]):
    """使用者資料序列化器，用於 API 回應中的使用者資料呈現。"""

    class Meta:
        model = User
        fields = ["id", "email", "display_name", "role", "created_at"]
        read_only_fields = ["id", "role", "created_at"]


class RegisterSerializer(serializers.Serializer[User]):
    """使用者註冊請求序列化器，包含 email 唯一性與密碼強度驗證。"""

    email = serializers.EmailField(max_length=256)
    # write_only=True 確保密碼不會出現在任何序列化輸出（如 API 回應）中。
    password = serializers.CharField(min_length=8, write_only=True)
    display_name = serializers.CharField(min_length=2, max_length=100)

    def validate_email(self, value: str) -> str:
        """驗證 email 尚未被其他帳號使用。

        Args:
            value: 輸入的電子郵件。

        Returns:
            驗證通過的電子郵件字串。

        Raises:
            ValidationError: email 已被註冊時拋出。
        """
        # 在 serializer 層檢查 email 唯一性，可在進入 service 層前就提早回傳 400，
        # 但需注意此處存在 TOCTOU（time-of-check/time-of-use）競爭條件：
        # 兩個請求同時通過此檢查後，資料庫的 unique constraint 才是最終防線。
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email is already registered.")
        return value

    def validate_display_name(self, value: str) -> str:
        """驗證顯示名稱非純空白。

        Args:
            value: 輸入的顯示名稱。

        Returns:
            去除前後空白後的顯示名稱。

        Raises:
            ValidationError: 去除空白後長度不足 2 字元時拋出。
        """
        # CharField 預設只把純空白 "" 視為空，"  " 會通過 min_length=2 檢查；
        # strip 後再次檢查長度確保呈現給其他使用者的顯示名稱不是隱形空白。
        stripped = value.strip()
        if len(stripped) < 2:
            raise serializers.ValidationError(
                "Display name must contain at least 2 non-whitespace characters."
            )
        return stripped

    def validate_password(self, value: str) -> str:
        """透過 Django 內建驗證器檢查密碼強度。

        Args:
            value: 輸入的明文密碼。

        Returns:
            驗證通過的密碼字串。

        Raises:
            ValidationError: 密碼不符合 AUTH_PASSWORD_VALIDATORS 設定的規則時拋出。
        """
        # 呼叫 Django 內建密碼驗證器（settings.AUTH_PASSWORD_VALIDATORS），
        # 包含長度、常見密碼、數字密碼等多道檢查。
        validate_password(value)
        return value


class LoginSerializer(serializers.Serializer[None]):
    """使用者登入請求序列化器。"""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class LoginResponseSerializer(serializers.Serializer[None]):
    """登入成功回應序列化器，描述 access_token 與過期時間。"""

    access_token = serializers.CharField()
    expires_in = serializers.IntegerField()


class TokenRefreshResponseSerializer(serializers.Serializer[None]):
    """Token 刷新成功回應序列化器，描述新的 access_token 與過期時間。"""

    access_token = serializers.CharField()
    expires_in = serializers.IntegerField()
