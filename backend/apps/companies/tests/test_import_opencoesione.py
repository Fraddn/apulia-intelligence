import csv
import io
import shutil
import tempfile
import zipfile
from datetime import date
from pathlib import Path
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from apps.companies.importers import opencoesione
from apps.companies.models import Assurance, Company, FieldProvenance, Source, SourceSnapshot

HEADER = [
    "COD_LOCALE_PROGETTO", "SOGG_COD_RUOLO", "SOGG_DESCR_RUOLO", "SOGG_PROGR_RUOLO",
    "OC_CODICE_FISCALE_SOGG", "OC_DENOMINAZIONE_SOGG", "COD_FORMA_GIURIDICA_SOGG",
    "DESCR_FORMA_GIURIDICA_SOGG", "COD_COMUNE_SEDE_SOGG", "INDIRIZZO_SOGG", "CAP_SOGG",
    "COD_ATECO_SOGG", "DESCRIZIONE_ATECO_SOGG", "COD_ADDETTI_SOGG", "DESCR_ADDETTI_SOGG",
    "COD_DIMENSIONE_SOGG", "DESCR_DIMENSIONE_SOGG", "CODICE_FISCALE_SOGGETTO",
    "DENOMINAZIONE_SOGGETTO", "OC_COD_ENTE_BDAP", "OC_COD_ENTE_IPA", "OC_COD_ENTE_MIUR",
    "OC_COD_ENTE_SIOPE", "OC_COD_ENTE_ISTAT_S13", "OC_COD_ENTE_SSN",
]

SRL = ("1.3.2", "Società a responsabilità limitata")


def make_vat(serial: int, office: str) -> str:
    base = f"{serial:07d}{office}"
    total = sum(int(d) for d in base[0:10:2])
    for d in base[1:10:2]:
        doubled = int(d) * 2
        total += doubled - 9 if doubled > 9 else doubled
    return base + str((10 - total % 10) % 10)


def row(vat, name="ACME SRL", form=SRL, comune="", ateco="C-25.62.00", project="P1", **extra):
    data = dict.fromkeys(HEADER, "")
    data.update(
        COD_LOCALE_PROGETTO=project, SOGG_COD_RUOLO="2", SOGG_DESCR_RUOLO="Attuatore del progetto",
        OC_CODICE_FISCALE_SOGG=vat, OC_DENOMINAZIONE_SOGG=name,
        COD_FORMA_GIURIDICA_SOGG=form[0], DESCR_FORMA_GIURIDICA_SOGG=form[1],
        COD_COMUNE_SEDE_SOGG=comune, COD_ATECO_SOGG=ateco,
    )
    data.update(extra)
    return data


def write_zip(directory: Path, rows, filename="opencoesione_soggetti_20260630.zip", inner="soggetti_20260630.csv"):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=HEADER, delimiter=";", quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows(rows)
    path = directory / filename
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(inner, buffer.getvalue().encode("utf-8"))
    return path


BA = make_vat(1, "072")
FG = make_vat(2, "071")
LE = make_vat(3, "075")
MI = make_vat(4, "155")
TA = make_vat(5, "073")
BR = make_vat(6, "074")


