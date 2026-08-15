from django.contrib import admin
from .models import Product, SyncSetting


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


@admin.register(SyncSetting)
class SyncSettingAdmin(admin.ModelAdmin):
    list_display = (
        "sheet_hash",
        "customer_hash",
        "last_sync",
        "total_products",
    )

    readonly_fields = ("last_sync",)