import io
import shutil
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.companies.enrichment import websites
from apps.companies.models import Assurance, Company, Source, SourceSnapshot, WebsiteCheck, WebsitePage

VAT = "01775410747"

HOME = f"""<html><head><title>Valle Fiorita</title><style>.x{{color:red}}</style><script>var a=1;</script></head>
<body><nav><a href="/chi-siamo">Chi siamo</a> <a href="/contatti/">Contatti</a> <a href="https://facebook.com/x">FB</a>
<a href="/prodotti">Prodotti</a> <a href="mailto:info@vallefiorita.it">Scrivici</a></nav>
<h1>Catering di qualità</h1><p>Produciamo pasta fresca dal 1990.</p>
<footer>Valle Fiorita S.r.l. – P.IVA {VAT} – Via Appia 120, 72100 Brindisi (BR)</footer></body></html>"""

CONTACT = """<html><body><h1>Contatti</h1>
<p>Telefono: <a href="tel:+390831123456">0831 123456</a></p>
<p>Email: info@vallefiorita.it – Ufficio: mario.rossi@vallefiorita.it – PEC: vallefiorita@pec.it</p>
<p>Sede operativa: Via Roma 5, 20121 Milano</p></body></html>"""


class ParsingTests(SimpleTestCase):
    def test_normalize_url(self):
        self.assertEqual(websites.normalize_url("vallefiorita.it"), "https://vallefiorita.it/")
        self.assertEqual(websites.normalize_url("http://www.vallefiorita.it/home"), "http://www.vallefiorita.it/home")
        self.assertEqual(websites.normalize_url("  "), "")
        self.assertEqual(websites.normalize_url("not a url"), "")

    def test_visible_text_skips_scripts_and_styles(self):
        text = websites.visible_text(HOME)
        self.assertIn("Produciamo pasta fresca dal 1990.", text)
        self.assertNotIn("var a", text)
        self.assertNotIn("color:red", text)

    def test_vat_formats(self):
        for text in (f"P.IVA {VAT}", f"P. IVA: IT{VAT}", "P.IVA 017 754 107 47", f"Partita IVA IT {VAT}", f"VAT IT{VAT}."):
            with self.subTest(text=text):
                self.assertTrue(websites.shows_vat(text, VAT))
        self.assertFalse(websites.shows_vat("P.IVA 01775410748", VAT))
        self.assertFalse(websites.shows_vat(f"Codice 9{VAT}9", VAT))

    def test_candidate_links_prefer_company_pages_on_same_site(self):
        links = websites.candidate_links(HOME, "https://vallefiorita.it/")
        self.assertEqual(links, ["https://vallefiorita.it/contatti/", "https://vallefiorita.it/chi-siamo"])

    def test_keywords_match_whole_words_only(self):
        html = """
            <a href="/it/finanziamenti-per-lo-sviluppo-aziendale">Finanziamenti</a>
            <a href="/it/esperti-legali">Esperti</a>
            <a href="/societa-trasparente">Società trasparente</a>
            <a href="/clienti/clienti-aziende">Aziende</a>
            <a href="/it/contattaci">Scrivici</a>
            <a href="/azienda/">La nostra storia</a>
            <a href="/privacy-policy">Privacy</a>
            <a href="/note-legali">Note legali</a>
        """
        self.assertEqual(websites.candidate_links(html, "https://x.it/"), [
            "https://x.it/it/contattaci", "https://x.it/azienda/", "https://x.it/note-legali", "https://x.it/privacy-policy",
        ])

    def test_text_after_a_link_is_not_part_of_its_label(self):
        html = '<a href="/news/1">Notizia</a> Contatti: scrivici <a href="/team">Team</a>'
        self.assertEqual(websites.candidate_links(html, "https://x.it/"), [])

    def test_city_stops_at_company_details(self):
        cases = {
            "Via Salvatore Cognetti, 36 70121 BARI C.F. 00347000721": "Bari",
            "Via Appia 120, 72100 Brindisi Cap. Soc. 10.000": "Brindisi",
            "Via Roma 1 - 73100 Lecce Tel. 0832 123456": "Lecce",
            "Via Roma 1 - 70056 Molfetta P.IVA 01234567890": "Molfetta",
            "Corso Italia 10, 74121 Taranto": "Taranto",
            "Via Dante 3, 76121 BARLETTA (BT)": "Barletta",
            "Piazza Duomo 2, 71121 San Giovanni Rotondo": "San Giovanni Rotondo",
        }
        for text, city in cases.items():
            with self.subTest(text=text):
                self.assertEqual(websites.address(text)["city"], city)

    def test_emails_generic_and_pec_only(self):
        text = websites.visible_text(CONTACT)
        self.assertEqual(websites.generic_email(text, CONTACT), "info@vallefiorita.it")
        self.assertEqual(websites.pec(text), "vallefiorita@pec.it")
        self.assertEqual(websites.generic_email("scrivi a mario.rossi@azienda.it", ""), "")
        self.assertEqual(websites.pec("PEC: azienda@legalmail.it"), "azienda@legalmail.it")

    def test_phone(self):
        self.assertEqual(websites.phone(websites.visible_text(CONTACT), CONTACT), "+39 0831123456")
        self.assertEqual(websites.phone("Tel. 080 5234567", ""), "080 5234567")
        self.assertEqual(websites.phone("P.IVA 01775410747", ""), "")

    def test_address_only_in_puglia(self):
        self.assertEqual(
            websites.address(websites.visible_text(HOME)),
            {"address": "Via Appia 120", "postcode": "72100", "city": "Brindisi"},
        )
        self.assertEqual(websites.address("Via Roma 5, 20121 Milano"), {})
        self.assertEqual(
            websites.address("Sede legale: Viale Japigia, 184 - 70126 Bari"),
            {"address": "Viale Japigia, 184", "postcode": "70126", "city": "Bari"},
        )