class ImportTestCase(TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def run_import(self, rows, **kwargs):
        path = write_zip(self.tmp, rows, **kwargs)
        return opencoesione.run_import(path, batch_size=2)


class IncludeExcludeTests(ImportTestCase):
    def test_company_with_puglia_comune(self):
        self.run_import([row(BA, name="ALFA SRL", comune="016072006")])
        company = Company.objects.get(vat_number=BA)
        self.assertEqual(company.name, "ALFA SRL")
        self.assertEqual(company.province, "BA")
        self.assertEqual(company.municipality_code, "072006")
        self.assertEqual(company.profile_level, Company.ProfileLevel.CANDIDATE)
        province = company.provenance_for("province")
        self.assertEqual(province.assurance, Assurance.OFFICIAL)
        self.assertEqual(province.raw_value, "016072006")

    def test_province_derived_from_vat_when_comune_missing(self):
        self.run_import([row(FG)])
        company = Company.objects.get(vat_number=FG)
        self.assertEqual(company.province, "FG")
        self.assertEqual(company.municipality_code, "")
        province = company.provenance_for("province")
        self.assertEqual(province.assurance, Assurance.DERIVED)
        self.assertEqual(province.confidence, opencoesione.VAT_PROVINCE_CONFIDENCE)
        self.assertEqual(province.raw_value, FG)

    def test_company_that_moved_into_puglia(self):
        self.run_import([row(MI, comune="016075035")])
        self.assertEqual(Company.objects.get(vat_number=MI).province, "LE")

    def test_exclusions(self):
        stats = self.run_import([
            row("80062590379", form=("2.4.10", "Regione")),
            row(make_vat(7, "072"), form=("2.4.10", "Comune")),
            row("RSSMRA80A01H501U", form=("1.1.0", "Imprenditore individuale")),
            row(MI),
            row(BA[:-1] + str((int(BA[-1]) + 1) % 10)),
            row(LE, comune="015146049"),
            row(make_vat(8, "072"), form=("1.1.20", "Imprenditore individuale non agricolo")),
            row(make_vat(9, "072"), form=("1.8.10", "Associazione non riconosciuta")),
            row(make_vat(10, "072"), form=("1.7.90", "Altra forma di ente privato con personalità giuridica")),
            row(make_vat(11, "072"), form=("1.6.10", "Ente pubblico economico")),
        ])
        self.assertEqual(Company.objects.count(), 0)
        self.assertEqual(stats["skipped_rows"]["not_business"], 5)
        self.assertEqual(stats["skipped_rows"]["non_commercial_entity"], 1)
        self.assertEqual(stats["skipped_rows"]["not_company_code"], 1)
        self.assertEqual(stats["skipped_rows"]["outside_puglia"], 1)
        self.assertEqual(stats["skipped_rows"]["invalid_vat"], 1)
        self.assertEqual(stats["excluded_companies"]["registered_outside_puglia"], 1)

    def test_business_legal_forms_included(self):
        forms = ["1.2.30", "1.3.10", "1.3.20", "1.4.20", "1.5.20", "1.9.00"]
        self.run_import([row(make_vat(200 + i, "072"), form=(code, "x")) for i, code in enumerate(forms)])
        self.assertEqual(Company.objects.count(), len(forms))

    def test_record_without_real_name_is_excluded(self):
        stats = self.run_import([row(BA, name=BA), row(FG, name="")])
        self.assertEqual(Company.objects.count(), 0)
        self.assertEqual(stats["excluded_companies"]["no_name"], 2)

    def test_non_commercial_tax_codes_are_skipped(self):
        stats = self.run_import([row("80054330586", name="CNR"), row("93012345678", name="ASSOCIAZIONE SRL")])
        self.assertEqual(Company.objects.count(), 0)
        self.assertEqual(stats["skipped_rows"]["non_commercial_entity"], 2)

    def test_out_of_region_vat_needs_only_puglia_municipalities(self):
        rome = make_vat(300, "058")
        moved = make_vat(301, "058")
        stats = self.run_import([
            row(rome, name="RETE NAZIONALE SPA", comune="016072006", project="P1"),
            row(rome, name="RETE NAZIONALE SPA", comune="012058091", project="P2"),
            row(moved, name="TRASFERITA SRL", comune="016075035", project="P3"),
        ])
        self.assertFalse(Company.objects.filter(vat_number=rome).exists())
        self.assertTrue(Company.objects.filter(vat_number=moved).exists())
        self.assertEqual(stats["excluded_companies"]["registered_outside_puglia"], 1)

    def test_most_frequent_legal_form_wins(self):
        self.run_import([
            row(BA, form=("1.2.30", "Società in accomandita semplice"), project="P1"),
            row(BA, form=SRL, project="P2"),
            row(BA, form=SRL, project="P3"),
        ])
        self.assertEqual(Company.objects.get(vat_number=BA).legal_form_code, "1.3.2")

    def test_comune_outside_puglia_in_any_row_excludes_company(self):
        self.run_import([row(LE, project="P1"), row(LE, project="P2", comune="015146049")])
        self.assertFalse(Company.objects.filter(vat_number=LE).exists())


class AggregationTests(ImportTestCase):
    def test_rows_for_same_company_are_merged(self):
        stats = self.run_import([
            row(TA, name="BETA SRL", ateco="", project="P1"),
            row(TA, name="BETA SRL", ateco="J-62.01.00", project="P2",
                DESCR_DIMENSIONE_SOGG="Piccola impresa", COD_DIMENSIONE_SOGG="2"),
            row(TA, name="BETA SRL", project="P3", INDIRIZZO_SOGG="Via Roma 1", CAP_SOGG="74100"),
        ])
        self.assertEqual(Company.objects.count(), 1)
        company = Company.objects.get(vat_number=TA)
        self.assertEqual(company.ateco_code, "62.01.00")
        self.assertEqual(company.size_class, Company.SizeClass.SMALL)
        self.assertEqual(company.address, "Via Roma 1")
        self.assertEqual(company.postcode, "74100")
        self.assertEqual(stats["companies_found"], 1)
        self.assertEqual(stats["projects"][TA], 3)

    def test_size_mapping(self):
        sizes = {"Microimpresa": "micro", "Piccola impresa": "small", "Media impresa": "medium", "Grande impresa": "large"}
        rows = [row(make_vat(100 + i, "072"), DESCR_DIMENSIONE_SOGG=label) for i, label in enumerate(sizes)]
        self.run_import(rows)
        for i, expected in enumerate(sizes.values()):
            with self.subTest(expected=expected):
                self.assertEqual(Company.objects.get(vat_number=make_vat(100 + i, "072")).size_class, expected)


class CleaningTests(ImportTestCase):
    def test_ateco_versions(self):
        stats = self.run_import([
            row(BA, ateco="62.01.00_2007"),
            row(FG, ateco="47.11.40_2022"),
            row(LE, ateco="62.10.00_2025"),
            row(TA, ateco="garbage"),
        ])
        ba, fg, le, ta = (Company.objects.get(vat_number=v) for v in (BA, FG, LE, TA))
        self.assertEqual((ba.ateco_section, ba.ateco_code, ba.ateco_version), ("J", "62.01.00", "2007"))
        self.assertEqual((fg.ateco_section, fg.ateco_code, fg.ateco_version), ("G", "47.11.40", "2022"))
        self.assertEqual((le.ateco_section, le.ateco_code, le.ateco_version), ("", "62.10.00", "2025"))
        self.assertEqual((ta.ateco_section, ta.ateco_code), ("", ""))
        self.assertEqual(stats["ateco"]["version_2025"], 1)
        self.assertEqual(stats["ateco"]["unparsed"], 1)

    def test_quotes_removed_from_names(self):
        self.run_import([row(BA, name='"""PHARMAEFFE S.A.S. DI FOGLIA & C')])
        company = Company.objects.get(vat_number=BA)
        self.assertEqual(company.name, "PHARMAEFFE S.A.S. DI FOGLIA & C")
        self.assertEqual(company.provenance_for("name").raw_value, '"""PHARMAEFFE S.A.S. DI FOGLIA & C')

    def test_text_cleaned_but_raw_kept(self):
        raw_name = "CAFFÃ\xa0  ROMA  SRL"
        self.run_import([row(BA, name=raw_name, DESCRIZIONE_ATECO_SOGG="biscotti§; dolci")])
        company = Company.objects.get(vat_number=BA)
        self.assertEqual(company.name, "CAFFà ROMA SRL")
        self.assertEqual(company.ateco_description, "biscotti; dolci")
        self.assertEqual(company.provenance_for("name").raw_value, raw_name)
        self.assertEqual(company.provenance_for("legal_form").raw_value, SRL[1])


class SnapshotTests(ImportTestCase):
    def test_snapshot_and_source_recorded(self):
        stats = self.run_import([row(BA)])
        snapshot = SourceSnapshot.objects.get()
        self.assertEqual(snapshot.source.code, "opencoesione")
        self.assertEqual(snapshot.source.licence, "CC BY 4.0")
        self.assertEqual(snapshot.reference, "opencoesione_soggetti_20260630.zip")
        self.assertEqual(snapshot.data_date, date(2026, 6, 30))
        self.assertEqual(len(snapshot.checksum), 64)
        self.assertTrue(snapshot.stats["complete"])
        self.assertEqual(snapshot.stats["created"], 1)
        self.assertEqual(stats["created"], 1)

    def test_same_file_is_not_imported_twice(self):
        path = write_zip(self.tmp, [row(BA)])
        opencoesione.run_import(path)
        stats = opencoesione.run_import(path)
        self.assertTrue(stats["already_imported"])
        self.assertEqual(SourceSnapshot.objects.count(), 1)
        self.assertEqual(FieldProvenance.objects.filter(company__vat_number=BA, field="name").count(), 1)

    def test_force_reimport_does_not_duplicate_companies(self):
        path = write_zip(self.tmp, [row(BA)])
        opencoesione.run_import(path)
        stats = opencoesione.run_import(path, force=True)
        self.assertEqual(Company.objects.count(), 1)
        self.assertEqual(stats["unchanged"], 1)


class PruneTests(ImportTestCase):
    def test_companies_missing_from_new_file_are_reported_and_pruned(self):
        self.run_import([row(BA), row(FG)])
        stats = self.run_import(
            [row(BA)], filename="opencoesione_soggetti_20260831.zip", inner="soggetti_20260831.csv",
        )
        self.assertEqual(stats["stale"], 1)
        self.assertTrue(Company.objects.filter(vat_number=FG).exists())

        path = write_zip(self.tmp, [row(BA)], filename="opencoesione_soggetti_20261031.zip", inner="soggetti_20261031.csv")
        stats = opencoesione.run_import(path, prune=True)
        self.assertEqual(stats["pruned"], 1)
        self.assertFalse(Company.objects.filter(vat_number=FG).exists())

    def test_companies_with_other_sources_are_never_pruned(self):
        self.run_import([row(BA), row(FG)])
        fg = Company.objects.get(vat_number=FG)
        manual = SourceSnapshot.objects.create(
            source=Source.objects.create(code="manual", name="Manual", kind=Source.Kind.MANUAL), reference="admin edit",
        )
        fg.record_provenance("website", "https://beta.example", manual, Assurance.MANUAL)
        path = write_zip(self.tmp, [row(BA)], filename="opencoesione_soggetti_20260831.zip", inner="soggetti_20260831.csv")
        stats = opencoesione.run_import(path, prune=True)
        self.assertEqual(stats["pruned"], 0)
        self.assertTrue(Company.objects.filter(vat_number=FG).exists())


class UpdateTests(ImportTestCase):
    def test_newer_file_updates_values(self):
        self.run_import([row(BA, name="OLD NAME SRL")])
        stats = self.run_import(
            [row(BA, name="NEW NAME SRL")],
            filename="opencoesione_soggetti_20260831.zip", inner="soggetti_20260831.csv",
        )
        company = Company.objects.get(vat_number=BA)
        self.assertEqual(company.name, "NEW NAME SRL")
        self.assertEqual(company.provenance_for("name").raw_value, "NEW NAME SRL")
        self.assertEqual(stats["updated"], 1)

    def test_values_from_other_sources_are_not_overwritten(self):
        self.run_import([row(BA, name="OLD NAME SRL", ateco="")])
        company = Company.objects.get(vat_number=BA)
        manual = SourceSnapshot.objects.create(
            source=Source.objects.create(code="manual", name="Manual", kind=Source.Kind.MANUAL),
            reference="admin edit",
        )
        company.name = "Corrected Name S.r.l."
        company.save()
        company.record_provenance("name", "Corrected Name S.r.l.", manual, Assurance.MANUAL)

        self.run_import(
            [row(BA, name="OLD NAME SRL", ateco="J-62.01.00")],
            filename="opencoesione_soggetti_20260831.zip", inner="soggetti_20260831.csv",
        )
        company.refresh_from_db()
        self.assertEqual(company.name, "Corrected Name S.r.l.")
        self.assertEqual(company.ateco_code, "62.01.00")


class CommandTests(ImportTestCase):
    def setUp(self):
        super().setUp()
        self.raw = self.tmp / "raw"
        self.raw.mkdir()
        self.settings_override = override_settings(DATA_DIR=self.tmp)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

    def test_uses_newest_local_file(self):
        write_zip(self.raw, [row(BA)], filename="opencoesione_soggetti_20260430.zip", inner="soggetti_20260430.csv")
        write_zip(self.raw, [row(BA), row(FG)])
        out = io.StringIO()
        call_command("import_opencoesione", stdout=out)
        self.assertEqual(Company.objects.count(), 2)
        self.assertIn("opencoesione_soggetti_20260630.zip", out.getvalue())
        self.assertIn("created: 2", out.getvalue())

    def test_explicit_file(self):
        path = write_zip(self.tmp, [row(BA)], filename="custom.zip")
        call_command("import_opencoesione", file=str(path), stdout=io.StringIO())
        self.assertEqual(Company.objects.count(), 1)

    def test_no_file_available(self):
        with self.assertRaises(CommandError):
            call_command("import_opencoesione", stdout=io.StringIO())

    def test_download_saves_dated_file(self):
        source = write_zip(self.tmp, [row(BA)], filename="remote.zip", inner="soggetti_20260831.csv")
        response = mock.MagicMock()
        response.__enter__.return_value = io.BytesIO(source.read_bytes())
        with mock.patch.object(opencoesione, "urlopen", return_value=response) as urlopen:
            call_command("import_opencoesione", download=True, stdout=io.StringIO())
        self.assertEqual(urlopen.call_args.args[0].full_url, opencoesione.DOWNLOAD_URL)
        self.assertTrue((self.raw / "opencoesione_soggetti_20260831.zip").exists())
        self.assertEqual(Company.objects.count(), 1)
