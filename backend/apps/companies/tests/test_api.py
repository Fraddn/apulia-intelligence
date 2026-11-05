from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.companies.models import Assurance, Company, Project, ProjectRole, Source, SourceSnapshot, StateAid, WebsiteCheck


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
            {"vat_number", "name", "province", "city", "ateco_section", "ateco_code", "size_class",
             "beneficiary_projects", "sole_beneficiary_funding"},
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

    def list(self, query=""):
        response = self.client.get(f"/api/companies{query}")
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_list_includes_funding_columns(self):
        items = {c["vat_number"]: c for c in self.list()["items"]}
        self.assertEqual(items["03132170717"]["beneficiary_projects"], 2)
        self.assertEqual(items["03132170717"]["sole_beneficiary_funding"], 100000.0)
        self.assertEqual(items["05866880726"]["beneficiary_projects"], 2)
        self.assertEqual(items["05866880726"]["sole_beneficiary_funding"], 50000.0)
        self.assertEqual(items["02462780731"]["beneficiary_projects"], 0)
        self.assertIsNone(items["02462780731"]["sole_beneficiary_funding"])

    def test_filter_by_division(self):
        self.assertEqual({c["name"] for c in self.list("?division=62")["items"]}, {"ALFA INFORMATICA SRL", "GAMMA SOFTWARE SPA"})
        self.assertEqual(self.list("?division=41")["count"], 1)
        self.assertEqual(self.client.get("/api/companies?division=6").status_code, 422)

    def test_filter_funded(self):
        data = self.list("?funded=true")
        self.assertEqual({c["name"] for c in data["items"]}, {"ALFA INFORMATICA SRL", "GAMMA SOFTWARE SPA"})
        self.assertEqual(data["count"], 2)

    def test_filter_by_theme_counts_only_beneficiary_roles(self):
        self.assertEqual({c["name"] for c in self.list("?theme=01")["items"]}, {"ALFA INFORMATICA SRL", "GAMMA SOFTWARE SPA"})
        self.assertEqual([c["name"] for c in self.list("?theme=03")["items"]], ["GAMMA SOFTWARE SPA"])
        self.assertEqual(self.list("?theme=07")["count"], 0)

    def test_sort_by_funding_and_projects(self):
        by_funding = [c["name"] for c in self.list("?sort=funding")["items"]]
        self.assertEqual(by_funding[:2], ["ALFA INFORMATICA SRL", "GAMMA SOFTWARE SPA"])
        self.assertEqual(len(by_funding), 5)
        by_projects = [c["name"] for c in self.list("?sort=projects")["items"]]
        self.assertEqual(by_projects[:2], ["ALFA INFORMATICA SRL", "GAMMA SOFTWARE SPA"])
        self.assertEqual(self.client.get("/api/companies?sort=random").status_code, 422)

    def test_filter_by_size_where_sme_includes_micro_small_medium(self):
        self.assertEqual([c["name"] for c in self.list("?size=small")["items"]], ["ALFA INFORMATICA SRL"])
        self.assertEqual([c["name"] for c in self.list("?size=sme")["items"]], ["ALFA INFORMATICA SRL"])
        self.assertEqual([c["name"] for c in self.list("?size=large")["items"]], ["GAMMA SOFTWARE SPA"])
        self.assertEqual(self.list("?size=unknown")["count"], 3)
        self.assertEqual(self.client.get("/api/companies?size=huge").status_code, 422)

    def test_filter_by_minimum_projects_and_funding(self):
        self.assertEqual(self.list("?min_projects=2")["count"], 2)
        self.assertEqual(self.list("?min_projects=3")["count"], 0)
        self.assertEqual([c["name"] for c in self.list("?min_funding=60000")["items"]], ["ALFA INFORMATICA SRL"])
        self.assertEqual(self.list("?min_funding=50000&size=large")["count"], 1)
        self.assertEqual(self.client.get("/api/companies?min_projects=0").status_code, 422)

    def test_filters_combine_with_section_and_search(self):
        self.assertEqual(self.list("?section=J&division=62&funded=true&search=gamma")["count"], 1)

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


