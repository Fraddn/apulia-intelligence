from django.test import SimpleTestCase

from apps.companies.text import clean_text


class CleanTextTests(SimpleTestCase):
    def test_double_encoded_utf8(self):
        self.assertEqual(clean_text("AttivitÃ\xa0 di pulizia"), "Attività di pulizia")
        self.assertEqual(clean_text("SocietÃ\xa0 a responsabilitÃ\xa0 limitata"), "Società a responsabilità limitata")

    def test_triple_encoded_utf8(self):
        self.assertEqual(clean_text("LA CITTÃ\x83Â\xa0 SOLIDALE"), "LA CITTà SOLIDALE")

    def test_windows_1252_mojibake(self):
        self.assertEqual(clean_text("KOINÃŠ SOC. COOP."), "KOINÊ SOC. COOP.")

    def test_truncated_text_left_as_is(self):
        self.assertEqual(clean_text("ASS.NE AGORÃ"), "ASS.NE AGORÃ")

    def test_escaped_semicolon(self):
        self.assertEqual(clean_text("biscotti§; prodotti"), "biscotti; prodotti")

    def test_whitespace_collapsed(self):
        self.assertEqual(clean_text("  PA.MEC   SRL \xa0"), "PA.MEC SRL")

    def test_correct_text_untouched(self):
        self.assertEqual(clean_text("Società Ã unchanged if not fixable"), "Società Ã unchanged if not fixable")
        self.assertEqual(clean_text("CAFFÈ"), "CAFFÈ")

    def test_empty(self):
        self.assertEqual(clean_text(None), "")
        self.assertEqual(clean_text("   "), "")
