from django.db import models
from decimal import Decimal


def extract_description(item_text):
    """
    Extracts the human-readable description from a QuickBooks-style
    item string such as:

        V BELT:B:B 106 V BELT - SANLUX (B 106 V BELT - SANLUX)
        -> B 106 V BELT - SANLUX

        POLISHER:POLISHER PARTS:6MM TUBE (6MM TUBE)
        -> 6MM TUBE

    The description starts after the final colon. Well-formed items
    then carry the description inside a parenthesised group, so the
    content of the last balanced group is used. Truncated items (cut
    off with '...') fall back to the outermost group that was never
    closed.
    """
    value = (item_text or "").strip()
    if not value:
        return ""

    value = value.rsplit(":", 1)[-1].strip()

    truncated = value.endswith("...")
    work = value[:-3].rstrip() if truncated else value

    if truncated:
        # The description group is cut off, so its closing paren is
        # missing. Walk the text with a stack to find the outermost
        # group that never got closed - that is the description.
        stack = []
        for index, char in enumerate(work):
            if char == "(":
                stack.append(index)
            elif char == ")" and stack:
                stack.pop()

        if stack:
            start = stack[0]
            return work[start + 1:].strip() + "..."
        return work + "..."

    groups = []
    stack = []
    for index, char in enumerate(work):
        if char == "(":
            stack.append(index)
        elif char == ")":
            if stack:
                start = stack.pop()
                groups.append((start, index, work[start + 1:index]))

    if groups:
        last_close = work.rfind(")")
        closing = [g for g in groups if g[1] == last_close]
        if closing:
            group = min(closing, key=lambda g: g[0])
        else:
            group = groups[-1]
        return group[2].strip()

    return value.split(":")[-1].strip()


class Customer(models.Model):
    """A customer account with aggregate quantities, amounts and balance."""
    name = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
    )

    total_qty = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    total_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    balance = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Invoice(models.Model):
    """An invoice issued to a customer, with per-item lines."""
    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )

    customer = models.ForeignKey(
        Customer,
        related_name="invoices",
        on_delete=models.CASCADE,
    )

    date = models.DateField(
        null=True,
        blank=True,
    )

    total = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    balance = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "invoice_number"]

    @property
    def total_qty(self):
        total = sum(
            (item.qty for item in self.items.all()),
            Decimal("0.00"),
        )
        return total

    @property
    def total_amount(self):
        return self.total

    def __str__(self):
        return f"{self.invoice_number} - {self.customer.name}"


class InvoiceItem(models.Model):
    """A single line of an invoice (raw QuickBooks item + quantity/price)."""
    invoice = models.ForeignKey(
        Invoice,
        related_name="items",
        on_delete=models.CASCADE,
    )

    item = models.CharField(
        max_length=600,
        blank=True,
        default="",
    )

    @property
    def description(self):
        return extract_description(self.item)

    qty = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    sales_price = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.invoice_id} - {self.item}"
