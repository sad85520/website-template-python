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
    password = serializers.CharField(min_length=8, write_only=True)
    display_name = serializers.CharField(min_length=2, max_length=100)

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email is already registered.")
        return value

    def validate_password(self, value: str) -> str:
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
