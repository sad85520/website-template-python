"""測試用 factory，使用 factory_boy 建立 User 實例。"""

import factory
from factory.django import DjangoModelFactory

from apps.accounts.models import User

# 測試預設密碼常數：當測試需要用 factory 產生的 user 登入時，應 import 此常數，
# 避免在多個測試檔案散落同一明文字串（重新命名或長度調整時只改一處）。
DEFAULT_PASSWORD = "Password123!"


class UserFactory(DjangoModelFactory):
    """建立測試用 User 實例的工廠，預設產生有效且已啟用的一般使用者。"""

    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    display_name = factory.Faker("name")
    # PostGenerationMethodCall 會在物件建立後呼叫 set_password()，
    # 確保密碼以雜湊形式存入 DB，而非明文——與真實使用者建立流程一致。
    password = factory.PostGenerationMethodCall("set_password", DEFAULT_PASSWORD)
    role = User.Role.USER
    is_active = True
