import csv
import io
import shutil
import tempfile
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.companies.importers import opencoesione_projects as projects_importer
from apps.companies.models import Company, Project, ProjectRole, SourceSnapshot

from .test_import_opencoesione import BA, FG, HEADER as SOGGETTI_HEADER, LE, row, write_zip

PROJECT_HEADER = [
    "COD_LOCALE_PROGETTO", "CUP", "OC_TITOLO_PROGETTO", "OC_SINTESI_PROGETTO", "OC_LINK", "OC_DESCR_CICLO",
    "OC_COD_TEMA_SINTETICO", "OC_TEMA_SINTETICO", "OC_FINANZ_UE_NETTO", "OC_FINANZ_TOT_PUB_NETTO", "TOT_PAGAMENTI",
    "OC_DATA_INIZIO_PROGETTO", "OC_DATA_FINE_PROGETTO_PREVISTA", "OC_DATA_FINE_PROGETTO_EFFETTIVA", "OC_STATO_PROGETTO",
]


def project(code, title="Progetto", **extra):
    data = dict.fromkeys(PROJECT_HEADER, "")
    data.update(
        COD_LOCALE_PROGETTO=code, CUP=f"CUP{code}", OC_TITOLO_PROGETTO=title,
        OC_SINTESI_PROGETTO=f"Descrizione di {title}", OC_LINK=f"https://opencoesione.gov.it/it/dati/progetti/{code.lower()}/",
        OC_DESCR_CICLO="Ciclo di programmazione 2014-2020", OC_COD_TEMA_SINTETICO="01",
        OC_TEMA_SINTETICO="Ricerca e innovazione", OC_FINANZ_UE_NETTO="1000,00", OC_FINANZ_TOT_PUB_NETTO="2500,50",
        TOT_PAGAMENTI="1200,25", OC_DATA_INIZIO_PROGETTO="20200115", OC_DATA_FINE_PROGETTO_PREVISTA="20221231",
        OC_STATO_PROGETTO="Concluso",
    )
    data.update(extra)
    return data


def write_projects(directory: Path, rows, filename="opencoesione_progetti_20260831.zip", inner="progetti_20260831.csv"):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=PROJECT_HEADER, delimiter=";", quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows(rows)
    path = directory / filename
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(inner, buffer.getvalue().encode("utf-8"))
    return path


def role_row(vat, code, role, name="X SRL"):
    labels = {"1": "Programmatore del progetto", "2": "Attuatore del progetto", "3": "Beneficiario del progetto", "4": "Realizzatore del progetto"}
    return row(vat, name=name, project=code, SOGG_COD_RUOLO=role, SOGG_DESCR_RUOLO=labels[role])


OTHER = "80062590379"