class StateAidApiTests(ApiTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        rna_source = Source.objects.create(code="rna", name="RNA", kind=Source.Kind.OPEN_DATA)
        snapshot = SourceSnapshot.objects.create(source=rna_source, reference="rna_aiuti_2026_10.zip", data_date=date(2026, 10, 1))
        alfa = Company.objects.get(vat_number="03132170717")
        gamma = Company.objects.get(vat_number="05866880726")
        for cor, company, amount, granted in (
            ("101", alfa, "1000.50", date(2021, 3, 1)),
            ("102", alfa, "2500.00", date(2025, 6, 1)),
            ("103", gamma, "500.00", date(2024, 1, 1)),
            ("104", alfa, None, date(2026, 1, 1)),
        ):
            StateAid.objects.create(
                cor=cor, company=company, aid_amount=Decimal(amount) if amount else None, granted_on=granted,
                measure_title=f"Misura {cor}", granting_body="Regione Puglia", project_title=f"Progetto {cor}",
                objectives="Ricerca, sviluppo e innovazione", procedures="De Minimis", instruments="Sovvenzione",
                transparency_url=f"https://example.it/{cor}", snapshot=snapshot,
            )

    def test_company_aid(self):
        data = self.client.get("/api/companies/03132170717").json()["aid"]
        self.assertEqual(data["count"], 3)
        self.assertEqual(data["total_amount"], 3500.5)
        self.assertEqual(data["latest_date"], "2026-01-01")
        self.assertEqual([a["cor"] for a in data["items"]], ["104", "102", "101"])
        first = data["items"][1]
        self.assertEqual(first["aid_amount"], 2500.0)
        self.assertEqual(first["measure_title"], "Misura 102")
        self.assertEqual(first["granting_body"], "Regione Puglia")
        self.assertEqual(first["project_title"], "Progetto 102")
        self.assertEqual(first["objectives"], "Ricerca, sviluppo e innovazione")
        self.assertEqual(first["procedures"], "De Minimis")
        self.assertEqual(first["instruments"], "Sovvenzione")
        self.assertEqual(first["transparency_url"], "https://example.it/102")
        self.assertEqual(first["granted_on"], "2025-06-01")
        self.assertIsNone(data["items"][0]["aid_amount"])

    def test_company_without_aid(self):
        data = self.client.get("/api/companies/02462780731").json()["aid"]
        self.assertEqual(data, {"count": 0, "total_amount": None, "latest_date": None, "items": []})

    def test_stats_aid(self):
        data = self.client.get("/api/stats").json()["aid"]
        self.assertEqual(data["companies"], 2)
        self.assertEqual(data["grants"], 4)
        self.assertEqual(data["total_amount"], 4000.5)


class WebsiteCheckApiTests(ApiTestCase):
    def test_detail_without_check(self):
        data = self.client.get("/api/companies/03132170717").json()
        self.assertIsNone(data["website_check"])
        self.assertEqual(data["pec"], "")

    def test_detail_with_check(self):
        from django.utils import timezone

        company = Company.objects.get(vat_number="03132170717")
        company.pec = "alfa@pec.it"
        company.save()
        WebsiteCheck.objects.create(
            company=company, url="https://alfa.it/", status=WebsiteCheck.Status.VERIFIED, pages=3, checked_at=timezone.now()
        )
        data = self.client.get("/api/companies/03132170717").json()
        self.assertEqual(data["pec"], "alfa@pec.it")
        self.assertEqual(data["website_check"]["status"], "verified")
        self.assertEqual(data["website_check"]["url"], "https://alfa.it/")
        self.assertEqual(data["website_check"]["pages"], 3)
        self.assertIn("checked_at", data["website_check"])
