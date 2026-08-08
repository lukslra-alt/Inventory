from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from inventory.models import Product
from inventory.services.category_tree import get_category_tree
from inventory.services.google_client import download_google_sheet
from inventory.services.qb_parser import QuickBooksParser
from inventory.services.sync_engine import sync_products


def write_fixture_sheet(filepath, rows):
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"

    for row_index, values in enumerate(rows, start=1):
        for column_index, value in enumerate(values, start=1):
            sheet.cell(row=row_index, column=column_index, value=value)

    workbook.save(filepath)


def product_row(item, description, cost, qty):
    row = [None] * 11
    row[2] = item   # C
    row[4] = description  # E
    row[6] = cost   # G
    row[10] = qty   # K
    return row


class QuickBooksParserTests(TestCase):

    def test_parse_full_hierarchy(self):
        rows = [
            product_row("Tools:Power:Drills:Electric", "Power Drill", 250.50, 12),
        ]
        filepath = self.make_sheet(rows)
        products = QuickBooksParser(filepath).parse()

        self.assertEqual(len(products), 1)
        product = products[0]
        self.assertEqual(product["item"], "Tools:Power:Drills:Electric")
        self.assertEqual(product["product_name"], "Power Drill")
        self.assertEqual(product["category"], "Tools")
        self.assertEqual(product["subcategory"], "Power")
        self.assertEqual(product["level3"], "Drills")
        self.assertEqual(product["level4"], "Electric")
        self.assertEqual(product["hierarchy_path"], "Tools:Power:Drills:Electric")
        self.assertEqual(product["qty"], 12.0)
        self.assertEqual(product["cost"], 250.50)

    def test_parse_shallow_hierarchy(self):
        rows = [
            product_row("Tools", "Hammer", 10.00, 5),
        ]
        filepath = self.make_sheet(rows)
        products = QuickBooksParser(filepath).parse()

        self.assertEqual(len(products), 1)
        product = products[0]
        self.assertEqual(product["category"], "Tools")
        self.assertEqual(product["subcategory"], "")
        self.assertEqual(product["level3"], "")
        self.assertEqual(product["level4"], "")

    def test_parse_skips_header_row(self):
        rows = [
            product_row("Item", "Item Description", "Cost", "Qty"),
            product_row("Tools", "Hammer", 10.00, 5),
        ]
        filepath = self.make_sheet(rows)
        products = QuickBooksParser(filepath).parse()

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["product_name"], "Hammer")

    def test_parse_skips_rows_without_item_or_description(self):
        rows = [
            product_row("", "", 0, 0),
            product_row("Tools", "", 10.00, 5),
            product_row("", "No Item", 10.00, 5),
            product_row("Tools", "Hammer", 10.00, 5),
        ]
        filepath = self.make_sheet(rows)
        products = QuickBooksParser(filepath).parse()

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["product_name"], "Hammer")

    def test_parse_handles_currency_text_cost(self):
        rows = [
            product_row("Tools", "Hammer", "Rs. 1,250.50", 5),
        ]
        filepath = self.make_sheet(rows)
        products = QuickBooksParser(filepath).parse()

        self.assertEqual(products[0]["cost"], 1250.50)

    def test_parse_missing_cost_defaults_to_zero(self):
        rows = [
            product_row("Tools", "Hammer", None, 5),
        ]
        filepath = self.make_sheet(rows)
        products = QuickBooksParser(filepath).parse()

        self.assertEqual(products[0]["cost"], 0.0)

    def make_sheet(self, rows):
        import tempfile

        filepath = tempfile.mktemp(suffix=".xlsx")
        write_fixture_sheet(filepath, rows)
        self.addCleanup(self._remove, filepath)
        return filepath

    @staticmethod
    def _remove(filepath):
        import os

        if os.path.exists(filepath):
            os.remove(filepath)


