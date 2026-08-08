from decimal import Decimal

from django.test import TestCase

from inventory.models import Product


class ProductHierarchyPathTests(TestCase):

    def test_full_hierarchy_path(self):
        product = Product(
            item="Tools:Power:Drills:Electric",
            product_name="Drill",
            category="Tools",
            subcategory="Power",
            level3="Drills",
            level4="Electric",
        )
        product.build_hierarchy_path()
        self.assertEqual(
            product.hierarchy_path,
            "Tools > Power > Drills > Electric",
        )

    def test_partial_hierarchy_path(self):
        product = Product(
            item="Tools:Power",
            product_name="Drill",
            category="Tools",
            subcategory="Power",
        )
        product.build_hierarchy_path()
        self.assertEqual(product.hierarchy_path, "Tools > Power")

    def test_empty_hierarchy_path(self):
        product = Product(item="Tools:Power", product_name="Drill")
        product.build_hierarchy_path()
        self.assertEqual(product.hierarchy_path, "")

    def test_whitespace_only_levels_are_skipped(self):
        product = Product(
            item="Tools",
            product_name="Drill",
            category="Tools",
            subcategory="  ",
        )
        product.build_hierarchy_path()
        self.assertEqual(product.hierarchy_path, "Tools")


class ProductStatusTests(TestCase):

    def test_qty_zero_is_nil(self):
        product = Product(
            item="X:Y",
            product_name="Item",
            qty=Decimal("0.00"),
            reorder_qty=Decimal("5.00"),
        )
        product.calculate_status()
        self.assertEqual(product.status, "NIL")

    def test_qty_below_reorder_is_low(self):
        product = Product(
            item="X:Y",
            product_name="Item",
            qty=Decimal("3.00"),
            reorder_qty=Decimal("5.00"),
        )
        product.calculate_status()
        self.assertEqual(product.status, "LOW")

    def test_qty_above_reorder_is_ok(self):
        product = Product(
            item="X:Y",
            product_name="Item",
            qty=Decimal("9.00"),
            reorder_qty=Decimal("5.00"),
        )
        product.calculate_status()
        self.assertEqual(product.status, "OK")

    def test_qty_equal_to_reorder_is_ok(self):
        product = Product(
            item="X:Y",
            product_name="Item",
            qty=Decimal("5.00"),
            reorder_qty=Decimal("5.00"),
        )
        product.calculate_status()
        self.assertEqual(product.status, "OK")


class ProductSaveTests(TestCase):

    def test_save_builds_hierarchy_and_status(self):
        product = Product.objects.create(
            item="Tools:Power",
            product_name="Drill",
            category="Tools",
            subcategory="Power",
            qty=Decimal("2.00"),
            reorder_qty=Decimal("10.00"),
        )
        product.refresh_from_db()
        self.assertEqual(product.hierarchy_path, "Tools > Power")
        self.assertEqual(product.status, "LOW")

    def test_str_returns_product_name(self):
        product = Product(item="A:B", product_name="Hammer")
        self.assertEqual(str(product), "Hammer")


class ProductMetaTests(TestCase):

    def test_ordering(self):
        Product.objects.create(item="B", product_name="Beta")
        Product.objects.create(item="A", product_name="Alpha")
        names = list(
            Product.objects.values_list("product_name", flat=True)
        )
        self.assertEqual(names, ["Alpha", "Beta"])
