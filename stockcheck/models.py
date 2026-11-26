from django.conf import settings
from django.db import models


class StockCheckRecord(models.Model):
    """One completed physical count for a product.

    The OneToOneField is deliberate: a product can only be counted once until
    the history is reset, which prevents the same item appearing again.
    """

    product = models.OneToOneField(
        "inventory.Product",
        on_delete=models.CASCADE,
        related_name="stock_check_record",
    )
    system_qty = models.DecimalField(max_digits=18, decimal_places=2)
    counted_qty = models.DecimalField(max_digits=18, decimal_places=2)
    variance = models.DecimalField(max_digits=18, decimal_places=2)
    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="stock_checks",
    )
    checked_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-checked_at"]

    def __str__(self):
        return f"{self.product_id} checked {self.checked_at:%Y-%m-%d %H:%M}"
