from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from inventory.models import Product
from pricelist.models import PricePage, PriceListItem, PriceListHeading
from usermanage.models import UserProfile


class PricePageModelTests(TestCase):

    def setUp(self):
        self.page = PricePage.objects.create(name="N70 Polisher", slug="0")

    def test_str(self):
        self.assertEqual(str(self.page), "N70 Polisher")

    def test_ordering_by_display_order(self):
        first = PricePage.objects.create(name="First", slug="a", display_order=2)
        second = PricePage.objects.create(name="Second", slug="b", display_order=1)
        names = list(PricePage.objects.values_list("name", flat=True))
        # setUp page has display_order 0 and sorts first
        self.assertEqual(names, [self.page.name, second.name, first.name])


class PriceListItemModelTests(TestCase):

    def setUp(self):
        self.page = PricePage.objects.create(name="Page", slug="p")
        self.product = Product.objects.create(item="A:B", product_name="Hammer")
        self.item = PriceListItem.objects.create(page=self.page, product=self.product)

    def test_str_returns_product_name(self):
        self.assertEqual(str(self.item), "Hammer")

    def test_item_visible_by_default(self):
        self.assertTrue(self.item.visible)


class PriceCategoryViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="user", password="pass")
        self.page = PricePage.objects.create(name="Page", slug="p")
        UserProfile.objects.update_or_create(
            user=self.user, defaults={"can_access_pricelist": True}
        )

    def test_requires_login(self):
        response = self.client.get(reverse("price_categories"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_user_without_access_is_redirected(self):
        blocked = User.objects.create_user(username="blocked", password="pass")
        self.client.force_login(blocked)
        response = self.client.get(reverse("price_categories"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("customer_list"))

    def test_lists_pages_for_logged_in_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("price_categories"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page")

    def test_staff_sees_manage_link(self):
        staff = User.objects.create_user(username="staff", password="pass", is_staff=True)
        self.client.force_login(staff)
        response = self.client.get(reverse("price_categories"))
        self.assertContains(response, "PRICE LIST MANAGEMENT")


class PricePageViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="user", password="pass")
        UserProfile.objects.update_or_create(
            user=self.user, defaults={"can_access_pricelist": True}
        )
        self.product = Product.objects.create(
            item="A:B",
            product_name="Hammer",
            sales_price=123.45,
        )
        self.page = PricePage.objects.create(name="Page", slug="p")
        PriceListItem.objects.create(page=self.page, product=self.product)

    def test_requires_login(self):
        response = self.client.get(
            reverse("price_page", args=["p"])
        )
        self.assertEqual(response.status_code, 302)

    def test_user_without_access_is_redirected(self):
        blocked = User.objects.create_user(username="blocked", password="pass")
        self.client.force_login(blocked)
        response = self.client.get(
            reverse("price_page", args=["p"])
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("customer_list"))

    def test_shows_page_name_and_products(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("price_page", args=["p"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hammer")
        self.assertContains(response, "123.45")

    def test_hidden_items_not_shown(self):
        other = Product.objects.create(item="C:D", product_name="Saw")
        PriceListItem.objects.create(
            page=self.page, product=other, visible=False
        )
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("price_page", args=["p"])
        )
        self.assertNotContains(response, "Saw")

    def test_missing_page_is_404(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("price_page", args=["missing"])
        )
        self.assertEqual(response.status_code, 404)


class AddProductsViewTests(TestCase):

    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.user = User.objects.create_user(username="user", password="pass")
        self.page = PricePage.objects.create(name="Page", slug="p")
        self.product = Product.objects.create(item="A:B", product_name="Hammer")

    def test_requires_staff(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("add_products", args=[self.page.id])
        )
        self.assertEqual(response.status_code, 302)

    def test_search_filters_products(self):
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse("add_products", args=[self.page.id]),
            {"search": "Saw"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Hammer")

    def test_added_items_context_marks_existing_products(self):
        self.client.force_login(self.staff)
        PriceListItem.objects.create(page=self.page, product=self.product)
        response = self.client.get(
            reverse("add_products", args=[self.page.id]),
            {"search": "Hammer"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.product.item, response.context["added_items"])

    def test_search_results_are_pre_checked(self):
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse("add_products", args=[self.page.id]),
            {"search": "Hammer"},
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(f'value="{self.product.item}"', content)
        self.assertIn("checked", content)

    def test_post_creates_price_list_items(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("add_products", args=[self.page.id]),
            {"products": [self.product.item]},
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("price_manage"))
        self.assertTrue(
            PriceListItem.objects.filter(
                page=self.page, product=self.product
            ).exists()
        )

    def test_post_ignores_duplicate_items(self):
        self.client.force_login(self.staff)
        PriceListItem.objects.create(page=self.page, product=self.product)
        response = self.client.post(
            reverse("add_products", args=[self.page.id]),
            {"products": [self.product.item]},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PriceListItem.objects.filter(page=self.page).count(), 1)


class PriceManageViewTests(TestCase):

    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.user = User.objects.create_user(username="user", password="pass")
        self.page = PricePage.objects.create(name="Page", slug="p")

    def test_requires_staff(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("price_manage"))
        self.assertEqual(response.status_code, 302)

    def test_lists_pages_for_staff(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("price_manage"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page")


class AddCategoryViewTests(TestCase):

    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.user = User.objects.create_user(username="user", password="pass")

    def test_requires_staff(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("add_category"))
        self.assertEqual(response.status_code, 302)

    def test_get_renders_form_for_staff(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("add_category"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Category Name")

    def test_post_creates_category(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("add_category"),
            {"name": "New Category", "slug": "new-category"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("price_manage"))
        self.assertTrue(
            PricePage.objects.filter(name="New Category").exists()
        )

    def test_post_auto_generates_slug(self):
        self.client.force_login(self.staff)
        self.client.post(
            reverse("add_category"),
            {"name": "My Great Category", "slug": ""},
        )
        page = PricePage.objects.get(name="My Great Category")
        self.assertEqual(page.slug, "my-great-category")


class PriceListHeadingModelTests(TestCase):

    def setUp(self):
        self.page = PricePage.objects.create(name="Page", slug="p")

    def test_str_returns_text(self):
        heading = PriceListHeading.objects.create(
            page=self.page, text="Spare Parts"
        )
        self.assertEqual(str(heading), "Spare Parts")

    def test_ordering_by_display_order(self):
        first = PriceListHeading.objects.create(
            page=self.page, text="First", display_order=2
        )
        second = PriceListHeading.objects.create(
            page=self.page, text="Second", display_order=1
        )
        texts = list(
            self.page.headings.values_list("text", flat=True)
        )
        self.assertEqual(texts, [second.text, first.text])


class AddHeadingViewTests(TestCase):

    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.user = User.objects.create_user(username="user", password="pass")
        self.page = PricePage.objects.create(name="Page", slug="p")

    def test_requires_staff(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("add_heading", args=[self.page.id])
        )
        self.assertEqual(response.status_code, 302)

    def test_get_renders_form_for_staff(self):
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse("add_heading", args=[self.page.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Heading")

    def test_post_creates_heading_and_redirects(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("add_heading", args=[self.page.id]),
            {"text": "Spare Parts", "display_order": "1"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("price_manage"))
        self.assertTrue(
            PriceListHeading.objects.filter(
                page=self.page, text="Spare Parts"
            ).exists()
        )


class EditPageViewTests(TestCase):

    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.user = User.objects.create_user(username="user", password="pass")
        self.page = PricePage.objects.create(name="Page", slug="p")
        self.product = Product.objects.create(
            item="A:B", product_name="Hammer"
        )

    def test_requires_staff(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("edit_page", args=[self.page.id])
        )
        self.assertEqual(response.status_code, 302)

    def test_get_renders_entries_and_search_results(self):
        self.client.force_login(self.staff)
        PriceListItem.objects.create(page=self.page, product=self.product)
        PriceListHeading.objects.create(
            page=self.page, text="Parts", display_order=1
        )
        response = self.client.get(
            reverse("edit_page", args=[self.page.id]),
            {"search": "Hammer"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hammer")
        self.assertContains(response, "Parts")

    def test_added_ids_context_marks_existing_products(self):
        self.client.force_login(self.staff)
        PriceListItem.objects.create(page=self.page, product=self.product)
        response = self.client.get(
            reverse("edit_page", args=[self.page.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.product.item, response.context["added_ids"])

    def test_post_adds_products_and_redirects(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("edit_page", args=[self.page.id]),
            {"products": [self.product.item]},
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response, reverse("edit_page", args=[self.page.id])
        )
        self.assertTrue(
            PriceListItem.objects.filter(
                page=self.page, product=self.product
            ).exists()
        )

    def test_post_ignores_missing_products(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("edit_page", args=[self.page.id]),
            {"products": ["does:not:exist"]},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PriceListItem.objects.filter(page=self.page).count(), 0)


class ReorderPageViewTests(TestCase):

    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.page = PricePage.objects.create(name="Page", slug="p")
        self.product = Product.objects.create(item="A:B", product_name="Hammer")
        self.item = PriceListItem.objects.create(page=self.page, product=self.product)
        self.heading = PriceListHeading.objects.create(
            page=self.page, text="Parts", display_order=0
        )

    def test_requires_staff(self):
        response = self.client.post(
            reverse("reorder_page", args=[self.page.id]),
            {"order": []},
        )
        self.assertEqual(response.status_code, 302)

    def test_updates_display_order_for_products_and_headings(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("reorder_page", args=[self.page.id]),
            {"order": [
                f"product:{self.item.id}",
                f"heading:{self.heading.id}",
            ]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"ok": True})
        self.item.refresh_from_db()
        self.heading.refresh_from_db()
        self.assertEqual(self.item.display_order, 1)
        self.assertEqual(self.heading.display_order, 2)


class ToggleItemViewTests(TestCase):

    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.page = PricePage.objects.create(name="Page", slug="p")
        self.product = Product.objects.create(item="A:B", product_name="Hammer")
        self.item = PriceListItem.objects.create(page=self.page, product=self.product)

    def test_toggles_visibility(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("toggle_item", args=[self.page.id]),
            {"type": "product", "id": self.item.id, "visible": "false"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"ok": True})
        self.item.refresh_from_db()
        self.assertFalse(self.item.visible)


class RemoveItemViewTests(TestCase):

    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.page = PricePage.objects.create(name="Page", slug="p")
        self.product = Product.objects.create(item="A:B", product_name="Hammer")

    def test_removes_product_item(self):
        self.client.force_login(self.staff)
        item = PriceListItem.objects.create(page=self.page, product=self.product)
        response = self.client.post(
            reverse("remove_item", args=[self.page.id]),
            {"type": "product", "id": item.id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"ok": True})
        self.assertFalse(
            PriceListItem.objects.filter(pk=item.pk).exists()
        )

    def test_removes_heading(self):
        self.client.force_login(self.staff)
        heading = PriceListHeading.objects.create(page=self.page, text="Parts")
        response = self.client.post(
            reverse("remove_item", args=[self.page.id]),
            {"type": "heading", "id": heading.id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"ok": True})
        self.assertFalse(
            PriceListHeading.objects.filter(pk=heading.pk).exists()
        )


class RenameCategoryViewTests(TestCase):

    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.page = PricePage.objects.create(name="Page", slug="p")

    def test_renames_category(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("rename_category"),
            {"id": self.page.id, "name": "Renamed Page"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"ok": True})
        self.page.refresh_from_db()
        self.assertEqual(self.page.name, "Renamed Page")

    def test_blank_name_returns_error(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("rename_category"),
            {"id": self.page.id, "name": "   "},
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content, {"ok": False, "error": "Category name is required"}
        )


class ReorderCategoriesViewTests(TestCase):

    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.first = PricePage.objects.create(name="First", slug="a")
        self.second = PricePage.objects.create(name="Second", slug="b")

    def test_reorders_categories(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("reorder_categories"),
            {"order": [self.second.id, self.first.id]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"ok": True})
        self.first.refresh_from_db()
        self.second.refresh_from_db()
        self.assertEqual(self.second.display_order, 1)
        self.assertEqual(self.first.display_order, 2)


class PricePagePdfTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="user", password="pass")
        self.product = Product.objects.create(
            item="A:B",
            product_name="Hammer",
            sales_price=Decimal("123.45"),
        )
        self.page = PricePage.objects.create(name="Page", slug="p")
        PriceListItem.objects.create(page=self.page, product=self.product)

    def test_requires_pricelist_access(self):
        response = self.client.get(reverse("price_page_pdf", args=["p"]))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_generates_pdf_for_user_with_access(self):
        UserProfile.objects.update_or_create(
            user=self.user, defaults={"can_access_pricelist": True}
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("price_page_pdf", args=["p"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_cols_parameter_is_clamped(self):
        UserProfile.objects.update_or_create(
            user=self.user, defaults={"can_access_pricelist": True}
        )
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("price_page_pdf", args=["p"]), {"cols": "99"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"%PDF"))
