from django.urls import path

from apps.accounts.views import MeView, UserDetailView, UserListView

urlpatterns = [
    path("me", MeView.as_view(), name="user-me"),
    path("", UserListView.as_view(), name="user-list"),
    path("<uuid:pk>", UserDetailView.as_view(), name="user-detail"),
]
