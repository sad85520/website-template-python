"""測試用 factory，使用 factory_boy 建立 User 實例。"""
import factory
from factory.django import DjangoModelFactory

from apps.accounts.models import User


class UserFactory(DjangoModelFactory):
    """建立測試用 User 實例的工廠，預設產生有效且已啟用的一般使用者。"""

    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    display_name = factory.Faker("name")
    # PostGenerationMethodCall 會在物件建立後呼叫 set_password()，
    # 確保密碼以雜湊形式存入 DB，而非明文——與真實使用者建立流程一致。
    password = factory.PostGenerationMethodCall("set_password", "Password123!")
    role = User.Role.USER
    is_active = True
