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
        'add-category/',
        views.add_category,
        name='add_category'
    ),

    path(
        'reorder-categories/',
        views.reorder_categories,
        name='reorder_categories'
    ),

    path(
        'rename-category/',
        views.rename_category,
        name='rename_category'
    ),

    path(
        '<slug:slug>/',
        views.price_page,
        name='price_page'
    ),

    path(
        'edit/<int:page_id>/',
        views.edit_page,
        name='edit_page'
    ),

    path(
        'reorder/<int:page_id>/',
        views.reorder_page,
        name='reorder_page'
    ),

    path(
        'toggle/<int:page_id>/',
        views.toggle_item,
        name='toggle_item'
    ),

    path(
        'remove/<int:page_id>/',
        views.remove_item,
        name='remove_item'
    ),

    path(
        'add-products/<int:page_id>/',
        views.add_products,
        name='add_products'
    ),

    path(
        'add-heading/<int:page_id>/',
        views.add_heading,
        name='add_heading'
    ),



]
