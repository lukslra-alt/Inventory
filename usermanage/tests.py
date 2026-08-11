from django.contrib.auth.models import AnonymousUser, User
from django.test import TestCase
from django.urls import reverse

from usermanage.models import UserProfile
from usermanage.roles import (
    can_access_pricelist,
    is_admin,
    is_staff,
    role_of,
    role_to_flags,
)
from usermanage.forms import UserCreateForm, UserEditForm


class UserProfileModelTests(TestCase):

    def test_profile_auto_created_on_user_create(self):
        user = User.objects.create_user(username="user", password="pass")
        profile = UserProfile.objects.filter(user=user).first()
        self.assertIsNotNone(profile)
        self.assertFalse(profile.can_access_pricelist)

    def test_profile_not_duplicated_on_resave(self):
        user = User.objects.create_user(username="user", password="pass")
        user.first_name = "Renamed"
        user.save()
        self.assertEqual(UserProfile.objects.filter(user=user).count(), 1)

    def test_str(self):
        user = User.objects.create_user(username="alice", password="pass")
        self.assertEqual(
            str(user.userprofile), "alice profile"
        )

    def test_can_toggle_pricelist_access(self):
        user = User.objects.create_user(username="user", password="pass")
        user.userprofile.can_access_pricelist = True
        user.userprofile.save()
        user.userprofile.refresh_from_db()
        self.assertTrue(user.userprofile.can_access_pricelist)


class RolesTests(TestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin", password="pass", is_staff=True, is_superuser=True
        )
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.customer = User.objects.create_user(
            username="customer", password="pass"
        )

    def test_is_admin(self):
        self.assertTrue(is_admin(self.admin))
        self.assertFalse(is_admin(self.staff))
        self.assertFalse(is_admin(self.customer))

    def test_is_staff(self):
        self.assertTrue(is_staff(self.staff))
        self.assertTrue(is_staff(self.admin))
        self.assertFalse(is_staff(self.customer))

    def test_role_of(self):
        self.assertEqual(role_of(self.admin), "admin")
        self.assertEqual(role_of(self.staff), "staff")
        self.assertEqual(role_of(self.customer), "customer")

    def test_role_to_flags(self):
        self.assertEqual(
            role_to_flags("admin"), {"is_staff": True, "is_superuser": True}
        )
        self.assertEqual(
            role_to_flags("staff"), {"is_staff": True, "is_superuser": False}
        )
        self.assertEqual(
            role_to_flags("customer"), {"is_staff": False, "is_superuser": False}
        )

    def test_staff_and_admin_always_have_pricelist_access(self):
        self.assertTrue(can_access_pricelist(self.admin))
        self.assertTrue(can_access_pricelist(self.staff))

    def test_customer_without_profile_has_no_access(self):
        self.assertFalse(can_access_pricelist(self.customer))

    def test_customer_with_access_flag_can_view(self):
        self.customer.userprofile.can_access_pricelist = True
        self.customer.userprofile.save()
        self.assertTrue(can_access_pricelist(self.customer))

    def test_anonymous_user_has_no_access(self):
        self.assertFalse(can_access_pricelist(AnonymousUser()))


class RoleFormsTests(TestCase):

    def test_create_form_sets_admin_flags(self):
        form = UserCreateForm(
            data={
                "username": "boss",
                "password": "StrongPass123!",
                "role": "admin",
            }
        )
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_create_form_sets_staff_flags(self):
        form = UserCreateForm(
            data={
                "username": "worker",
                "password": "StrongPass123!",
                "role": "staff",
            }
        )
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_form_sets_customer_flags(self):
        form = UserCreateForm(
            data={
                "username": "buyer",
                "password": "StrongPass123!",
                "role": "customer",
            }
        )
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_form_rejects_weak_password(self):
        form = UserCreateForm(
            data={
                "username": "buyer",
                "password": "pass",
                "role": "customer",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)

    def test_create_form_saves_pricelist_access(self):
        form = UserCreateForm(
            data={
                "username": "buyer",
                "password": "StrongPass123!",
                "role": "customer",
                "pricelist_access": "on",
            }
        )
        self.assertTrue(form.is_valid())
        user = form.save()
        user.userprofile.refresh_from_db()
        self.assertTrue(user.userprofile.can_access_pricelist)

    def test_edit_form_initial_role_reflects_current_flags(self):
        staff = User.objects.create_user(
            username="worker", password="pass", is_staff=True
        )
        form = UserEditForm(instance=staff)
        self.assertEqual(form.fields["role"].initial, "staff")

    def test_edit_form_changes_role_to_customer(self):
        staff = User.objects.create_user(
            username="worker", password="pass", is_staff=True
        )
        form = UserEditForm(
            instance=staff,
            data={
                "username": "worker",
                "first_name": "",
                "last_name": "",
                "email": "",
                "role": "customer",
                "is_active": "on",
            },
        )
        self.assertTrue(form.is_valid())
        form.save()
        staff.refresh_from_db()
        self.assertFalse(staff.is_staff)
        self.assertFalse(staff.is_superuser)


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
