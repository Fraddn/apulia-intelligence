import io
from urllib.parse import urlparse
from datetime import timedelta
from unittest import mock

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.companies.enrichment import discovery, websites
from apps.companies.models import Assurance, Company, WebsiteCheck, WebsiteDiscovery

VAT = "01775410747"
PAGE_WITH_VAT = f"<html><body><a href='/contatti'>Contatti</a> Valle Fiorita srl P.IVA {VAT}</body></html>"
PAGE_WITHOUT_VAT = "<html><body><a href='/contatti'>Contatti</a> Altra azienda P.IVA 09999999999</body></html>"


class CandidateTests(SimpleTestCase):
    def test_tokens_drop_legal_forms_and_owner_names(self):
        self.assertEqual(discovery.name_tokens("VALLE FIORITA CATERING S.R.L."), ["valle", "fiorita", "catering"])
        self.assertEqual(discovery.name_tokens("BAR CENTRALE S.N.C. DI ROSSI MARIO & C."), ["bar", "centrale"])
        self.assertEqual(discovery.name_tokens("Pasticceria Raffaello s.a.s. di Imbriani G."), ["pasticceria", "raffaello"])
        self.assertEqual(discovery.name_tokens("CAFFÈ D'ITALIA SRL"), ["caffe", "italia"])

    def test_candidate_domains(self):
        domains = discovery.candidate_domains("VALLE FIORITA CATERING SRL")
        self.assertEqual(domains[:3], ["vallefioritacatering.it", "vallefioritacatering.com", "vallefioritacatering.eu"])
        for expected in ("vallefiorita.it", "valle-fiorita.it", "vallefiorita.com"):
            self.assertIn(expected, domains)
        self.assertEqual(len(domains), len(set(domains)))
        self.assertLessEqual(len(domains), discovery.MAX_CANDIDATES)

    def test_no_candidates_for_short_or_empty_names(self):
        self.assertEqual(discovery.candidate_domains("AB SRL"), [])
        self.assertEqual(discovery.candidate_domains("S.R.L."), [])

    def test_long_names_skip_labels_over_dns_limit(self):
        name = "CONSORZIO PRODUTTORI AGRICOLI ASSOCIATI DELLA MURGIA BARESE TERRITORIO E SVILUPPO SRL"
        domains = discovery.candidate_domains(name)
        self.assertIn("consorzio-produttori.it", domains)
        self.assertTrue(all(len(d.split(".")[0]) <= 63 for d in domains))
        self.assertFalse(discovery._resolves("a" * 80 + ".it"))


class ResolveTests(SimpleTestCase):
    def addresses(self, *ips):
        return mock.patch.object(websites.socket, "getaddrinfo", return_value=[(2, 1, 6, "", (ip, 443)) for ip in ips])

    def test_public_address_counts(self):
        with self.addresses("89.46.105.61"):
            self.assertTrue(discovery._resolves("cosera.com"))

    def test_loopback_and_private_answers_do_not_count(self):
        for ip in ("127.0.0.1", "0.0.0.0", "192.168.1.1", "10.0.0.5", "::1"):
            with self.subTest(ip=ip), self.addresses(ip):
                self.assertFalse(discovery._resolves("notreal.it"))


class ProbeTests(SimpleTestCase):
    def web(self, pages, robots="User-agent: *\nAllow: /"):
        def get(url, timeout=None):
            if url.endswith("/robots.txt"):
                return 200, robots
            if url in pages:
                return 200, pages[url]
            raise OSError("not found")
        return get

    def probe(self, live, pages, **kwargs):
        hosts = {urlparse(url).hostname for url in pages}
        with mock.patch.object(discovery, "_resolves", side_effect=lambda d: d in live), \
             mock.patch.object(discovery, "_listening", side_effect=lambda host, port: host in hosts), \
             mock.patch.object(websites, "_get", side_effect=self.web(pages, **kwargs)):
            return discovery.probe("VALLE FIORITA CATERING SRL", VAT)

    def test_finds_site_showing_our_vat(self):
        result = self.probe({"vallefiorita.it", "vallefioritacatering.it"}, {
            "https://www.vallefioritacatering.it/": PAGE_WITHOUT_VAT,
            "https://www.vallefiorita.it/": PAGE_WITH_VAT,
        })
        self.assertEqual(result.status, WebsiteDiscovery.Status.FOUND)
        self.assertEqual(result.url, "https://www.vallefiorita.it/")
        self.assertIn("vallefioritacatering.it", result.tried)

    def test_vat_on_contact_page_counts(self):
        result = self.probe({"vallefiorita.it"}, {
            "https://www.vallefiorita.it/": "<html><body><a href='/contatti'>Contatti</a> Benvenuti</body></html>",
            "https://www.vallefiorita.it/contatti": f"<p>P.IVA {VAT}</p>",
        })
        self.assertEqual(result.url, "https://www.vallefiorita.it/")

    def test_falls_back_to_bare_domain(self):
        result = self.probe({"vallefiorita.it"}, {"https://vallefiorita.it/": PAGE_WITH_VAT})
        self.assertEqual(result.url, "https://vallefiorita.it/")

    def test_falls_back_to_plain_http_when_https_fails(self):
        result = self.probe({"vallefiorita.it"}, {"http://www.vallefiorita.it/": PAGE_WITH_VAT})
        self.assertEqual(result.url, "http://www.vallefiorita.it/")

    def test_not_found_when_no_site_shows_vat(self):
        result = self.probe({"vallefiorita.it"}, {"https://www.vallefiorita.it/": PAGE_WITHOUT_VAT})
        self.assertEqual(result.status, WebsiteDiscovery.Status.NOT_FOUND)
        self.assertEqual(result.url, "")

    def test_no_domain_exists(self):
        result = self.probe(set(), {})
        self.assertEqual(result.status, WebsiteDiscovery.Status.NOT_FOUND)
        self.assertGreater(len(result.tried), 0)

    def test_robots_disallow_is_respected(self):
        result = self.probe({"vallefiorita.it"}, {"https://www.vallefiorita.it/": PAGE_WITH_VAT}, robots="User-agent: *\nDisallow: /")
        self.assertEqual(result.status, WebsiteDiscovery.Status.NOT_FOUND)

    def test_no_candidates(self):
        with mock.patch.object(discovery, "_resolves") as resolves:
            result = discovery.probe("AB SRL", VAT)
        self.assertEqual(result.status, WebsiteDiscovery.Status.NO_CANDIDATES)
        resolves.assert_not_called()


class SaveTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(vat_number=VAT, name="VALLE FIORITA CATERING SRL", province="BR")

    def test_found_site_is_saved_as_derived(self):
        result = discovery.ProbeResult(WebsiteDiscovery.Status.FOUND, "https://www.vallefiorita.it/", ["vallefiorita.it"])
        record = discovery.save(self.company, result)
        self.company.refresh_from_db()
        self.assertEqual(self.company.website, "https://www.vallefiorita.it/")
        provenance = self.company.provenance_for("website")
        self.assertEqual(provenance.assurance, Assurance.DERIVED)
        self.assertEqual(provenance.confidence, discovery.CONFIDENCE)
        self.assertEqual(provenance.snapshot.source.code, "website_discovery")
        self.assertEqual(record.status, WebsiteDiscovery.Status.FOUND)
        self.assertEqual(record.tried, ["vallefiorita.it"])

    def test_existing_website_is_never_replaced(self):
        self.company.website = "https://manual.it/"
        self.company.save()
        discovery.save(self.company, discovery.ProbeResult(WebsiteDiscovery.Status.FOUND, "https://www.vallefiorita.it/", []))
        self.company.refresh_from_db()
        self.assertEqual(self.company.website, "https://manual.it/")

    def test_pending_selection(self):
        other = Company.objects.create(vat_number="03132170717", name="PA.MEC SRL", website="https://pamec.it/")
        recent = Company.objects.create(vat_number="02462780731", name="ERRETIESSE SRL")
        WebsiteDiscovery.objects.create(company=recent, status="not_found", attempted_at=timezone.now())
        old = Company.objects.create(vat_number="05866880726", name="PUBLINFORMA SRL")
        WebsiteDiscovery.objects.create(company=old, status="not_found", attempted_at=timezone.now() - timedelta(days=discovery.RETRY_DAYS + 1))
        pending = set(discovery.pending().values_list("vat_number", flat=True))
        self.assertEqual(pending, {VAT, "05866880726"})
        self.assertNotIn(other.vat_number, pending)
        self.assertIn(recent.vat_number, set(discovery.pending(force=True).values_list("vat_number", flat=True)))


class CommandTests(TestCase):
    def setUp(self):
        Company.objects.create(vat_number=VAT, name="VALLE FIORITA CATERING SRL", province="BR")
        Company.objects.create(vat_number="03132170717", name="PA.MEC SRL", province="FG")

    def fake_probe(self, name, vat):
        if vat == VAT:
            return discovery.ProbeResult(WebsiteDiscovery.Status.FOUND, "https://www.vallefiorita.it/", ["vallefiorita.it"])
        return discovery.ProbeResult(WebsiteDiscovery.Status.NOT_FOUND, "", ["pamec.it"])

    def test_command_saves_results_and_summarises(self):
        out = io.StringIO()
        with mock.patch.object(discovery, "probe", side_effect=self.fake_probe):
            call_command("discover_websites", workers=2, stdout=out)
        self.assertEqual(Company.objects.get(vat_number=VAT).website, "https://www.vallefiorita.it/")
        self.assertEqual(WebsiteDiscovery.objects.count(), 2)
        self.assertIn("found: 1", out.getvalue())
        self.assertIn("not_found: 1", out.getvalue())

    def test_limit_and_fetch(self):
        with mock.patch.object(discovery, "probe", side_effect=self.fake_probe), \
             mock.patch.object(websites, "fetch", return_value=WebsiteCheck(status="verified")) as fetch:
            call_command("discover_websites", limit=1, fetch=True, stdout=io.StringIO())
        self.assertEqual(WebsiteDiscovery.objects.count(), 1)
        self.assertEqual(fetch.call_count, 1 if Company.objects.exclude(website="").exists() else 0)
