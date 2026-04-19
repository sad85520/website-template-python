"""Django Admin 使用者管理設定。"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):  # type: ignore[type-arg]
    """自訂使用者後台管理介面，以 email 取代預設的 username 欄位。"""

    list_display = ["email", "display_name", "role", "is_active", "created_at"]
    list_filter = ["role", "is_active", "is_staff"]
    search_fields = ["email", "display_name"]
    ordering = ["-created_at"]
    # 自訂 fieldsets 是必要的：BaseUserAdmin 預設使用 username 欄位，
    # 此處改為 email 以配合自訂 User model 的 USERNAME_FIELD = "email"。
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("個人資訊", {"fields": ("display_name", "role")}),
        (
            "權限",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("日期", {"fields": ("last_login",)}),
    )
    # add_fieldsets 定義「新增使用者」表單的欄位，password1/password2 是 Django Admin 內建的密碼確認機制。
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "display_name", "password1", "password2", "role"),
            },
        ),
    )
