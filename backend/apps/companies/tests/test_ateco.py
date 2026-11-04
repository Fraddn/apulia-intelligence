from django.test import SimpleTestCase

from apps.companies.ateco import normalize_ateco, section_for_division


class NormalizeAtecoTests(SimpleTestCase):
    def test_code_with_section_prefix(self):
        self.assertEqual(normalize_ateco("C-25.62.00"), ("C", "25.62.00"))

    def test_plain_code_derives_section(self):
        self.assertEqual(normalize_ateco("62.01.00"), ("J", "62.01.00"))
        self.assertEqual(normalize_ateco("47.11.40"), ("G", "47.11.40"))

    def test_short_codes(self):
        self.assertEqual(normalize_ateco("62.01"), ("J", "62.01"))
        self.assertEqual(normalize_ateco("62"), ("J", "62"))

    def test_whitespace_and_case(self):
        self.assertEqual(normalize_ateco("  j-62.01.00 "), ("J", "62.01.00"))

    def test_empty_or_garbage(self):
        for value in [None, "", "   ", "xx", "C-", "99999"]:
            with self.subTest(value=value):
                self.assertEqual(normalize_ateco(value), (None, None))


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
