from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from apps.companies.enrichment import discovery, websites
from apps.companies.models import Company, WebsiteCheck, WebsiteDiscovery

VAT = "01775410747"
URL = f"/api/companies/{VAT}/discover"


def found(*args, **kwargs):
    return discovery.ProbeResult(WebsiteDiscovery.Status.FOUND, "https://www.vallefiorita.it/", ["vallefiorita.it"])


def fake_fetch(company, force=False):
    company.city = "Brindisi"
    company.save()
    return WebsiteCheck.objects.create(company=company, url=company.website, status="verified", checked_at=timezone.now())


class DiscoverEndpointTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(vat_number=VAT, name="VALLE FIORITA CATERING SRL", province="BR")

    def post(self):
        response = self.client.post(URL)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_discovers_saves_and_reads_contacts(self):
        with mock.patch.object(discovery, "probe", side_effect=found) as probe, \
             mock.patch.object(websites, "fetch", side_effect=fake_fetch) as fetch:
            data = self.post()
        probe.assert_called_once()
        self.assertEqual(probe.call_args.kwargs["deadline"] is not None, True)
        fetch.assert_called_once()
        self.assertEqual(data["discovery"]["status"], "found")
        self.assertEqual(data["discovery"]["found_url"], "https://www.vallefiorita.it/")
        self.assertEqual(data["company"]["website"], "https://www.vallefiorita.it/")
        self.assertEqual(data["company"]["city"], "Brindisi")
        self.assertEqual(data["company"]["website_check"]["status"], "verified")

    def test_not_found_is_remembered(self):
        not_found = discovery.ProbeResult(WebsiteDiscovery.Status.NOT_FOUND, "", ["x.it"])
        with mock.patch.object(discovery, "probe", return_value=not_found) as probe:
            self.assertEqual(self.post()["discovery"]["status"], "not_found")
            self.assertEqual(self.post()["discovery"]["status"], "not_found")
        self.assertEqual(probe.call_count, 1)

    def test_old_attempt_is_retried(self):
        WebsiteDiscovery.objects.create(company=self.company, status="not_found", attempted_at=timezone.now() - timedelta(days=discovery.RETRY_DAYS + 1))
        with mock.patch.object(discovery, "probe", side_effect=found) as probe, mock.patch.object(websites, "fetch", side_effect=fake_fetch):
            self.post()
        probe.assert_called_once()

    def test_existing_website_is_only_read(self):
        self.company.website = "https://manual.it/"
        self.company.save()
        with mock.patch.object(discovery, "probe") as probe, mock.patch.object(websites, "fetch", side_effect=fake_fetch) as fetch:
            data = self.post()
            self.post()
        probe.assert_not_called()
        self.assertEqual(fetch.call_count, 1)
        self.assertIsNone(data["discovery"])
        self.assertEqual(data["company"]["website_check"]["status"], "verified")

    def test_timeout_is_not_remembered(self):
        timeout = discovery.ProbeResult(discovery.TIMEOUT)
        with mock.patch.object(discovery, "probe", return_value=timeout):
            data = self.post()
        self.assertEqual(data["discovery"]["status"], "timeout")
        self.assertFalse(WebsiteDiscovery.objects.exists())

    def test_busy_when_too_many_searches_run(self):
        with mock.patch.object(discovery, "probe") as probe, mock.patch.object(discovery, "_slots") as slots:
            slots.acquire.return_value = False
            data = self.post()
        probe.assert_not_called()
        self.assertEqual(data["discovery"]["status"], "busy")
        self.assertFalse(WebsiteDiscovery.objects.exists())

    def test_unknown_company(self):
        self.assertEqual(self.client.post("/api/companies/99999999999/discover").status_code, 404)


class ProbeDeadlineTests(TestCase):
    def test_probe_stops_at_deadline(self):
        clock = iter([0, 0, 100, 100, 100, 100])
        with mock.patch.object(discovery, "_resolves", return_value=True), \
             mock.patch.object(discovery.time, "monotonic", side_effect=lambda: next(clock)), \
             mock.patch.object(websites, "_robots") as robots, \
             mock.patch.object(websites, "_get", return_value=(200, "<p>nothing</p>")):
            robots.return_value.can_fetch.return_value = True
            result = discovery.probe("VALLE FIORITA CATERING SRL", VAT, deadline=10)
        self.assertEqual(result.status, discovery.TIMEOUT)
