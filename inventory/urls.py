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
        "search_products/",
        views.search_products,
        name="search_products"
    ),

    path(
        "product/<int:pk>/edit/",
        views.product_edit,
        name="product_edit"
    ),

    path(
        "sync/",
        views.manual_sync,
        name="manual_sync"
    ),

    path(
        "dashboard/",
        views.dashboard,
        name="dashboard"
    ),

]
