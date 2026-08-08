from django.contrib import admin
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "item",
        "product_name",
        "cost",
        "qty",
        "sales_price",
        "reorder_qty",
        "status",
        "active",
    )

    list_filter = ("status",)

    search_fields = ("product_name",)

    ordering = ("product_name",)