class FakeWeb:
    def __init__(self, pages, robots="User-agent: *\nAllow: /"):
        self.pages = pages
        self.robots = robots
        self.requested = []

    def __call__(self, url, timeout=None):
        self.requested.append(url)
        if url.endswith("/robots.txt"):
            return 200, self.robots
        if url not in self.pages:
            return 404, ""
        return 200, self.pages[url]


class FetchTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            vat_number=VAT, name="VALLE FIORITA CATERING SRL", province="BR", website="https://vallefiorita.it/"
        )

    def run_fetch(self, web, **kwargs):
        with mock.patch.object(websites, "_get", web):
            return websites.fetch(self.company, **kwargs)

    def test_verified_site_fills_contacts_and_keeps_pages(self):
        web = FakeWeb({"https://vallefiorita.it/": HOME, "https://vallefiorita.it/contatti/": CONTACT})
        check = self.run_fetch(web)
        self.company.refresh_from_db()
        self.assertEqual(check.status, WebsiteCheck.Status.VERIFIED)
        self.assertEqual(self.company.address, "Via Appia 120")
        self.assertEqual(self.company.postcode, "72100")
        self.assertEqual(self.company.city, "Brindisi")
        self.assertEqual(self.company.phone, "+39 0831123456")
        self.assertEqual(self.company.email, "info@vallefiorita.it")
        self.assertEqual(self.company.pec, "vallefiorita@pec.it")
        provenance = self.company.provenance_for("email")
        self.assertEqual(provenance.assurance, Assurance.COMPANY)
        self.assertEqual(provenance.snapshot.source.code, "company_website")
        self.assertIn(provenance.snapshot.reference, {"https://vallefiorita.it/", "https://vallefiorita.it/contatti/"})
        pages = WebsitePage.objects.filter(company=self.company)
        self.assertEqual(set(pages.values_list("url", flat=True)), {"https://vallefiorita.it/", "https://vallefiorita.it/contatti/"})
        self.assertIn("pasta fresca", pages.get(url="https://vallefiorita.it/").text)
        self.assertTrue(pages.get(url="https://vallefiorita.it/").vat_found)

    def test_pages_from_older_checks_are_replaced(self):
        WebsitePage.objects.create(
            company=self.company, url="https://vallefiorita.it/news/old", status_code=200, text="old", fetched_at=timezone.now()
        )
        self.run_fetch(FakeWeb({"https://vallefiorita.it/": HOME}))
        self.assertEqual(list(WebsitePage.objects.filter(company=self.company).values_list("url", flat=True)), ["https://vallefiorita.it/"])

    def test_site_without_our_vat_is_not_used(self):
        web = FakeWeb({"https://vallefiorita.it/": HOME.replace(VAT, "09999999999")})
        check = self.run_fetch(web)
        self.company.refresh_from_db()
        self.assertEqual(check.status, WebsiteCheck.Status.VAT_NOT_FOUND)
        self.assertEqual(self.company.email, "")
        self.assertEqual(self.company.city, "")

    def test_robots_disallow_is_respected(self):
        web = FakeWeb({"https://vallefiorita.it/": HOME}, robots="User-agent: *\nDisallow: /")
        check = self.run_fetch(web)
        self.assertEqual(check.status, WebsiteCheck.Status.BLOCKED)
        self.assertEqual([u for u in web.requested if not u.endswith("robots.txt")], [])

    def test_unreachable_site(self):
        def broken(url, timeout=None):
            raise OSError("connection refused")
        check = self.run_fetch(broken)
        self.assertEqual(check.status, WebsiteCheck.Status.UNREACHABLE)
        self.assertIn("connection refused", check.error)

    def test_no_website(self):
        self.company.website = ""
        self.company.save()
        check = self.run_fetch(FakeWeb({}))
        self.assertEqual(check.status, WebsiteCheck.Status.NO_WEBSITE)

    def test_other_sources_are_not_overwritten(self):
        official = SourceSnapshot.objects.create(source=Source.objects.create(code="opencoesione", name="OC", kind="open_data"), reference="f.zip")
        self.company.address = "Via Ufficiale 1"
        self.company.save()
        self.company.record_provenance("address", "Via Ufficiale 1", official, Assurance.OFFICIAL)
        self.run_fetch(FakeWeb({"https://vallefiorita.it/": HOME, "https://vallefiorita.it/contatti/": CONTACT}))
        self.company.refresh_from_db()
        self.assertEqual(self.company.address, "Via Ufficiale 1")
        self.assertEqual(self.company.email, "info@vallefiorita.it")

    def test_address_is_kept_as_one_unit(self):
        official = SourceSnapshot.objects.create(source=Source.objects.create(code="opencoesione", name="OC", kind="open_data"), reference="f.zip")
        self.company.address, self.company.postcode = "BRINDISI", "72100"
        self.company.save()
        self.company.record_provenance("address", "BRINDISI", official, Assurance.OFFICIAL)
        self.company.record_provenance("postcode", "72100", official, Assurance.OFFICIAL)
        lecce = HOME.replace("Via Appia 120, 72100 Brindisi (BR)", "Via Leuca 5, 73100 Lecce")
        self.run_fetch(FakeWeb({"https://vallefiorita.it/": lecce, "https://vallefiorita.it/contatti/": CONTACT}))
        self.company.refresh_from_db()
        self.assertEqual((self.company.address, self.company.postcode, self.company.city), ("BRINDISI", "72100", ""))
        self.assertEqual(self.company.email, "info@vallefiorita.it")

    def test_mixed_address_from_earlier_fetch_is_repaired(self):
        official = SourceSnapshot.objects.create(source=Source.objects.create(code="opencoesione", name="OC", kind="open_data"), reference="f.zip")
        website = SourceSnapshot.objects.create(source=Source.objects.create(code="company_website", name="W", kind="website"), reference="https://vallefiorita.it/")
        self.company.address, self.company.postcode, self.company.city = "BRINDISI", "72100", "Lecce"
        self.company.save()
        self.company.record_provenance("address", "BRINDISI", official, Assurance.OFFICIAL)
        self.company.record_provenance("city", "Lecce", website, Assurance.COMPANY)
        lecce = HOME.replace("Via Appia 120, 72100 Brindisi (BR)", "Via Leuca 5, 73100 Lecce")
        self.run_fetch(FakeWeb({"https://vallefiorita.it/": lecce}), force=True)
        self.company.refresh_from_db()
        self.assertEqual(self.company.city, "")

    def test_fetches_at_most_five_pages(self):
        links = "".join(f'<a href="/contatti-{i}">Contatti {i}</a>' for i in range(10))
        pages = {"https://vallefiorita.it/": f"<html><body>{links} P.IVA {VAT}</body></html>"}
        pages.update({f"https://vallefiorita.it/contatti-{i}": "<p>pagina</p>" for i in range(10)})
        web = FakeWeb(pages)
        self.run_fetch(web)
        self.assertEqual(len([u for u in web.requested if not u.endswith("robots.txt")]), websites.MAX_PAGES)

    def test_recent_check_is_reused_unless_forced(self):
        web = FakeWeb({"https://vallefiorita.it/": HOME})
        self.run_fetch(web)
        calls = len(web.requested)
        self.run_fetch(web)
        self.assertEqual(len(web.requested), calls)
        WebsiteCheck.objects.update(checked_at=timezone.now() - timedelta(days=websites.REFRESH_DAYS + 1))
        self.run_fetch(web)
        self.assertGreater(len(web.requested), calls)


