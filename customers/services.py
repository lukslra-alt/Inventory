import csv
from collections import defaultdict
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
    for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _cell(row, index):
    if index < len(row):
        return row[index]
    return ""


def _clean_ref(value):
    """Return a bill reference without the Tally asterisk marker."""
    return (value or "").strip().lstrip("*").strip()


def _is_receivables_export(rows):
    """
    Detect the Tally-style Bills Receivable layout.

    Such files carry a header row like:
        Account, Dated, Type, Ref. No., Ref. Amt., Pending Amt., ...
    """
    for row in rows:
        if len(row) < 6:
            continue
        cells = [(cell or "").strip().lower() for cell in row[:6]]
        if (
            cells[0] == "account"
            and cells[3] == "ref. no."
            and cells[5].startswith("pending")
        ):
            return True
    return False


@transaction.atomic
def import_customer_csv(filepath):
    """
    Import a customer/bill export and upsert Customer, Invoice and
    InvoiceItem records.

    Two layouts are supported and detected automatically:

    1. QuickBooks customer export, with customer blocks and item lines.
    2. Tally-style Bills Receivable export, with one row per bill:
           Account,Dated,Type,Ref. No.,Ref. Amt.,Pending Amt.,...
       These files have no item detail, so each bill is stored with a
       single summary line.

    The file is treated as the full source of truth: customers and
    invoices not present in it are removed.
    """
    result = {
        "customers": 0,
        "invoices": 0,
        "items": 0,
        "deleted": 0,
        "deleted_invoices": 0,
    }

    with open(filepath, newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))

    if _is_receivables_export(rows):
        _import_receivables_rows(rows, result)
    else:
        _import_quickbooks_rows(rows, result)

    return result


def _import_quickbooks_rows(rows, result):
    """Import a QuickBooks customer export (customer blocks + items)."""
    current_customer = None
    # Names of every customer block seen in the file. Used at the end to
    # delete customers that no longer exist in the export.
    seen_names = set()
    # Buffer invoices per customer block; flushed when the next customer
    # name appears or at EOF. invoice_number -> {customer, date, rows}.
    pending_invoices = {}

    def flush():
        """Commit all buffered invoices for the current customer block."""
        nonlocal pending_invoices
        if current_customer is None:
            pending_invoices = {}
            return

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
                # Full replace: drop stale line items before re-importing.
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

                # Each line carries its own open-balance cell; sum them
                # because QuickBooks does not provide a single total.
                invoice_balance += open_balance

                result["items"] += 1

            invoice.total = invoice_total
            invoice.balance = invoice_balance
            invoice.save()

        # QuickBooks only lists open items, so an invoice drops out of the
        # export as soon as it is settled. Without this sweep those paid
        # invoices stay in the database forever and keep inflating the
        # customer's outstanding balance. Anything in the export's block
        # for this customer is authoritative; everything else is stale.
        stale = Invoice.objects.filter(customer=current_customer).exclude(
            invoice_number__in=pending_invoices
        )
        result["deleted_invoices"] += stale.count()
        stale.delete()

        pending_invoices = {}

    for row in rows:
        if not row:
            continue

        first = (row[0] or "").strip()

        # ---------------------------------------------------------
        # Invoice row
        # ---------------------------------------------------------
        if not first:
            # Invoice rows have a blank col A and "Invoice" in col B.
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
            # "Total <name>" row carries customer-level qty/amount/balance
            # from the QuickBooks export (cols 5, 6, 8).
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

        seen_names.add(first)

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

    # Remove customers absent from the export (cascades to their invoices
    # and line items via the model's on_delete rules).
    deleted_counts = Customer.objects.exclude(
        name__in=seen_names
    ).delete()
    result["deleted"] = deleted_counts[1].get("customers.Customer", 0)


def _import_receivables_rows(rows, result):
    """
    Import a Tally-style Bills Receivable export.

    Each data row is one open bill:
        0 = Account, 1 = Dated, 2 = Type, 3 = Ref. No.,
        4 = Ref. Amt., 5 = Pending Amt.
    """
    seen_names = set()
    customer_totals = defaultdict(
        lambda: {"total": Decimal("0.00"), "balance": Decimal("0.00")}
    )
    customer_invoices = defaultdict(set)

    for row in rows:
        account = _cell(row, 0).strip()

        # Skip blank rows, the column heading row and the report footer.
        if not account or account.lower() == "account":
            continue

        ref = _clean_ref(_cell(row, 3))
        if not ref:
            continue

        bill_type = _cell(row, 2).strip() or "Bill"
        bill_date = _parse_date(_cell(row, 1))
        total = _to_decimal(_cell(row, 4))
        balance = _to_decimal(_cell(row, 5))

        customer, created = Customer.objects.get_or_create(name=account)
        if created:
            result["customers"] += 1

        seen_names.add(account)
        customer_invoices[account].add(ref)
        customer_totals[account]["total"] += total
        customer_totals[account]["balance"] += balance

        invoice, created = Invoice.objects.update_or_create(
            invoice_number=ref,
            defaults={
                "customer": customer,
                "date": bill_date,
                "total": total,
                "balance": balance,
            },
        )
        if created:
            result["invoices"] += 1
        else:
            invoice.items.all().delete()

        # The receivables report carries no item detail. Keep one summary
        # line so invoice quantities and totals stay consistent.
        InvoiceItem.objects.create(
            invoice=invoice,
            item=f"Bill {ref} - {bill_type}",
            qty=Decimal("1.00"),
            sales_price=total,
            amount=total,
        )
        result["items"] += 1

    # Rewrite each customer's aggregate totals from this snapshot.
    for name, totals in customer_totals.items():
        customer = Customer.objects.get(name=name)
        customer.total_qty = Decimal("0.00")
        customer.total_amount = totals["total"]
        customer.balance = totals["balance"]
        customer.save()

    # Anything not listed for a customer is settled/invalid and is removed.
    for name, refs in customer_invoices.items():
        stale = Invoice.objects.filter(customer__name=name).exclude(
            invoice_number__in=refs
        )
        result["deleted_invoices"] += stale.count()
        stale.delete()

    # Remove customers absent from the snapshot (cascades to their invoices).
    deleted_counts = Customer.objects.exclude(
        name__in=seen_names
    ).delete()
    result["deleted"] = deleted_counts[1].get("customers.Customer", 0)
