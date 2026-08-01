from django.db import models
from inventory.models import Product


class PricePage(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return self.name


class PriceListItem(models.Model):
    page = models.ForeignKey(
        PricePage,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    display_order = models.PositiveIntegerField(default=0)
    visible = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return self.product.product_name
