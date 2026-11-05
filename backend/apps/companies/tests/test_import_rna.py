import io
import shutil
import tempfile
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.companies.importers import rna
from apps.companies.models import Assurance, Company, SourceSnapshot, StateAid

from .test_import_opencoesione import BA, FG, LE

NS = "http://www.rna.it/RNA_aiuto/schema"


def component(amount, nominal=None, procedure="De Minimis", objective="Ricerca, sviluppo e innovazione", instrument="Sovvenzione"):
    return f"""
            <COMPONENTE_AIUTO>
                <DES_PROCEDIMENTO>{procedure}</DES_PROCEDIMENTO>
                <DES_OBIETTIVO>{objective}</DES_OBIETTIVO>
                <SETTORE_ATTIVITA>(NACE 2.1) J.62.1</SETTORE_ATTIVITA>
                <STRUMENTI_AIUTO>
                    <STRUMENTO_AIUTO>
                        <DES_STRUMENTO>{instrument}</DES_STRUMENTO>
                        <ELEMENTO_DI_AIUTO>{amount}</ELEMENTO_DI_AIUTO>
                        <IMPORTO_NOMINALE>{nominal or amount}</IMPORTO_NOMINALE>
                    </STRUMENTO_AIUTO>
                </STRUMENTI_AIUTO>
            </COMPONENTE_AIUTO>"""


def aid(cor, vat, components=None, size="PMI", granted="2026-10-05", title="Progetto digitale", cup="n.d."):
    return f"""
    <AIUTO>
        <CAR>35950</CAR>
        <TITOLO_MISURA>PR PUGLIA FESR 2021/2027 – Innovazione</TITOLO_MISURA>
        <DES_TIPO_MISURA>Regime di aiuti</DES_TIPO_MISURA>
        <SOGGETTO_CONCEDENTE>Regione Puglia</SOGGETTO_CONCEDENTE>
        <COR>{cor}</COR>
        <TITOLO_PROGETTO>{title}</TITOLO_PROGETTO>
        <DESCRIZIONE_PROGETTO>Descrizione di {title}</DESCRIZIONE_PROGETTO>
        <LINK_TRASPARENZA_NAZIONALE>https://www.regione.puglia.it/bandi/{cor}</LINK_TRASPARENZA_NAZIONALE>
        <DATA_CONCESSIONE>{granted}</DATA_CONCESSIONE>
        <CUP>{cup}</CUP>
        <DENOMINAZIONE_BENEFICIARIO>BENEFICIARIO SRL</DENOMINAZIONE_BENEFICIARIO>
        <CODICE_FISCALE_BENEFICIARIO>{vat}</CODICE_FISCALE_BENEFICIARIO>
        <DES_TIPO_BENEFICIARIO>{size}</DES_TIPO_BENEFICIARIO>
        <REGIONE_BENEFICIARIO>Puglia</REGIONE_BENEFICIARIO>
        <COMPONENTI_AIUTO>{''.join(components or [component("1000.50")])}
        </COMPONENTI_AIUTO>
    </AIUTO>"""


def write_rna(directory: Path, aids, name="rna_aiuti_2026_10.zip"):
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<LISTA_AIUTI xmlns="{NS}">{"".join(aids)}\n</LISTA_AIUTI>\n'
    path = directory / name
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name.replace("rna_aiuti_", "OpenData_Aiuti_").replace(".zip", ".xml"), xml.encode("utf-8"))
    return path


