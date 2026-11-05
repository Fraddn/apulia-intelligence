from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.companies.models import Assurance, Company, Project, ProjectRole, Source, SourceSnapshot


class ApiTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        source = Source.objects.create(
            code="opencoesione", name="OpenCoesione", kind=Source.Kind.OPEN_DATA,
            url="https://opencoesione.gov.it/it/opendata/", licence="CC BY 4.0", attribution="Fonte: OpenCoesione",
        )
        cls.snapshot = SourceSnapshot.objects.create(
            source=source, reference="opencoesione_soggetti_20260630.zip", data_date=date(2026, 6, 30)
        )
        rows = [
            ("03132170717", "ALFA INFORMATICA SRL", "BA", "J", "62.01.00", "small"),
            ("02462780731", "BETA COSTRUZIONI SRL", "TA", "F", "41.20.00", "unknown"),
            ("05866880726", "GAMMA SOFTWARE SPA", "BA", "J", "62.02.00", "large"),
            ("02229530734", "DELTA MECCANICA SNC", "LE", "C", "25.62.00", "unknown"),
            ("01439400761", "EPSILON SRL", "FG", "", "", "unknown"),
        ]
        for vat, name, province, section, code, size in rows:
            Company.objects.create(
                vat_number=vat, name=name, province=province, ateco_section=section,
                ateco_code=code, ateco_version="2007" if code else "", size_class=size,
            )
        alfa = Company.objects.get(vat_number="03132170717")
        alfa.record_provenance("name", "ALFA  INFORMATICA SRL", cls.snapshot, Assurance.OFFICIAL)
        alfa.record_provenance("province", "03132170717", cls.snapshot, Assurance.DERIVED, confidence=0.7)


class CompanyListTests(ApiTestCase):
    def get(self, query=""):
        response = self.client.get(f"/api/companies{query}")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_lists_companies_sorted_by_name(self):
        data = self.get()
        self.assertEqual(data["count"], 5)
        self.assertEqual([c["name"] for c in data["items"]][:2], ["ALFA INFORMATICA SRL", "BETA COSTRUZIONI SRL"])
        self.assertEqual(
            set(data["items"][0]),
            {"vat_number", "name", "province", "city", "ateco_section", "ateco_code", "size_class"},
        )

    def test_search_by_name_or_vat(self):
        self.assertEqual([c["name"] for c in self.get("?search=software")["items"]], ["GAMMA SOFTWARE SPA"])
        self.assertEqual(self.get("?search=0313217")["count"], 1)

    def test_filters(self):
        self.assertEqual(self.get("?province=BA")["count"], 2)
        self.assertEqual(self.get("?section=J")["count"], 2)
        self.assertEqual(self.get("?province=BA&section=J&search=alfa")["count"], 1)
        self.assertEqual(self.get("?ateco=62.01")["count"], 1)

    def test_pagination(self):
        data = self.get("?page=2&page_size=2")
        self.assertEqual(data["count"], 5)
        self.assertEqual([c["name"] for c in data["items"]], ["DELTA MECCANICA SNC", "EPSILON SRL"])

    def test_invalid_province_rejected(self):
        self.assertEqual(self.client.get("/api/companies?province=XX").status_code, 422)


class CompanyDetailTests(ApiTestCase):
    def test_detail_with_provenance(self):
        response = self.client.get("/api/companies/03132170717")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "ALFA INFORMATICA SRL")
        self.assertEqual(data["ateco_version"], "2007")
        provenance = {p["field"]: p for p in data["provenance"]}
        self.assertEqual(set(provenance), {"name", "province"})
        self.assertEqual(provenance["province"]["assurance"], "derived")
        self.assertEqual(provenance["province"]["confidence"], 0.7)
        self.assertEqual(provenance["name"]["raw_value"], "ALFA  INFORMATICA SRL")
        self.assertEqual(provenance["name"]["source"]["name"], "OpenCoesione")
        self.assertEqual(provenance["name"]["source"]["attribution"], "Fonte: OpenCoesione")
        self.assertEqual(provenance["name"]["data_date"], "2026-06-30")

    def test_only_latest_provenance_per_field(self):
        company = Company.objects.get(vat_number="03132170717")
        newer = SourceSnapshot.objects.create(source=self.snapshot.source, reference="newer.zip")
        company.record_provenance("name", "ALFA INFORMATICA S.R.L.", newer, Assurance.OFFICIAL)
        data = self.client.get("/api/companies/03132170717").json()
        names = [p for p in data["provenance"] if p["field"] == "name"]
        self.assertEqual(len(names), 1)
        self.assertEqual(names[0]["raw_value"], "ALFA INFORMATICA S.R.L.")

    def test_not_found(self):
        self.assertEqual(self.client.get("/api/companies/99999999999").status_code, 404)


