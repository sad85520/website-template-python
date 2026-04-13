from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Accounts 應用程式設定，定義預設主鍵類型與應用程式名稱。"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Accounts"