class SyncEngineTests(TestCase):

    def _product_data(self, item, **overrides):
        data = {
            "item": item,
            "product_name": "Product",
            "category": "Tools",
            "subcategory": "",
            "level3": "",
            "level4": "",
            "hierarchy_path": item,
            "qty": "10.00",
            "cost": "5.00",
        }
        data.update(overrides)
        return data

    def test_adds_new_products(self):
        result = sync_products([
            self._product_data("Tools:A"),
            self._product_data("Tools:B"),
        ])

        self.assertEqual(result["added"], 2)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(result["restored"], 0)
        self.assertEqual(result["removed"], 0)
        self.assertEqual(result["total_products"], 2)
        self.assertEqual(Product.objects.count(), 2)
        self.assertTrue(Product.objects.filter(item="Tools:A", active=True).exists())

    def test_updates_existing_product(self):
        Product.objects.create(item="Tools:A", product_name="Old", qty=Decimal("1.00"))

        result = sync_products([
            self._product_data("Tools:A", product_name="New", qty="20.00", cost="7.50"),
        ])

        self.assertEqual(result["added"], 0)
        self.assertEqual(result["updated"], 1)
        product = Product.objects.get(item="Tools:A")
        self.assertEqual(product.product_name, "New")
        self.assertEqual(product.qty, Decimal("20.00"))
        self.assertEqual(product.cost, Decimal("7.50"))

    def test_does_not_update_unchanged_product(self):
        Product.objects.create(
            item="Tools:A",
            product_name="Product",
            category="Tools",
            hierarchy_path="Tools",
            qty=Decimal("10.00"),
            cost=Decimal("5.00"),
        )

        result = sync_products([
            self._product_data("Tools:A", hierarchy_path="Tools"),
        ])

        self.assertEqual(result["updated"], 0)

    def test_restores_inactive_product(self):
        Product.objects.create(item="Tools:A", product_name="Old", active=False)

        result = sync_products([
            self._product_data("Tools:A"),
        ])

        self.assertEqual(result["restored"], 1)
        product = Product.objects.get(item="Tools:A")
        self.assertTrue(product.active)

    def test_removes_products_missing_from_sheet(self):
        Product.objects.create(item="Tools:A", product_name="A")
        Product.objects.create(item="Tools:B", product_name="B")

        result = sync_products([
            self._product_data("Tools:A"),
        ])

        self.assertEqual(result["removed"], 1)
        self.assertTrue(Product.objects.get(item="Tools:A").active)
        self.assertFalse(Product.objects.get(item="Tools:B").active)

    def test_transaction_rolls_back_on_error(self):
        Product.objects.create(item="Tools:A", product_name="A")

        with self.assertRaises(Exception):
            with patch(
                "inventory.services.sync_engine.Product.objects.filter",
                side_effect=Exception("boom"),
            ):
                sync_products([self._product_data("Tools:B")])

        # Transaction.atomic should have rolled back the insert
        self.assertEqual(Product.objects.count(), 1)
        self.assertFalse(Product.objects.filter(item="Tools:B").exists())


class CategoryTreeTests(TestCase):

    def test_builds_nested_tree(self):
        Product.objects.create(
            item="T:P:D:E",
            product_name="Drill",
            category="Tools",
            subcategory="Power",
            level3="Drills",
            level4="Electric",
        )
        Product.objects.create(
            item="T:P:H",
            product_name="Hammer",
            category="Tools",
            subcategory="Power",
        )
        Product.objects.create(
            item="S:A",
            product_name="Saw",
            category="Stationary",
            active=False,
        )

        tree = get_category_tree()

        self.assertIn("Tools", tree)
        self.assertNotIn("Stationary", tree)

        tools = tree["Tools"]
        self.assertEqual(tools["type"], "category")
        self.assertIn("Power", tools["children"])

        power = tools["children"]["Power"]
        self.assertEqual(power["type"], "subcategory")
        self.assertIn("Drills", power["children"])
        drills = power["children"]["Drills"]
        self.assertIn("Electric", drills["children"])
        self.assertEqual(drills["children"]["Electric"]["type"], "level4")

        # Products attach under the parent node's "children" dict
        hammer = next(
            p for p in power["children"]["products"]
            if p["product_name"] == "Hammer"
        )
        self.assertEqual(hammer["id"], "T:P:H")


class GoogleClientTests(TestCase):

    @patch("inventory.services.google_client.requests.get")
    def test_download_success(self, mock_get):
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.content = b"file-bytes"

        result = download_google_sheet()

        self.assertTrue(result["success"])
        self.assertEqual(result["size"], len(b"file-bytes"))
        self.assertIn("filepath", result)

    @patch("inventory.services.google_client.requests.get")
    def test_download_failure(self, mock_get):
        import requests

        mock_get.side_effect = requests.RequestException("network down")

        result = download_google_sheet()

        self.assertFalse(result["success"])
        self.assertIn("error", result)
