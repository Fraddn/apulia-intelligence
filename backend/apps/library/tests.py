from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.companies.models import Company
from apps.library import api as library_api
from apps.library.models import SavedCompany


class LibraryApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model().objects
        cls.anna = users.create_user("anna", "anna@example.com", "pw")
        cls.bruno = users.create_user("bruno", "bruno@example.com", "pw")
        cls.alfa = Company.objects.create(vat_number="03132170717", name="ALFA SRL", province="BA")
        cls.beta = Company.objects.create(vat_number="05866880726", name="BETA SPA", province="LE")

    def setUp(self):
        self.client.force_login(self.anna)

    def test_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get("/api/library").status_code, 401)
        self.assertEqual(self.client.post("/api/library/03132170717").status_code, 401)

    def test_save_list_and_remove(self):
        self.assertEqual(self.client.get("/api/library").json(), [])
        response = self.client.post("/api/library/03132170717")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "ALFA SRL")
        self.assertEqual(response.json()["note"], "")
        self.client.post("/api/library/05866880726")
        items = self.client.get("/api/library").json()
        self.assertEqual([i["vat_number"] for i in items], ["05866880726", "03132170717"])
        self.assertEqual(items[0]["beneficiary_projects"], 0)
        self.assertEqual(self.client.delete("/api/library/05866880726").status_code, 204)
        self.assertEqual([i["vat_number"] for i in self.client.get("/api/library").json()], ["03132170717"])

    def test_saving_twice_keeps_one_entry_and_the_note(self):
        self.client.post("/api/library/03132170717")
        self.client.patch("/api/library/03132170717", {"note": " Follow up "}, content_type="application/json")
        self.client.post("/api/library/03132170717")
        self.assertEqual(SavedCompany.objects.count(), 1)
        self.assertEqual(self.client.get("/api/library").json()[0]["note"], "Follow up")

    def test_each_user_has_their_own_library(self):
        SavedCompany.objects.create(user=self.bruno, company=self.beta, note="bruno's")
        self.client.post("/api/library/03132170717")
        self.assertEqual([i["vat_number"] for i in self.client.get("/api/library").json()], ["03132170717"])
        self.assertEqual(self.client.patch("/api/library/05866880726", {"note": "x"}, content_type="application/json").status_code, 404)
        self.client.delete("/api/library/05866880726")
        self.assertTrue(SavedCompany.objects.filter(user=self.bruno).exists())

    def test_unknown_company(self):
        self.assertEqual(self.client.post("/api/library/00000000000").status_code, 404)

    def test_note_length_is_limited(self):
        self.client.post("/api/library/03132170717")
        response = self.client.patch("/api/library/03132170717", {"note": "x" * 501}, content_type="application/json")
        self.assertEqual(response.status_code, 422)

    def test_library_size_is_capped(self):
        original = library_api.MAX_SAVED
        library_api.MAX_SAVED = 1
        try:
            self.client.post("/api/library/03132170717")
            self.assertEqual(self.client.post("/api/library/05866880726").status_code, 409)
            self.assertEqual(self.client.post("/api/library/03132170717").status_code, 200)
        finally:
            library_api.MAX_SAVED = original
