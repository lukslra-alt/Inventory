from django.contrib import admin
from .models import PricePage, PriceListItem, PriceListHeading
from adminsortable2.admin import SortableAdminMixin, SortableInlineAdminMixin
from django.urls import reverse
from django.utils.html import format_html


class PriceListHeadingInline(
    SortableInlineAdminMixin,
    admin.TabularInline
):
    model = PriceListHeading
    extra = 0


class PriceListItemInline(
    SortableInlineAdminMixin,
    admin.TabularInline
):
    model = PriceListItem
    extra = 0
    autocomplete_fields = ['product']


@admin.register(PricePage)
class PricePageAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = [
        'name',
        'add_products_button'
    ]

    inlines = [
        PriceListItemInline,
        PriceListHeadingInline,
    ]

    def add_products_button(self, obj):
        url = reverse(
            'add_products',
            args=[obj.id]
        )

        return format_html(
            '<a class="button" href="{}">Add Products</a>',
            url
        )

    add_products_button.short_description = "Products"
