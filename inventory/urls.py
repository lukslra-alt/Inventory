from django.urls import path
from . import views

urlpatterns = [

    path("", views.dashboard, name="main"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("search_products/", views.search_products, name="search_products"),
    path("product/<path:pk>/edit/", views.product_edit, name="product_edit"),
    path("sync/", views.sync_page, name="sync_page"),
    path("sync/products/", views.sync_products, name="sync_products"),
    path("sync/customers/", views.sync_customers, name="sync_customers"),
    path("sync/all/", views.manual_sync, name="manual_sync"),
    path("offline-products/", views.offline_products, name="offline_products"),

]
