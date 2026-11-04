from datetime import date

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.companies.models import Assurance, Company, FieldProvenance, Source, SourceSnapshot


def make_snapshot():
    source = Source.objects.create(
        code="opencoesione",
        name="OpenCoesione",
        kind=Source.Kind.OPEN_DATA,
        url="https://opencoesione.gov.it/it/opendata/",
        licence="CC BY 4.0",
        attribution="Fonte: OpenCoesione",
    )
    return SourceSnapshot.objects.create(
        source=source,
        reference="opencoesione_soggetti_20260630.zip",
        checksum="abc123",
        data_date=date(2026, 6, 30),
    )


class CompanyTests(TestCase):
    def test_defaults(self):
        company = Company.objects.create(vat_number="03132170717", name="PA.MEC SRL")
        self.assertEqual(company.profile_level, Company.ProfileLevel.CANDIDATE)
        self.assertEqual(company.status, Company.Status.UNKNOWN)
        self.assertEqual(company.size_class, Company.SizeClass.UNKNOWN)
        self.assertEqual(str(company), "PA.MEC SRL (03132170717)")

    def test_vat_number_is_unique(self):
        Company.objects.create(vat_number="03132170717", name="A")
        with self.assertRaises(IntegrityError):
            Company.objects.create(vat_number="03132170717", name="B")

    def test_invalid_vat_fails_validation(self):
        company = Company(vat_number="03132170718", name="X")
        with self.assertRaises(ValidationError) as ctx:
            company.full_clean()
        self.assertIn("vat_number", ctx.exception.message_dict)

    def test_province_name(self):
        company = Company(vat_number="03132170717", name="X", province="BT")
        self.assertEqual(company.get_province_display(), "Barletta-Andria-Trani")


class ProvenanceTests(TestCase):
    def setUp(self):
        self.snapshot = make_snapshot()
        self.company = Company.objects.create(vat_number="03132170717", name="PA.MEC SRL", province="FG")

    def test_record_and_read_latest(self):
        self.company.record_provenance("province", "071", self.snapshot, Assurance.DERIVED, confidence=0.8)
        self.company.record_provenance("name", "PA.MEC  SRL", self.snapshot, Assurance.OFFICIAL)

        province = self.company.provenance_for("province")
        self.assertEqual(province.raw_value, "071")
        self.assertEqual(province.assurance, Assurance.DERIVED)
        self.assertEqual(province.confidence, 0.8)
        self.assertEqual(province.snapshot.source.code, "opencoesione")
        self.assertIsNone(self.company.provenance_for("website"))

    def test_latest_wins(self):
        newer = SourceSnapshot.objects.create(source=self.snapshot.source, reference="newer.zip", data_date=date(2026, 8, 31))
        self.company.record_provenance("name", "OLD", self.snapshot, Assurance.OFFICIAL)
        self.company.record_provenance("name", "NEW", newer, Assurance.OFFICIAL)
        self.assertEqual(self.company.provenance_for("name").raw_value, "NEW")
        self.assertEqual(FieldProvenance.objects.filter(company=self.company, field="name").count(), 2)

    def test_same_value_same_snapshot_is_not_duplicated(self):
        for _ in range(2):
            self.company.record_provenance("name", "PA.MEC SRL", self.snapshot, Assurance.OFFICIAL)
        self.assertEqual(FieldProvenance.objects.filter(company=self.company, field="name").count(), 1)

    def test_unknown_field_rejected(self):
        with self.assertRaises(ValueError):
            self.company.record_provenance("not_a_field", "x", self.snapshot, Assurance.OFFICIAL)

    def test_confidence_range(self):
        prov = FieldProvenance(company=self.company, field="name", snapshot=self.snapshot,
                               assurance=Assurance.INFERRED, confidence=1.5)
        with self.assertRaises(ValidationError):
            prov.full_clean()
