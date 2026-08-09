from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class UserManageViewTests(TestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin", password="pass", is_staff=True, is_superuser=True
        )
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.regular = User.objects.create_user(
            username="user", password="pass"
        )

    def test_user_list_requires_admin(self):
        response = self.client.get(reverse("usermanage:user_list"))
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.regular)
        response = self.client.get(reverse("usermanage:user_list"))
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.staff)
        response = self.client.get(reverse("usermanage:user_list"))
        self.assertEqual(response.status_code, 302)

    def test_user_list_shows_users(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("usermanage:user_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "admin")
        self.assertContains(response, "user")

    def test_add_staff_user(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("usermanage:user_add"),
            {
                "username": "newstaff",
                "password": "StrongPass123!",
                "first_name": "New",
                "last_name": "Staff",
                "email": "staff@example.com",
                "role": "staff",
            },
        )
        self.assertRedirects(response, reverse("usermanage:user_list"))
        user = User.objects.get(username="newstaff")
        self.assertTrue(user.check_password("StrongPass123!"))
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_add_customer_user(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("usermanage:user_add"),
            {
                "username": "customer",
                "password": "StrongPass123!",
                "role": "customer",
            },
        )
        self.assertRedirects(response, reverse("usermanage:user_list"))
        user = User.objects.get(username="customer")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_edit_user(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("usermanage:user_edit", args=[self.regular.pk]),
            {
                "username": "user",
                "first_name": "Renamed",
                "last_name": "",
                "email": "",
                "role": "staff",
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("usermanage:user_list"))
        self.regular.refresh_from_db()
        self.assertEqual(self.regular.first_name, "Renamed")
        self.assertTrue(self.regular.is_staff)

    def test_reset_password(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("usermanage:user_reset_password", args=[self.regular.pk]),
            {"password": "NewStrongPass123!"},
        )
        self.assertRedirects(response, reverse("usermanage:user_list"))
        self.regular.refresh_from_db()
        self.assertTrue(self.regular.check_password("NewStrongPass123!"))

    def test_delete_user(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("usermanage:user_delete", args=[self.regular.pk])
        )
        self.assertRedirects(response, reverse("usermanage:user_list"))
        self.assertFalse(
            User.objects.filter(pk=self.regular.pk).exists()
        )

    def test_cannot_delete_self(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("usermanage:user_delete", args=[self.admin.pk])
        )
        self.assertRedirects(response, reverse("usermanage:user_list"))
        self.assertTrue(
            User.objects.filter(pk=self.admin.pk).exists()
        )
