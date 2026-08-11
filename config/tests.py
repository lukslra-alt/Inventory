from django.test import TestCase
from django.urls import reverse


class ServiceWorkerTests(TestCase):

    def test_serves_service_worker_javascript(self):
        response = self.client.get(reverse("service_worker"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"], "application/javascript"
        )

    def test_serves_worker_with_root_control_header(self):
        response = self.client.get(reverse("service_worker"))
        self.assertEqual(response["Service-Worker-Allowed"], "/")

    def test_serves_real_file_content(self):
        response = self.client.get(reverse("service_worker"))
        self.assertIn(b"CACHE_NAME", response.content)
