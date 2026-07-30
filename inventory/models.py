from django.db import models


class Product(models.Model):
    STATUS_OK = "OK"
    STATUS_LOW = "LOW"
    STATUS_NIL = "NIL"

    STATUS_CHOICES = [
        (STATUS_OK, "OK"),
        (STATUS_LOW, "LOW"),
        (STATUS_NIL, "NIL"),
    ]

    product_name = models.CharField(
        max_length=200,
        unique=True,
        db_index=True,
    )

    qty = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    avg_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    # Admin controlled - NEVER overwritten by sync
    sales_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    # Admin controlled - NEVER overwritten by sync
    reorder_qty = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    status = models.CharField(
        max_length=5,
        choices=STATUS_CHOICES,
        default=STATUS_OK,
    )

    active = models.BooleanField(
        default=True,
        db_index=True
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product_name"]

    def update_status(self):
        if self.qty == 0:
            self.status = self.STATUS_NIL
        elif self.qty < self.reorder_qty:
            self.status = self.STATUS_LOW
        else:
            self.status = self.STATUS_OK

    def save(self, *args, **kwargs):
        self.update_status()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.product_name


class SyncHistory(models.Model):
    sync_time = models.DateTimeField(auto_now_add=True)

    file_hash = models.CharField(
        max_length=64,
        blank=True,
    )

    products_updated = models.IntegerField(default=0)

    success = models.BooleanField(default=True)

    message = models.TextField(blank=True)

    class Meta:
        ordering = ["-sync_time"]

    def __str__(self):
        return self.sync_time.strftime("%Y-%m-%d %H:%M:%S")
