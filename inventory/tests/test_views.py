import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from inventory.models import Product


class DashboardViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.nonstaff = User.objects.create_user(
            username="viewer", password="pass"
        )
        self.product = Product.objects.create(
            item="Tools:Power",
            product_name="Drill",
            category="Tools",
            subcategory="Power",
            qty=Decimal("10.00"),
            sales_price=Decimal("100.00"),
            cost=Decimal("50.00"),
        )

    def test_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_renders_for_authenticated_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Drill")

    def test_search_filters_products(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard"), {"search": "Hammer"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"]), 0)

    def test_category_filter(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard"), {"category": "Garden"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"]), 0)

    def test_pagination_page_size(self):
        self.client.force_login(self.user)
        for i in range(55):
            Product.objects.create(
                item=f"Tools:B{i}",
                product_name=f"Product {i}",
            )
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"]), 50)

    def test_nonstaff_sees_no_cost(self):
        self.client.force_login(self.nonstaff)
        response = self.client.get(reverse("dashboard"))
        self.assertFalse(response.context["show_cost"])
        self.assertFalse(response.context["is_admin"])

    def test_staff_sees_cost(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard"))
        self.assertTrue(response.context["show_cost"])
        self.assertTrue(response.context["is_admin"])


class SearchProductsViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.product = Product.objects.create(
            item="Tools:Power",
            product_name="Drill",
            category="Tools",
            qty=Decimal("3.00"),
            reorder_qty=Decimal("5.00"),
            sales_price=Decimal("100.00"),
            cost=Decimal("50.00"),
        )

    def test_requires_login(self):
        response = self.client.get(reverse("search_products"))
        self.assertEqual(response.status_code, 302)

    def test_returns_json_products(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("search_products"))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data["products"]), 1)
        product = data["products"][0]
        self.assertEqual(product["id"], "Tools:Power")
        self.assertEqual(product["name"], "Drill")
        self.assertEqual(product["qty"], "3.00")
        self.assertEqual(product["price"], "100.00")
        self.assertEqual(product["cost"], "50.00")
        self.assertEqual(product["status"], "LOW")

    def test_filters_by_q_parameter(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("search_products"), {"q": "Hammer"}
        )
        data = json.loads(response.content)
        self.assertEqual(len(data["products"]), 0)

    def test_filters_by_category(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("search_products"), {"category": "Garden"}
        )
        data = json.loads(response.content)
        self.assertEqual(len(data["products"]), 0)

    def test_limits_results_to_50(self):
        self.client.force_login(self.user)
        for i in range(60):
            Product.objects.create(
                item=f"Tools:B{i}",
                product_name=f"Product {i}",
            )
        response = self.client.get(reverse("search_products"))
        data = json.loads(response.content)
        self.assertEqual(len(data["products"]), 50)


class ProductEditViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.nonstaff = User.objects.create_user(
            username="viewer", password="pass"
        )
        self.product = Product.objects.create(
            item="Tools:Power",
            product_name="Drill",
            qty=Decimal("10.00"),
            reorder_qty=Decimal("5.00"),
        )

    def test_requires_staff(self):
        self.client.force_login(self.nonstaff)
        response = self.client.get(
            reverse("product_edit", args=[self.product.item])
        )
        self.assertEqual(response.status_code, 302)

    def test_get_renders_form(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("product_edit", args=[self.product.item])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Drill")

    def test_post_updates_product(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("product_edit", args=[self.product.item]),
            {"sales_price": "120.00", "reorder_qty": "8.00"},
        )
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.sales_price, Decimal("120.00"))
        self.assertEqual(self.product.reorder_qty, Decimal("8.00"))

    def test_post_invalid_form_rerenders(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("product_edit", args=[self.product.item]),
            {"sales_price": "-5", "reorder_qty": "5"},
        )
        self.assertEqual(response.status_code, 200)


class OfflineProductsViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.product = Product.objects.create(
            item="Tools:Power",
            product_name="Drill",
            category="Tools",
            sales_price=Decimal("100.00"),
        )

    def test_requires_staff(self):
        response = self.client.get(reverse("offline_products"))
        self.assertEqual(response.status_code, 302)

    def test_returns_item_keyed_products(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("offline_products"))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data), 1)
        self.assertIn("item", data[0])
        self.assertNotIn("id", data[0])
        self.assertEqual(data[0]["item"], "Tools:Power")


class ManualSyncViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.nonstaff = User.objects.create_user(
            username="viewer", password="pass"
        )

    def test_requires_staff(self):
        self.client.force_login(self.nonstaff)
        response = self.client.get(reverse("manual_sync"))
        self.assertEqual(response.status_code, 302)

    @patch("inventory.views.call_command")
    def test_success_redirects_with_message(self, mock_call):
        self.client.force_login(self.user)
        response = self.client.get(reverse("manual_sync"))
        mock_call.assert_called_once_with("sync_inventory")
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("dashboard"))

    @patch("inventory.views.call_command", side_effect=Exception("boom"))
    def test_failure_redirects_with_error_message(self, mock_call):
        self.client.force_login(self.user)
        response = self.client.get(reverse("manual_sync"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("dashboard"))
