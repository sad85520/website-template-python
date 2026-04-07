import factory
from factory.django import DjangoModelFactory

from apps.accounts.models import User


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    display_name = factory.Faker("name")
    password = factory.PostGenerationMethodCall("set_password", "Password123!")
    role = User.Role.USER
    is_active = True
