from django.contrib import admin
from .models import Customer, Invoice, InvoiceItem


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "total_qty", "total_amount", "balance")
    search_fields = ("name",)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "customer", "date", "total", "balance")
    list_filter = ("customer",)
    search_fields = ("invoice_number", "customer__name")
    inlines = [InvoiceItemInline]
