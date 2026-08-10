import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction

from customers.models import Customer, Invoice, InvoiceItem


def _to_decimal(value):
    if value is None:
        return Decimal("0.00")
    cleaned = str(value).strip().replace(",", "")
    if not cleaned:
        return Decimal("0.00")
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def _parse_date(value):
    if not value:
        return None
    value = str(value).strip()
    for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _cell(row, index):
    if index < len(row):
        return row[index]
    return ""


@transaction.atomic
def import_customer_csv(filepath):
    """
    Parses a QuickBooks-style customer export CSV and upserts
    Customer, Invoice and InvoiceItem records.

    Expected row shapes:
        <Customer Name>,,,,,,,,                -> starts a customer block
        ,Invoice,<date>,<num>,<item>,<balance>,<qty>,<price>,<amount>,
        Total <Customer Name>,,...,<qty>,,<total>,<total>
    """
    result = {
        "customers": 0,
        "invoices": 0,
        "items": 0,
    }

    current_customer = None
    # invoice_number -> {customer, date, rows: [...]}
    pending_invoices = {}

    with open(filepath, newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        rows = list(reader)

    def flush():
        nonlocal pending_invoices
        for invoice_number, data in pending_invoices.items():
            invoice, created = Invoice.objects.update_or_create(
                invoice_number=invoice_number,
                defaults={
                    "customer": data["customer"],
                    "date": data["date"],
                },
            )
            if created:
                result["invoices"] += 1
            else:
                invoice.items.all().delete()

            invoice_total = Decimal("0.00")
            invoice_balance = Decimal("0.00")
            for row in data["rows"]:
                # CSV layout:
                # 4 = Item, 5 = Open Balance, 6 = Qty, 7 = Sales Price, 8 = Amount
                open_balance = _to_decimal(_cell(row, 5))
                qty = _to_decimal(_cell(row, 6))
                sales_price = _to_decimal(_cell(row, 7))
                amount = _to_decimal(_cell(row, 8))

                InvoiceItem.objects.create(
                    invoice=invoice,
                    item=_cell(row, 4).strip(),
                    qty=qty,
                    sales_price=sales_price,
                    amount=amount,
                )

                # Accumulate invoice item amounts.
                invoice_total += amount

                # Accumulate open balances for this invoice.
                invoice_balance += open_balance

                result["items"] += 1

            invoice.total = invoice_total
            invoice.balance = invoice_balance
            invoice.save()

        pending_invoices = {}

    for row in rows:
        if not row:
            continue

        first = (row[0] or "").strip()

        # ---------------------------------------------------------
        # Invoice row
        # ---------------------------------------------------------
        if not first:
            # Blank line or header — check for an invoice line.
            if (len(row) > 1 and row[1] and row[1].strip() == "Invoice"):
                if current_customer is None:
                    continue
                invoice_number = _cell(row, 3).strip()
                if not invoice_number:
                    continue
                data = pending_invoices.get(invoice_number)
                if data is None:
                    data = {
                        "customer": current_customer,
                        "date": _parse_date(_cell(row, 2)),
                        "rows": [],
                    }
                    pending_invoices[invoice_number] = data

                # Add this item row to the invoice.
                data["rows"].append(row)
            continue

        # ---------------------------------------------------------
        # Skip CSV headings
        # ---------------------------------------------------------
        if first == "TOTAL":
            continue

        if first.lower() == "type":
            continue

        # ---------------------------------------------------------
        # Customer total row
        # ---------------------------------------------------------
        if first.startswith("Total"):
            # Update running totals on the customer.
            if current_customer is not None:
                current_customer.balance = _to_decimal(_cell(row, 5))
                current_customer.total_qty = _to_decimal(_cell(row, 6))
                current_customer.total_amount = _to_decimal(_cell(row, 8))
                current_customer.save()
            continue

        # ---------------------------------------------------------
        # New customer block
        # ---------------------------------------------------------

        # Save all invoices belonging to the previous customer.
        flush()

        current_customer, created = Customer.objects.get_or_create(
            name=first,
            defaults={
                "total_qty": Decimal("0.00"),
                "total_amount": Decimal("0.00"),
                "balance": Decimal("0.00"),
            },
        )
        if created:
            result["customers"] += 1

    flush()

    return result
