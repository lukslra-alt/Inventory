from django.urls import path
from . import views

urlpatterns = [

    path(
        '',
        views.price_categories,
        name='price_categories'
    ),

    path(
        'manage/',
        views.price_manage,
        name='price_manage'
    ),

    path(
        '<slug:slug>/',
        views.price_page,
        name='price_page'
    ),

    path(
        'add-products/<int:page_id>/',
        views.add_products,
        name='add_products'
    ),



]
