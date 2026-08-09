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
    except InvalidOperation:
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
        ,Invoice,<date>,<num>,<item>,<qty>,<price>,<amount>,<balance>
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
                    "balance": data["balance"],
                },
            )
            if created:
                result["invoices"] += 1
            else:
                invoice.items.all().delete()

            total = Decimal("0.00")
            for row in data["rows"]:
                amount = _to_decimal(_cell(row, 7))
                InvoiceItem.objects.create(
                    invoice=invoice,
                    item=_cell(row, 4).strip(),
                    qty=_to_decimal(_cell(row, 5)),
                    sales_price=_to_decimal(_cell(row, 6)),
                    amount=amount,
                )
                result["items"] += 1
                total += amount

            invoice.total = total
            invoice.save()
        pending_invoices = {}

    for row in rows:
        if not row:
            continue

        first = (row[0] or "").strip()

        if not first:
            # Blank line or header — check for an invoice line.
            if len(row) > 1 and row[1] and row[1].strip() == "Invoice":
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
                        "balance": Decimal("0.00"),
                        "rows": [],
                    }
                    pending_invoices[invoice_number] = data
                # Balance is a running customer balance; keep the latest row.
                data["balance"] = _to_decimal(_cell(row, 8))
                data["rows"].append(row)
            continue

        if first == "TOTAL":
            continue

        if first.startswith("Total"):
            # Update running totals on the customer.
            if current_customer is not None:
                current_customer.total_qty = _to_decimal(_cell(row, 5))
                current_customer.total_amount = _to_decimal(_cell(row, 7))
                current_customer.balance = _to_decimal(_cell(row, 8))
                current_customer.save()
            continue

        if first.lower() == "type":
            continue

        # A customer block header row — flush prior invoice lines first.
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