class RnaImportTests(TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        for vat, name in ((BA, "ALFA SRL"), (FG, "BETA SRL"), (LE, "GAMMA SRL")):
            Company.objects.create(vat_number=vat, name=name)

    def test_imports_aid_for_our_companies_only(self):
        path = write_rna(self.tmp, [aid("101", BA), aid("102", "00998540439"), aid("103", FG)])
        stats = rna.import_file(path)
        self.assertEqual(set(StateAid.objects.values_list("cor", flat=True)), {"101", "103"})
        self.assertEqual(stats["records"], 3)
        self.assertEqual(stats["created"], 2)

    def test_fields_and_summed_components(self):
        path = write_rna(self.tmp, [aid("101", BA, components=[
            component("19068.20", procedure="Esenzione", objective="Aiuti a finalità regionale", instrument="Sovvenzione"),
            component("90069.36", "100000.00", procedure="De Minimis", objective="Ricerca, sviluppo e innovazione", instrument="Garanzia"),
        ])])
        rna.import_file(path)
        record = StateAid.objects.get(cor="101")
        self.assertEqual(record.company.vat_number, BA)
        self.assertEqual(record.aid_amount, Decimal("109137.56"))
        self.assertEqual(record.nominal_amount, Decimal("119068.20"))
        self.assertEqual(record.granted_on, date(2026, 10, 5))
        self.assertEqual(record.measure_code, "35950")
        self.assertEqual(record.measure_title, "PR PUGLIA FESR 2021/2027 – Innovazione")
        self.assertEqual(record.measure_type, "Regime di aiuti")
        self.assertEqual(record.granting_body, "Regione Puglia")
        self.assertEqual(record.project_title, "Progetto digitale")
        self.assertEqual(record.project_description, "Descrizione di Progetto digitale")
        self.assertEqual(record.procedures, "Esenzione; De Minimis")
        self.assertEqual(record.objectives, "Aiuti a finalità regionale; Ricerca, sviluppo e innovazione")
        self.assertEqual(record.instruments, "Sovvenzione; Garanzia")
        self.assertEqual(record.sector, "(NACE 2.1) J.62.1")
        self.assertEqual(record.cup, "")
        self.assertEqual(record.beneficiary_size, "PMI")
        self.assertEqual(record.transparency_url, "https://www.regione.puglia.it/bandi/101")
        self.assertEqual(record.snapshot.source.code, "rna")
        self.assertEqual(record.snapshot.data_date, date(2026, 10, 1))

    def test_control_characters_are_tolerated(self):
        path = write_rna(self.tmp, [aid("101", BA, title="Emergenza COVID\x02 19")])
        rna.import_file(path)
        self.assertEqual(StateAid.objects.get(cor="101").project_title, "Emergenza COVID 19")

    def test_rerun_skips_and_updates_by_cor(self):
        path = write_rna(self.tmp, [aid("101", BA)])
        rna.import_file(path)
        self.assertTrue(rna.import_file(path)["already_imported"])
        corrected = write_rna(self.tmp, [aid("101", BA, components=[component("2000.00")])], name="rna_aiuti_2026_10_002.zip")
        stats = rna.import_file(corrected)
        self.assertEqual(StateAid.objects.count(), 1)
        self.assertEqual(StateAid.objects.get(cor="101").aid_amount, Decimal("2000.00"))
        self.assertEqual(stats["updated"], 1)

    def test_size_filled_only_when_unknown(self):
        Company.objects.filter(vat_number=FG).update(size_class=Company.SizeClass.SMALL)
        path = write_rna(self.tmp, [
            aid("101", BA, size="PMI", granted="2020-01-01"),
            aid("102", BA, size="Grande impresa", granted="2025-06-01"),
            aid("103", FG, size="Grande impresa"),
            aid("104", LE, size="Non classificata"),
        ])
        stats = rna.import_file(path)
        ba, fg, le = (Company.objects.get(vat_number=v) for v in (BA, FG, LE))
        self.assertEqual(ba.size_class, Company.SizeClass.LARGE)
        self.assertEqual(fg.size_class, Company.SizeClass.SMALL)
        self.assertEqual(le.size_class, Company.SizeClass.UNKNOWN)
        provenance = ba.provenance_for("size_class")
        self.assertEqual(provenance.assurance, Assurance.OFFICIAL)
        self.assertEqual(provenance.raw_value, "Grande impresa")
        self.assertEqual(provenance.snapshot.source.code, "rna")
        self.assertEqual(stats["sizes_set"], 1)

    def test_sme_size(self):
        rna.import_file(write_rna(self.tmp, [aid("101", BA, size="PMI")]))
        self.assertEqual(Company.objects.get(vat_number=BA).size_class, Company.SizeClass.SME)

    def test_file_names_and_dates(self):
        self.assertEqual(rna.local_name("OpenData_Aiuti_2021_12_002.zip"), "rna_aiuti_2021_12_002.zip")
        self.assertEqual(rna.period("rna_aiuti_2021_12_002.zip"), date(2021, 12, 1))
        self.assertIsNone(rna.period("other.zip"))


@override_settings()
class RnaDownloadAndCommandTests(TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        override = override_settings(DATA_DIR=self.tmp)
        override.enable()
        self.addCleanup(override.disable)
        Company.objects.create(vat_number=BA, name="ALFA SRL")

    def test_discovers_all_files_including_parts(self):
        pages = {
            0: '<a href="/open-data/aiuti/OpenData_Aiuti_2026_10.zip">x</a><a href="/open-data/aiuti/OpenData_Aiuti_2026_10.xml">x</a>',
            1: '<a href="/open-data/aiuti/OpenData_Aiuti_2021_12.zip">x</a><a href="/open-data/aiuti/OpenData_Aiuti_2021_12_002.zip">x</a>',
            2: "<p>no more files</p>",
        }

        def fake_page(page):
            return pages.get(page, "")

        with mock.patch.object(rna, "_listing_page", side_effect=fake_page):
            names = rna.discover_files()
        self.assertEqual(names, ["OpenData_Aiuti_2021_12.zip", "OpenData_Aiuti_2021_12_002.zip", "OpenData_Aiuti_2026_10.zip"])

    def test_download_only_missing_files(self):
        raw = rna.raw_dir()
        write_rna(raw, [aid("101", BA)], name="rna_aiuti_2026_09.zip")
        source = write_rna(self.tmp, [aid("102", BA)], name="rna_aiuti_2026_10.zip")
        names = ["OpenData_Aiuti_2026_09.zip", "OpenData_Aiuti_2026_10.zip"]
        with mock.patch.object(rna, "discover_files", return_value=names), \
             mock.patch.object(rna, "_fetch", side_effect=lambda url, target: shutil.copy(source, target)) as fetch:
            downloaded = rna.download_missing(raw)
        self.assertEqual([p.name for p in downloaded], ["rna_aiuti_2026_10.zip"])
        self.assertEqual(fetch.call_count, 1)
        self.assertTrue(fetch.call_args.args[0].endswith("/OpenData_Aiuti_2026_10.zip"))

    def test_command_imports_all_local_files_in_order(self):
        raw = rna.raw_dir()
        write_rna(raw, [aid("101", BA, components=[component("100.00")])], name="rna_aiuti_2026_09.zip")
        write_rna(raw, [aid("101", BA, components=[component("150.00")])], name="rna_aiuti_2026_10.zip")
        out = io.StringIO()
        call_command("import_rna", stdout=out)
        self.assertEqual(StateAid.objects.get(cor="101").aid_amount, Decimal("150.00"))
        self.assertEqual(SourceSnapshot.objects.filter(source__code="rna").count(), 2)
        self.assertIn("rna_aiuti_2026_10.zip", out.getvalue())
        out = io.StringIO()
        call_command("import_rna", stdout=out)
        self.assertIn("already imported", out.getvalue())
