from django.urls import path

from . import views

urlpatterns = [
    path("", views.stock_check, name="stock_check"),
    path("reset/", views.reset_checks, name="stock_check_reset"),
    path("restore/", views.restore_product, name="stock_check_restore"),
]