class ProjectImportTests(TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        for vat, name in ((BA, "ALFA SRL"), (FG, "BETA SRL"), (LE, "GAMMA SRL")):
            Company.objects.create(vat_number=vat, name=name)
        self.soggetti = write_zip(self.tmp, [
            role_row(BA, "P1", "3"),
            role_row(BA, "P1", "2"),
            role_row(BA, "P2", "3"),
            role_row(FG, "P2", "3"),
            role_row(OTHER, "P2", "3"),
            role_row(FG, "P3", "4"),
            role_row(OTHER, "P4", "3"),
            role_row(LE, "P9", "3"),
        ])
        self.projects = write_projects(self.tmp, [
            project("P1", "Piattaforma cloud"),
            project("P2", "Rete di ricerca", OC_FINANZ_TOT_PUB_NETTO="900000,00", OC_STATO_PROGETTO="In corso"),
            project("P3", "Nuova strada", OC_COD_TEMA_SINTETICO="07", OC_TEMA_SINTETICO="Trasporti e mobilità",
                    OC_DATA_INIZIO_PROGETTO="", OC_STATO_PROGETTO="Liquidato"),
            project("P4", "Progetto di altri"),
        ])

    def run_import(self, **kwargs):
        return projects_importer.run_import(self.projects, self.soggetti, batch_size=2, **kwargs)

    def test_imports_only_projects_of_our_companies(self):
        stats = self.run_import()
        self.assertEqual(set(Project.objects.values_list("code", flat=True)), {"P1", "P2", "P3"})
        self.assertEqual(stats["projects_created"], 3)
        self.assertEqual(stats["projects_missing"], 1)

    def test_project_fields(self):
        self.run_import()
        p1 = Project.objects.get(code="P1")
        self.assertEqual(p1.title, "Piattaforma cloud")
        self.assertEqual(p1.summary, "Descrizione di Piattaforma cloud")
        self.assertEqual(p1.cup, "CUPP1")
        self.assertEqual((p1.theme_code, p1.theme), ("01", "Ricerca e innovazione"))
        self.assertEqual(p1.cycle, "Ciclo di programmazione 2014-2020")
        self.assertEqual(p1.public_funding, Decimal("2500.50"))
        self.assertEqual(p1.eu_funding, Decimal("1000.00"))
        self.assertEqual(p1.payments, Decimal("1200.25"))
        self.assertEqual(p1.start_date, date(2020, 1, 15))
        self.assertEqual(p1.expected_end_date, date(2022, 12, 31))
        self.assertIsNone(p1.actual_end_date)
        self.assertEqual(p1.status, Project.Status.COMPLETED)
        self.assertEqual(p1.url, "https://opencoesione.gov.it/it/dati/progetti/p1/")
        self.assertEqual(p1.snapshot.source.code, "opencoesione")
        p3 = Project.objects.get(code="P3")
        self.assertIsNone(p3.start_date)
        self.assertEqual(p3.status, Project.Status.SETTLED)
        self.assertEqual(Project.objects.get(code="P2").status, Project.Status.ONGOING)

    def test_roles_and_beneficiary_counts(self):
        self.run_import()
        roles = set(ProjectRole.objects.values_list("company__vat_number", "project__code", "role"))
        self.assertEqual(roles, {
            (BA, "P1", "beneficiary"), (BA, "P1", "implementer"), (BA, "P2", "beneficiary"),
            (FG, "P2", "beneficiary"), (FG, "P3", "contractor"),
        })
        self.assertEqual(Project.objects.get(code="P1").beneficiaries_count, 1)
        self.assertEqual(Project.objects.get(code="P2").beneficiaries_count, 3)
        self.assertEqual(Project.objects.get(code="P3").beneficiaries_count, 0)

    def test_snapshot_and_rerun(self):
        self.run_import()
        snapshot = SourceSnapshot.objects.get(reference__contains="progetti")
        self.assertEqual(snapshot.data_date, date(2026, 8, 31))
        self.assertIn("opencoesione_soggetti_20260630.zip", snapshot.reference)
        self.assertTrue(self.run_import()["already_imported"])
        stats = self.run_import(force=True)
        self.assertEqual(Project.objects.count(), 3)
        self.assertEqual(ProjectRole.objects.count(), 5)
        self.assertEqual(stats["projects_updated"], 0)
        self.assertEqual(stats["projects_unchanged"], 3)

    def test_updates_changed_projects(self):
        self.run_import()
        self.projects = write_projects(
            self.tmp, [project("P1", "Piattaforma cloud v2", OC_FINANZ_TOT_PUB_NETTO="3000,00")],
            filename="opencoesione_progetti_20261031.zip", inner="progetti_20261031.csv",
        )
        stats = self.run_import()
        p1 = Project.objects.get(code="P1")
        self.assertEqual(p1.title, "Piattaforma cloud v2")
        self.assertEqual(p1.public_funding, Decimal("3000.00"))
        self.assertIn("20261031", p1.snapshot.reference)
        self.assertEqual(stats["projects_updated"], 1)

    def test_projects_left_without_companies_are_removed(self):
        self.run_import()
        Company.objects.filter(vat_number=FG).delete()
        stats = self.run_import(force=True)
        self.assertFalse(Project.objects.filter(code="P3").exists())
        self.assertTrue(Project.objects.filter(code="P2").exists())
        self.assertEqual(stats["projects_removed"], 1)

    def test_bad_amounts_and_dates_become_empty(self):
        self.projects = write_projects(self.tmp, [project("P1", OC_FINANZ_TOT_PUB_NETTO="n/d", OC_DATA_INIZIO_PROGETTO="2020")])
        self.run_import()
        p1 = Project.objects.get(code="P1")
        self.assertIsNone(p1.public_funding)
        self.assertIsNone(p1.start_date)


class ProjectCommandTests(TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        (self.tmp / "raw").mkdir()
        override = override_settings(DATA_DIR=self.tmp)
        override.enable()
        self.addCleanup(override.disable)
        Company.objects.create(vat_number=BA, name="ALFA SRL")

    def test_uses_newest_local_files(self):
        write_zip(self.tmp / "raw", [role_row(BA, "P1", "3")])
        write_projects(self.tmp / "raw", [project("P1")])
        out = io.StringIO()
        call_command("import_opencoesione_projects", stdout=out)
        self.assertEqual(Project.objects.count(), 1)
        self.assertIn("opencoesione_progetti_20260831.zip", out.getvalue())
        self.assertIn("projects created: 1", out.getvalue())
