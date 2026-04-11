"""Custom User model with email-based authentication."""
import uuid
from typing import Any

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager["User"]):
    def create_user(
        self, email: str, password: str, display_name: str = "", **extra_fields: Any
    ) -> "User":
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, display_name=display_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields: Any) -> "User":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        USER = "user", "User"
        ADMIN = "admin", "Admin"

    # 使用 UUID 作為主鍵可防止外部透過遞增 ID 推測使用者總數或枚舉帳號。
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, max_length=256)
    display_name = models.CharField(max_length=100)
    # role 欄位用於應用層授權（如 IsAdminUser）；is_staff 則控制 Django Admin 後台存取權限，兩者職責不同，不可混用。
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # 暴力破解防護欄位：連續登入失敗達閾值時，設定 lockout_until 鎖定帳號。
    # 這兩個欄位由 services.login_user 維護，其他地方不應直接修改。
    failed_login_attempts = models.IntegerField(default=0)
    lockout_until = models.DateTimeField(null=True, blank=True)

    # 改用 email 作為登入憑證，USERNAME_FIELD 必須對應到一個 unique=True 欄位，
    # REQUIRED_FIELDS 則是執行 createsuperuser 時額外要求輸入的欄位。
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["display_name"]

    objects: UserManager = UserManager()

    class Meta:
        db_table = "accounts_user"
        # 預設依 created_at 降冪排序（最新使用者優先）；
        # 此排序會套用至所有未指定 .order_by() 的 QuerySet，需確保 created_at 欄位有建立索引，
        # 否則大資料量時每次查詢都會觸發全表排序。
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.email
