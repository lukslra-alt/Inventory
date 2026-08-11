from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class LogoutViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="user", password="pass")

    def test_requires_login(self):
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_logs_out_user_and_redirects(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/accounts/login/")

        # Confirm the session is cleared
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)
