from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from apps.companies.vat import is_valid_vat, province_from_vat, validate_vat

VALID = ["03132170717", "02462780731", "05866880726", "02229530734", "01439400761"]


class VatChecksumTests(SimpleTestCase):
    def test_real_vat_numbers_are_valid(self):
        for vat in VALID:
            with self.subTest(vat=vat):
                self.assertTrue(is_valid_vat(vat))

    def test_wrong_check_digit_is_invalid(self):
        self.assertFalse(is_valid_vat("03132170718"))

    def test_wrong_length_or_non_digits_are_invalid(self):
        for value in ["", "123", "0313217071", "031321707170", "0313217071A", "RSSMRA80A01H501U"]:
            with self.subTest(value=value):
                self.assertFalse(is_valid_vat(value))

    def test_validator_raises(self):
        with self.assertRaises(ValidationError):
            validate_vat("03132170718")
        validate_vat("03132170717")


class ProvinceFromVatTests(SimpleTestCase):
    def test_puglia_tax_offices(self):
        cases = {
            "03132170717": "FG",
            "05866880726": "BA",
            "02462780731": "TA",
            "01439400761": None,
        }
        for vat, province in cases.items():
            with self.subTest(vat=vat):
                self.assertEqual(province_from_vat(vat), province)

    def test_all_offices(self):
        for office, province in {"071": "FG", "072": "BA", "073": "TA", "074": "BR", "075": "LE", "110": "BT"}.items():
            with self.subTest(office=office):
                self.assertEqual(province_from_vat(f"0000000{office}0"), province)

    def test_invalid_input_returns_none(self):
        self.assertIsNone(province_from_vat("abc"))
