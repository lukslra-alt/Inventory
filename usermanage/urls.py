from django.urls import path
from . import views

app_name = "usermanage"

urlpatterns = [
    path("", views.user_list, name="user_list"),
    path("add/", views.user_add, name="user_add"),
    path("<int:pk>/edit/", views.user_edit, name="user_edit"),
    path("<int:pk>/delete/", views.user_delete, name="user_delete"),
    path(
        "<int:pk>/reset-password/",
        views.user_reset_password,
        name="user_reset_password",
    ),
]
