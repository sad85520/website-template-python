"""Custom User model with email-based authentication."""
import uuid
from typing import Any

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models import Q


class UserQuerySet(models.QuerySet["User"]):
    """封裝使用者常用查詢邏輯，透過 ``BaseUserManager.from_queryset`` 暴露給 ``User.objects``。

    將查詢邏輯放在 QuerySet 而非 Repository 層的理由見
    ``docs/adr/ADR-002-remove-repository-layer.md``：直接沿用 Django ORM 的可鏈結 QuerySet，
    避免重複包裝 ``.filter().first()`` 等瑣碎呼叫，同時保留單一職責與可測試性。
    """

    def get_by_email(self, email: str) -> "User | None":
        """以 email 查詢使用者，不存在則回傳 None（避免呼叫端處理 DoesNotExist）。"""
        return self.filter(email=email).first()

    def get_by_email_for_auth(self, email: str) -> "User | None":
        """
        authenticate() 之前取得完整帳號狀態（含停用帳號），用於檢查 lockout_until。

        與 ``get_by_email`` 刻意分開：Django 的 authenticate() 只處理 is_active 帳號，
        若以此替代將無法判斷 lockout 狀態，造成鎖定機制失效。
        """
        return self.filter(email=email).first()

    def search(self, query: str) -> "UserQuerySet":
        """依關鍵字比對 email 與 display_name；空字串回傳全部。"""
        if not query:
            return self.all()
        # 使用 Q 物件組合 OR 條件，單次查詢避免 QuerySet 聯集可能造成的重複資料。
        return self.filter(Q(email__icontains=query) | Q(display_name__icontains=query)).distinct()


# ``BaseUserManager.from_queryset(UserQuerySet)`` 會自動把 ``UserQuerySet`` 上的查詢方法
# 複製到 Manager 類別上，避免手動 delegate 造成的重複樣板；
# ``# type: ignore[misc]`` 為 django-stubs 對動態建立之基底類別的已知限制（issue #738），
# 集中在此一行，讓其他檔案完全不需要 ignore。
class UserManager(BaseUserManager["User"].from_queryset(UserQuerySet)):  # type: ignore[misc]
    """自訂使用者管理器，以 email 作為主要識別欄位。

    查詢方法（get_by_email、search 等）由 ``UserQuerySet`` 透過 ``from_queryset`` 自動繼承，
    本類別只保留與 ``BaseUserManager`` 合約相關的建立/管理邏輯。
    """

    def create_user(
        self, email: str, password: str, display_name: str = "", **extra_fields: Any
    ) -> "User":
        """建立並儲存一般使用者。

        Args:
            email: 使用者電子郵件（登入帳號）。
            password: 明文密碼，會透過 set_password 雜湊後儲存。
            display_name: 使用者顯示名稱，預設為空字串。
            **extra_fields: 額外的 User 欄位值。

        Returns:
            已儲存的 User 實例。

        Raises:
            ValueError: email 為空時拋出。
        """
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email)
        # self.model 在動態產生的 from_queryset 基底類別下會被推導為 Any；
        # 顯式標註型別後續才能通過 strict mypy。
        user: User = self.model(email=email, display_name=display_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields: Any) -> "User":
        """建立並儲存超級使用者，自動設定 is_staff、is_superuser 與 Admin 角色。

        Args:
            email: 使用者電子郵件。
            password: 明文密碼。
            **extra_fields: 額外的 User 欄位值。

        Returns:
            已儲存的超級使用者 User 實例。
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """系統使用者實體，以 email 作為登入憑證，內建暴力破解防護欄位。"""

    class Role(models.TextChoices):
        """使用者角色列舉，控制應用層的存取權限。"""

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

    # 顯式標註型別是讓 mypy/django-stubs 正確推導 ``User.objects.xxx`` 回傳型別的關鍵，
    # 若省略將 fallback 到 ``Any``，失去 QuerySet 方法的型別檢查。
    objects: UserManager = UserManager()

    class Meta:
        db_table = "accounts_user"
        # 預設依 created_at 降冪排序（最新使用者優先）；
        # 此排序會套用至所有未指定 .order_by() 的 QuerySet，需確保 created_at 欄位有建立索引，
        # 否則大資料量時每次查詢都會觸發全表排序。
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.email