class WebsiteCommandsTests(TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        Company.objects.create(vat_number=VAT, name="VALLE FIORITA CATERING SRL", province="BR")
        Company.objects.create(vat_number="03132170717", name="PA.MEC SRL", province="FG")

    def test_import_websites_csv(self):
        csv_path = self.tmp / "sites.csv"
        csv_path.write_text(f"vat_number,website\n{VAT},vallefiorita.it\n03132170717,\n99999999999,https://x.it\n")
        out = io.StringIO()
        call_command("import_websites", str(csv_path), stdout=out)
        company = Company.objects.get(vat_number=VAT)
        self.assertEqual(company.website, "https://vallefiorita.it/")
        provenance = company.provenance_for("website")
        self.assertEqual(provenance.assurance, Assurance.MANUAL)
        self.assertEqual(provenance.snapshot.reference, "sites.csv")
        self.assertIn("updated: 1", out.getvalue())
        self.assertIn("unknown VAT numbers: 1", out.getvalue())

    def test_fetch_websites_command(self):
        Company.objects.filter(vat_number=VAT).update(website="https://vallefiorita.it/")
        web = FakeWeb({"https://vallefiorita.it/": HOME, "https://vallefiorita.it/contatti/": CONTACT})
        out = io.StringIO()
        with mock.patch.object(websites, "_get", web):
            call_command("fetch_websites", stdout=out)
        self.assertEqual(Company.objects.get(vat_number=VAT).email, "info@vallefiorita.it")
        self.assertIn("verified: 1", out.getvalue())


class AdminTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser("admin", "admin@example.com", "pw")
        self.client.force_login(user)
        self.company = Company.objects.create(vat_number=VAT, name="VALLE FIORITA CATERING SRL", province="BR")

    def test_editing_website_in_admin_records_manual_provenance(self):
        data = {f.name: getattr(self.company, f.name) or "" for f in Company._meta.concrete_fields if f.editable and f.name != "id"}
        data.update(website="https://vallefiorita.it/", founded_on="", latitude="", longitude="")
        data.update({"provenance-TOTAL_FORMS": 0, "provenance-INITIAL_FORMS": 0})
        response = self.client.post(f"/admin/companies/company/{self.company.pk}/change/", data)
        self.assertEqual(response.status_code, 302, response.content[:2000])
        self.company.refresh_from_db()
        self.assertEqual(self.company.website, "https://vallefiorita.it/")
        self.assertEqual(self.company.provenance_for("website").assurance, Assurance.MANUAL)

    def test_admin_action_fetches_selected(self):
        Company.objects.filter(pk=self.company.pk).update(website="https://vallefiorita.it/")
        web = FakeWeb({"https://vallefiorita.it/": HOME})
        with mock.patch.object(websites, "_get", web):
            response = self.client.post("/admin/companies/company/", {"action": "fetch_website_contacts", "_selected_action": [self.company.pk]})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(WebsiteCheck.objects.get(company=self.company).status, WebsiteCheck.Status.VERIFIED)
