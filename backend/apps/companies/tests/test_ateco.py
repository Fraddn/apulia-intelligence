from django.test import SimpleTestCase

from apps.companies.ateco import Ateco, normalize_ateco, section_for_division


class NormalizeAtecoTests(SimpleTestCase):
    def test_letter_prefix_defaults_to_2007(self):
        self.assertEqual(normalize_ateco("C-25.62.00"), Ateco("C", "25.62.00", "2007"))

    def test_version_suffix(self):
        self.assertEqual(normalize_ateco("62.01.00_2007"), Ateco("J", "62.01.00", "2007"))
        self.assertEqual(normalize_ateco("47.11.40_2022"), Ateco("G", "47.11.40", "2022"))

    def test_malformed_suffixes(self):
        self.assertEqual(normalize_ateco("62.01.00_2007_2007"), Ateco("J", "62.01.00", "2007"))
        self.assertEqual(normalize_ateco("62.01.00_2007_"), Ateco("J", "62.01.00", "2007"))

    def test_plain_code(self):
        self.assertEqual(normalize_ateco("62.01"), Ateco("J", "62.01", "2007"))
        self.assertEqual(normalize_ateco("85.6_2007"), Ateco("P", "85.6", "2007"))

    def test_section_only(self):
        self.assertEqual(normalize_ateco("P_2007"), Ateco("P", "", "2007"))

    def test_2025_codes_are_not_mapped(self):
        self.assertEqual(normalize_ateco("62.10.00_2025"), Ateco("", "62.10.00", "2025"))

    def test_whitespace_and_case(self):
        self.assertEqual(normalize_ateco("  j-62.01.00 "), Ateco("J", "62.01.00", "2007"))

    def test_invalid(self):
        for value in [None, "", "   ", "xx", "C-", "99999", "04.10", "Z-99.00.00", "C-62.01.00", "Z_2007"]:
            with self.subTest(value=value):
                self.assertIsNone(normalize_ateco(value))


class SectionForDivisionTests(SimpleTestCase):
    def test_boundaries(self):
        cases = {1: "A", 3: "A", 5: "B", 10: "C", 33: "C", 35: "D", 41: "F", 47: "G",
                 58: "J", 63: "J", 64: "K", 69: "M", 75: "M", 84: "O", 86: "Q", 99: "U"}
        for division, section in cases.items():
            with self.subTest(division=division):
                self.assertEqual(section_for_division(division), section)

    def test_unknown_division(self):
        self.assertIsNone(section_for_division(4))
        self.assertIsNone(section_for_division(100))