class StatsTests(ApiTestCase):
    def test_stats(self):
        data = self.client.get("/api/stats").json()
        self.assertEqual(data["total"], 5)
        self.assertEqual(data["with_ateco"], 4)
        self.assertEqual(data["size_known"], 2)
        self.assertEqual(data["by_province"][0], {"province": "BA", "count": 2})
        self.assertEqual({p["province"] for p in data["by_province"]}, {"BA", "TA", "LE", "FG"})
        self.assertEqual(data["by_section"][0], {"section": "J", "count": 2})
        self.assertNotIn("", [s["section"] for s in data["by_section"]])
        source = data["sources"][0]
        self.assertEqual(source["name"], "OpenCoesione")
        self.assertEqual(source["licence"], "CC BY 4.0")
        self.assertEqual(source["data_date"], "2026-06-30")


class FundingApiTests(ApiTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        alfa = Company.objects.get(vat_number="03132170717")
        gamma = Company.objects.get(vat_number="05866880726")

        def make(code, title, funding, beneficiaries, theme=("01", "Ricerca e innovazione"), **extra):
            fields = {"start_date": date(2021, 1, 1), **extra}
            return Project.objects.create(
                code=code, title=title, summary=f"Sintesi {title}", theme_code=theme[0], theme=theme[1],
                public_funding=funding, beneficiaries_count=beneficiaries, snapshot=cls.snapshot,
                url=f"https://opencoesione.gov.it/{code}", **fields,
            )

        sole = make("P1", "Piattaforma cloud", Decimal("100000.00"), 1, status=Project.Status.COMPLETED)
        shared = make("P2", "Rete di ricerca", Decimal("900000.00"), 3, start_date=date(2023, 5, 1))
        works = make("P3", "Nuova strada", Decimal("5000000.00"), 1, theme=("07", "Trasporti e mobilità"))
        other = make("P4", "Software gestionale", Decimal("50000.00"), 1, theme=("03", "Competitività delle imprese"))
        B, C = ProjectRole.Role.BENEFICIARY, ProjectRole.Role.CONTRACTOR
        ProjectRole.objects.create(company=alfa, project=sole, role=B)
        ProjectRole.objects.create(company=alfa, project=shared, role=B)
        ProjectRole.objects.create(company=gamma, project=shared, role=B)
        ProjectRole.objects.create(company=alfa, project=works, role=C)
        ProjectRole.objects.create(company=gamma, project=other, role=B)

    def test_company_funding_summary(self):
        data = self.client.get("/api/companies/03132170717").json()
        self.assertEqual(data["funding"], {
            "beneficiary_projects": 2,
            "sole_beneficiary_projects": 1,
            "shared_projects": 1,
            "sole_beneficiary_funding": 100000.0,
            "roles": {"beneficiary": 2, "contractor": 1},
        })

    def test_company_projects_list(self):
        data = self.client.get("/api/companies/03132170717").json()
        self.assertEqual(data["projects_total"], 3)
        first = data["projects"][0]
        self.assertEqual([p["code"] for p in data["projects"]], ["P2", "P1", "P3"])
        self.assertEqual(first["role"], "beneficiary")
        self.assertEqual(first["beneficiaries_count"], 3)
        self.assertEqual(first["public_funding"], 900000.0)
        self.assertEqual(first["summary"], "Sintesi Rete di ricerca")
        self.assertEqual(first["theme_code"], "01")
        self.assertEqual(first["url"], "https://opencoesione.gov.it/P2")
        self.assertEqual(data["projects"][1]["status"], "completed")
        self.assertEqual(data["projects"][2]["role"], "contractor")

    def test_company_without_projects(self):
        data = self.client.get("/api/companies/02462780731").json()
        self.assertEqual(data["projects_total"], 0)
        self.assertEqual(data["projects"], [])
        self.assertEqual(data["funding"]["beneficiary_projects"], 0)
        self.assertIsNone(data["funding"]["sole_beneficiary_funding"])

    def test_data_date_comes_from_company_data_not_projects(self):
        newer = SourceSnapshot.objects.create(
            source=self.snapshot.source, reference="opencoesione_progetti_20260831.zip", data_date=date(2026, 8, 31)
        )
        Project.objects.filter(code="P1").update(snapshot=newer)
        source = self.client.get("/api/stats").json()["sources"][0]
        self.assertEqual(source["data_date"], "2026-06-30")

    def test_stats_funding(self):
        data = self.client.get("/api/stats").json()["funding"]
        self.assertEqual(data["beneficiary_companies"], 2)
        self.assertEqual(data["beneficiary_projects"], 3)
        self.assertEqual(data["sole_beneficiary_funding"], 150000.0)
        self.assertEqual(data["by_theme"], [
            {"theme_code": "01", "theme": "Ricerca e innovazione", "count": 2},
            {"theme_code": "03", "theme": "Competitività delle imprese", "count": 1},
        ])
