import io
import shutil
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.companies.importers import istat
from apps.companies.models import Assurance, Company, Municipality, Source, SourceSnapshot

HEADER = (
    'Codice Regione;"Codice dell\'Unità territoriale sovracomunale \r\n(valida a fini statistici)";'
    "Codice Provincia (Storico)(1);Progressivo del Comune (2);Codice Comune formato alfanumerico;"
    "Denominazione (Italiana e straniera);Denominazione in italiano;Denominazione altra lingua;"
    "Codice Ripartizione Geografica;Ripartizione geografica;Denominazione Regione;Sigla automobilistica\r\n"
)
ROWS = [
    "16;272;072;006;072006;Bari;Bari;;4;Sud;Puglia;BA",
    "16;071;071;029;071029;Monte Sant'Angelo;Monte Sant'Angelo;;4;Sud;Puglia;FG",
    "16;110;110;002;110002;Barletta;Barletta;;4;Sud;Puglia;BT",
    "15;263;063;049;063049;Napoli;Napoli;;4;Sud;Campania;NA",
]


def write_istat(directory: Path, rows=ROWS, name="istat_comuni_20261105.csv"):
    path = directory / name
    path.write_bytes((HEADER + "\r\n".join(rows) + "\r\n").encode("latin-1"))
    return path


class MunicipalityImportTests(TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_imports_all_municipalities(self):
        stats = istat.import_municipalities(write_istat(self.tmp))
        self.assertEqual(Municipality.objects.count(), 4)
        bari = Municipality.objects.get(code="072006")
        self.assertEqual((bari.name, bari.province, bari.region_code), ("Bari", "BA", "16"))
        self.assertEqual(Municipality.objects.get(code="071029").name, "Monte Sant'Angelo")
        self.assertEqual(stats["municipalities"], 4)

    def test_reimport_updates_names(self):
        istat.import_municipalities(write_istat(self.tmp))
        istat.import_municipalities(write_istat(self.tmp, [ROWS[0].replace(";Bari;Bari;", ";Bari;Bari città;")], name="istat_comuni_20270101.csv"))
        self.assertEqual(Municipality.objects.get(code="072006").name, "Bari città")
        self.assertEqual(Municipality.objects.count(), 4)


class FillCitiesTests(TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        istat.import_municipalities(write_istat(tmp))

    def test_fills_city_from_municipality_code(self):
        company = Company.objects.create(vat_number="03132170717", name="A", municipality_code="072006")
        stats = istat.fill_cities()
        company.refresh_from_db()
        self.assertEqual(company.city, "Bari")
        provenance = company.provenance_for("city")
        self.assertEqual(provenance.assurance, Assurance.DERIVED)
        self.assertEqual(provenance.raw_value, "072006")
        self.assertEqual(provenance.snapshot.source.code, "istat")
        self.assertEqual(stats["filled"], 1)

    def test_conflicting_postcode_blocks_the_fill(self):
        company = Company.objects.create(vat_number="03132170717", name="A", municipality_code="072006", postcode="72100")
        stats = istat.fill_cities()
        company.refresh_from_db()
        self.assertEqual(company.city, "")
        self.assertEqual(stats["postcode_conflict"], 1)

    def test_earlier_conflicting_fill_is_removed(self):
        company = Company.objects.create(vat_number="03132170717", name="A", municipality_code="072006")
        istat.fill_cities()
        Company.objects.filter(pk=company.pk).update(postcode="72100")
        stats = istat.fill_cities()
        company.refresh_from_db()
        self.assertEqual(company.city, "")
        self.assertEqual(stats["cleared"], 1)

    def test_matching_postcode_is_fine(self):
        company = Company.objects.create(vat_number="03132170717", name="A", municipality_code="110002", postcode="76121")
        istat.fill_cities()
        company.refresh_from_db()
        self.assertEqual(company.city, "Barletta")

    def test_unknown_codes_are_counted_not_guessed(self):
        Company.objects.create(vat_number="03132170717", name="A", municipality_code="072999")
        stats = istat.fill_cities()
        self.assertEqual(Company.objects.get().city, "")
        self.assertEqual(stats["unknown_code"], 1)

    def test_city_from_other_sources_is_kept(self):
        company = Company.objects.create(vat_number="03132170717", name="A", municipality_code="072006", city="Bari Palese")
        website = SourceSnapshot.objects.create(source=Source.objects.create(code="company_website", name="W", kind="website"), reference="https://a.it/")
        company.record_provenance("city", "Bari Palese", website, Assurance.COMPANY)
        istat.fill_cities()
        company.refresh_from_db()
        self.assertEqual(company.city, "Bari Palese")

    def test_rerun_is_idempotent(self):
        Company.objects.create(vat_number="03132170717", name="A", municipality_code="110002")
        istat.fill_cities()
        self.assertEqual(istat.fill_cities()["filled"], 0)
        self.assertEqual(Company.objects.get().city, "Barletta")


@override_settings()
class CommandTests(TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        override = override_settings(DATA_DIR=self.tmp)
        override.enable()
        self.addCleanup(override.disable)

    def test_command_uses_newest_local_file_and_fills_cities(self):
        raw = istat.raw_dir()
        write_istat(raw)
        Company.objects.create(vat_number="03132170717", name="A", municipality_code="071029")
        out = io.StringIO()
        call_command("import_istat_municipalities", stdout=out)
        self.assertEqual(Company.objects.get().city, "Monte Sant'Angelo")
        self.assertIn("municipalities: 4", out.getvalue())
        self.assertIn("cities filled: 1", out.getvalue())
