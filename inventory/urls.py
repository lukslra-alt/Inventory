from django.urls import path
from . import views

urlpatterns = [

    path(
        "",
        views.dashboard,
        name="dashboard"
    ),

    path(
        "search/",
        views.product_search,
        name="product_search"
    ),

    path(
        "product/<int:pk>/edit/",
        views.edit_product,
        name="edit_product"
    ),

]
