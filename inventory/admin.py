from django.contrib import admin
from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = (
        "product_name",
        "qty",
        "avg_cost",
        "sales_price",
        "reorder_qty",
        "status",
    )

    list_filter = ("status",)

    search_fields = ("product_name",)

    ordering = ("product_name",)