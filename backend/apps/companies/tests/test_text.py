from django.test import SimpleTestCase

from apps.companies.text import clean_name, clean_text


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


class CleanNameTests(SimpleTestCase):
    def test_csv_escaped_quotes(self):
        cases = {
            '"" GEA CONSULTING SRLS': "GEA CONSULTING SRLS",
            '""" T.F. PLAST DI BLASI GIUSEPPE E F. S.N.C': "T.F. PLAST DI BLASI GIUSEPPE E F. S.N.C",
            '"""PHARMAEFFE S.A.S. DI FOGLIA GIOACCHINO & C': "PHARMAEFFE S.A.S. DI FOGLIA GIOACCHINO & C",
            '"""AL.AN. SAS"" DI ALBANESE ELENA': "AL.AN. SAS DI ALBANESE ELENA",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(clean_name(raw), expected)

    def test_wrapping_quotes(self):
        self.assertEqual(
            clean_name('"DAMIANI COSTRUZIONI S.N.C. DI DAMIANI RINALDO & C."'),
            "DAMIANI COSTRUZIONI S.N.C. DI DAMIANI RINALDO & C.",
        )
        self.assertEqual(clean_name("' AL FARO - S.R.L. '"), "AL FARO - S.R.L.")
        self.assertEqual(clean_name('"ECONHER SRL'), "ECONHER SRL")

    def test_accent_apostrophes_are_kept(self):
        self.assertEqual(clean_name('"ALTERECO - SOCIETA\' COOPERATIVA SOCIALE"'), "ALTERECO - SOCIETA' COOPERATIVA SOCIALE")
        self.assertEqual(clean_name("BAR CAFFE'"), "BAR CAFFE'")
        self.assertEqual(clean_name("SOCIETA' AGRICOLA ROSSI"), "SOCIETA' AGRICOLA ROSSI")

    def test_balanced_inner_quotes_are_kept(self):
        self.assertEqual(clean_name('CONSORZIO "LA RETE" SCARL'), 'CONSORZIO "LA RETE" SCARL')
        self.assertEqual(clean_name('CONSORZIO ""LA RETE"" SCARL'), 'CONSORZIO "LA RETE" SCARL')

    def test_also_cleans_text(self):
        self.assertEqual(clean_name('"CAFFÃ\xa0  ROMA  SRL"'), "CAFFà ROMA SRL")
        self.assertEqual(clean_name('""'), "")
