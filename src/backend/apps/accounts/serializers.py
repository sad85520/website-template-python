"""Serializers for accounts app."""
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ["id", "email", "display_name", "role", "created_at"]
        read_only_fields = ["id", "role", "created_at"]


class RegisterSerializer(serializers.Serializer[User]):
    email = serializers.EmailField(max_length=256)
    # write_only=True 確保密碼不會出現在任何序列化輸出（如 API 回應）中。
    password = serializers.CharField(min_length=8, write_only=True)
    display_name = serializers.CharField(min_length=2, max_length=100)

    def validate_email(self, value: str) -> str:
        # 在 serializer 層檢查 email 唯一性，可在進入 service 層前就提早回傳 400，
        # 但需注意此處存在 TOCTOU（time-of-check/time-of-use）競爭條件：
        # 兩個請求同時通過此檢查後，資料庫的 unique constraint 才是最終防線。
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email is already registered.")
        return value

    def validate_password(self, value: str) -> str:
        # 呼叫 Django 內建密碼驗證器（settings.AUTH_PASSWORD_VALIDATORS），
        # 包含長度、常見密碼、數字密碼等多道檢查。
        validate_password(value)
        return value


class LoginSerializer(serializers.Serializer[None]):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class LoginResponseSerializer(serializers.Serializer[None]):
    access_token = serializers.CharField()
    expires_in = serializers.IntegerField()


class TokenRefreshResponseSerializer(serializers.Serializer[None]):
    access_token = serializers.CharField()
    expires_in = serializers.IntegerField()
