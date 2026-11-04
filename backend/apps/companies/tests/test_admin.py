from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.companies.models import Company


class AdminTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser("admin", "admin@example.com", "pw")
        self.client.force_login(user)
        self.company = Company.objects.create(vat_number="03132170717", name="PA.MEC SRL", province="FG")

    def test_pages_load(self):
        for url in [
            "/admin/companies/company/",
            "/admin/companies/company/?province__exact=FG",
            "/admin/companies/company/?q=PA.MEC",
            f"/admin/companies/company/{self.company.pk}/change/",
            "/admin/companies/source/",
            "/admin/companies/sourcesnapshot/",
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
