import tempfile
import os
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from customers.models import (
    Customer,
    Invoice,
    InvoiceItem,
    extract_description,
)
from customers.services import import_customer_csv


def write_csv(rows, filepath):
    import csv

    with open(filepath, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        for row in rows:
            writer.writerow(row)


class ImportCustomerCsvTests(TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def make_csv(self, rows):
        filepath = os.path.join(self.tmpdir, "customers.csv")
        write_csv(rows, filepath)
        return filepath

    def test_imports_customers_invoices_and_items(self):
        rows = [
            ["", "Type", "Date", "Num", "Item", "Qty", "Sales Price", "Amount", "Balance"],
            ["Aaliya Rice Mill - Galewela", "", "", "", "", "", "", "", ""],
            ["", "Invoice", "7/7/2026", "E12487", "POLISHER:PARTS", 3, 2600, 7800, 7800],
            ["", "Invoice", "7/10/2026", "E12504", "V BELT:B:B 106", 10, 2120, 21200, 29000],
            ["", "Invoice", "7/10/2026", "E12504", "V BELT:B:B 67", 3, 1340, 4020, 33020],
            ["Total Aaliya Rice Mill - Galewela", "", "", "", "", 16, "", 33020, 33020],
            ["TOTAL", "", "", "", "", 16, "", 33020, 33020],
        ]
        result = import_customer_csv(self.make_csv(rows))

        self.assertEqual(result["customers"], 1)
        self.assertEqual(result["invoices"], 2)
        self.assertEqual(result["items"], 3)

        customer = Customer.objects.get(name="Aaliya Rice Mill - Galewela")
        self.assertEqual(customer.total_amount, Decimal("33020.00"))
        self.assertEqual(customer.total_qty, Decimal("16.00"))

        # Multi-line invoice keeps all items and accumulates the total.
        invoice = Invoice.objects.get(invoice_number="E12504")
        self.assertEqual(invoice.items.count(), 2)
        self.assertEqual(invoice.total, Decimal("25220.00"))
        self.assertEqual(invoice.balance, Decimal("33020.00"))

    def test_reimport_is_idempotent(self):
        rows = [
            ["Acme", "", "", "", "", "", "", "", ""],
            ["", "Invoice", "1/1/2026", "I001", "ITEM A", 2, 100, 200, 200],
            ["Total Acme", "", "", "", "", 2, "", 200, 200],
        ]
        filepath = self.make_csv(rows)

        import_customer_csv(filepath)
        result = import_customer_csv(filepath)

        self.assertEqual(result["invoices"], 0)
        self.assertEqual(result["items"], 1)
        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(InvoiceItem.objects.count(), 1)
        self.assertEqual(
            Invoice.objects.get(invoice_number="I001").total,
            Decimal("200.00"),
        )


class ExtractDescriptionTests(TestCase):

    def test_extracts_description_from_parentheses(self):
        self.assertEqual(
            extract_description(
                "V BELT:B:B 106 V BELT - SANLUX (B 106 V BELT - SANLUX)"
            ),
            "B 106 V BELT - SANLUX",
        )

    def test_handles_nested_parentheses(self):
        self.assertEqual(
            extract_description(
                "BAG CLOSER:REVO PARTS:NEEDLE (SINGLE) - REVO PARTS "
                "(NEEDLE (SINGLE) - REVO PARTS)"
            ),
            "NEEDLE (SINGLE) - REVO PARTS",
        )

    def test_falls_back_to_leaf_segment(self):
        self.assertEqual(
            extract_description("MOTORS:WACCO MOTOR:10HP 3P 4POLE"),
            "10HP 3P 4POLE",
        )

    def test_truncated_item(self):
        self.assertEqual(
            extract_description(
                "HULLER:10' QILI HULLER SPARES:RUBBER ROLLER - LVR "
                "(10' RUBBER ROLLE..."
            ),
            "10' RUBBER ROLLE...",
        )


class CustomerViewTests(TestCase):

    def setUp(self):
        from django.contrib.auth.models import User

        self.user = User.objects.create_user(username="tester", password="pass")
        self.client.login(username="tester", password="pass")

        self.customer = Customer.objects.create(name="Acme")
        self.invoice = Invoice.objects.create(
            invoice_number="I001",
            customer=self.customer,
            total=Decimal("200.00"),
            balance=Decimal("200.00"),
        )
        InvoiceItem.objects.create(
            invoice=self.invoice,
            item="ITEM A",
            qty=Decimal("2"),
            sales_price=Decimal("100"),
            amount=Decimal("200"),
        )

    def test_customer_list(self):
        response = self.client.get(reverse("customer_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Acme")

    def test_customer_detail(self):
        response = self.client.get(
            reverse("customer_detail", args=[self.customer.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "I001")

    def test_invoice_view(self):
        response = self.client.get(reverse("invoice_view", args=["I001"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ITEM A")
        self.assertContains(response, "200.00")

    def test_invoice_view_shows_description_not_item(self):
        self.invoice.items.all().update(
            item="V BELT:B:B 106 V BELT - SANLUX (B 106 V BELT - SANLUX)"
        )
        response = self.client.get(reverse("invoice_view", args=["I001"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "B 106 V BELT - SANLUX")
        self.assertNotContains(response, "V BELT:B:B 106 V BELT")

    def test_invoice_pdf(self):
        response = self.client.get(reverse("invoice_pdf", args=["I001"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))


class SyncCustomersCommandTests(TestCase):

    @patch("customers.management.commands.sync_customers.download_customer_csv")
    @patch("customers.management.commands.sync_customers.import_customer_csv")
    def test_imports_when_hash_changed(
        self,
        mock_import,
        mock_download,
    ):
        from django.core.management import call_command

        from inventory.models import SyncHistory, SyncSetting

        mock_download.return_value = {
            "success": True,
            "filepath": r"C:\fake\customers.csv",
            "hash": "abc123" + "0" * 58,
            "size": 100,
        }
        mock_import.return_value = {
            "customers": 2,
            "invoices": 5,
            "items": 20,
        }

        call_command("sync_customers")

        mock_import.assert_called_once_with(r"C:\fake\customers.csv")
        setting = SyncSetting.objects.get()
        self.assertEqual(setting.customer_hash, "abc123" + "0" * 58)
        self.assertEqual(
            SyncHistory.objects.filter(status="SUCCESS").count(),
            1,
        )

    @patch("customers.management.commands.sync_customers.download_customer_csv")
    @patch("customers.management.commands.sync_customers.import_customer_csv")
    def test_skips_when_hash_unchanged(
        self,
        mock_import,
        mock_download,
    ):
        from django.core.management import call_command

        from inventory.models import SyncHistory, SyncSetting

        file_hash = "abc123" + "0" * 58

        SyncSetting.objects.create(customer_hash=file_hash)

        mock_download.return_value = {
            "success": True,
            "filepath": r"C:\fake\customers.csv",
            "hash": file_hash,
            "size": 100,
        }

        call_command("sync_customers")

        mock_import.assert_not_called()
        self.assertEqual(
            SyncHistory.objects.filter(status="SKIPPED").count(),
            1,
        )
