from django.db import models
from django.utils import timezone
from decimal import Decimal


class Product(models.Model):
    """
    Product master.

    Google Sheet / QuickBooks controls:
        - category
        - subcategory
        - level3
        - level4
        - hierarchy_path
        - qty
        - avg_cost

    InventoryPro Admin controls:
        - sales_price
        - reorder_qty

    Sync controls:
        - active
        - updated_at
    """

    product_name = models.CharField(
        max_length=250,
        unique=True,
        db_index=True,
    )

    category = models.CharField(
        max_length=150,
        blank=True,
        default="",
        db_index=True,
    )

    subcategory = models.CharField(
        max_length=150,
        blank=True,
        default="",
        db_index=True,
    )

    level3 = models.CharField(
        max_length=150,
        blank=True,
        default="",
        db_index=True,
    )

    level4 = models.CharField(
        max_length=150,
        blank=True,
        default="",
        db_index=True,
    )

    hierarchy_path = models.CharField(
        max_length=600,
        blank=True,
        default="",
        db_index=True,
    )

    qty = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    avg_cost = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # Editable ONLY by InventoryPro Admin
    sales_price = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # Editable ONLY by InventoryPro Admin
    reorder_qty = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    STATUS_CHOICES = (
        ("OK", "OK"),
        ("LOW", "LOW"),
        ("NIL", "NIL"),
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="OK",
        db_index=True,
    )

    active = models.BooleanField(
        default=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "category",
            "subcategory",
            "level3",
            "level4",
            "product_name",
        ]

        indexes = [
            models.Index(fields=["product_name"]),
            models.Index(fields=["category"]),
            models.Index(fields=["subcategory"]),
            models.Index(fields=["level3"]),
            models.Index(fields=["level4"]),
            models.Index(fields=["hierarchy_path"]),
            models.Index(fields=["active"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return self.product_name

    def build_hierarchy_path(self):
        """
        Builds:
        CATEGORY > SUBCATEGORY > LEVEL3 > LEVEL4
        """

        parts = [
            self.category,
            self.subcategory,
            self.level3,
            self.level4,
        ]

        self.hierarchy_path = " > ".join(
            part.strip()
            for part in parts
            if part and part.strip()
        )

    def calculate_status(self):
        """
        Inventory Status

        Qty = 0       -> NIL
        Qty < Reorder -> LOW
        Else          -> OK
        """

        qty = Decimal(self.qty or 0)
        reorder = Decimal(self.reorder_qty or 0)

        if qty <= 0:
            self.status = "NIL"
        elif qty < reorder:
            self.status = "LOW"
        else:
            self.status = "OK"

        return self.status

    def save(self, *args, **kwargs):
        self.build_hierarchy_path()
        self.calculate_status()
        super().save(*args, **kwargs)


class SyncSetting(models.Model):
    """
    Stores sync metadata.
    Only one record is required.
    """

    sheet_hash = models.CharField(
        max_length=64,
        blank=True,
        default="",
    )

    last_sync = models.DateTimeField(
        null=True,
        blank=True,
    )

    total_products = models.PositiveIntegerField(
        default=0,
    )

    added = models.PositiveIntegerField(
        default=0,
    )

    updated = models.PositiveIntegerField(
        default=0,
    )

    removed = models.PositiveIntegerField(
        default=0,
    )

    restored = models.PositiveIntegerField(
        default=0,
    )

    def __str__(self):
        return "Inventory Sync Settings"


class SyncHistory(models.Model):
    STATUS_CHOICES = [
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("SKIPPED", "Skipped"),
    ]

    sync_time = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="SUCCESS",
        db_index=True,
    )

    added_count = models.PositiveIntegerField(
        default=0
    )

    updated_count = models.PositiveIntegerField(
        default=0
    )

    restored_count = models.PositiveIntegerField(
        default=0
    )

    removed_count = models.PositiveIntegerField(
        default=0
    )

    total_products = models.PositiveIntegerField(
        default=0
    )

    message = models.TextField(
        blank=True
    )

    duration_seconds = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0
    )

    class Meta:
        ordering = ["-sync_time"]

    def __str__(self):
        return f"{self.sync_time:%Y-%m-%d %H:%M:%S} - {self.status}"
