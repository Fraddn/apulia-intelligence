from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.core.management.base import BaseCommand

from apps.companies.enrichment import discovery, websites
from apps.companies.models import Company, WebsiteDiscovery


class Command(BaseCommand):
    help = "Find company websites by guessing domains from the name; keep only sites showing the company's VAT number."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, help="Try at most this many companies")
        parser.add_argument("--workers", type=int, default=8, help="Companies checked in parallel")
        parser.add_argument("--force", action="store_true", help="Retry companies tried in the last 180 days")
        parser.add_argument("--fetch", action="store_true", help="Read contacts from each website found")

    def handle(self, *args, **options):
        companies = discovery.pending(force=options["force"]).values_list("id", "name", "vat_number")
        if options["limit"]:
            companies = companies[: options["limit"]]
        companies = list(companies)
        self.stdout.write(f"Trying {len(companies):,} companies with {options['workers']} workers ...")

        outcome = Counter()
        with ThreadPoolExecutor(max_workers=max(1, options["workers"])) as pool:
            futures = {pool.submit(discovery.probe, name, vat): company_id for company_id, name, vat in companies}
            for done, future in enumerate(as_completed(futures), start=1):
                company = Company.objects.get(id=futures[future])
                try:
                    result = future.result()
                except Exception as error:
                    outcome["error"] += 1
                    self.stderr.write(f"  [{done:,}/{len(companies):,}] error {company.name[:50]}: {error}")
                    continue
                discovery.save(company, result)
                outcome[result.status] += 1
                if result.status == WebsiteDiscovery.Status.FOUND:
                    self.stdout.write(f"  [{done:,}/{len(companies):,}] found {result.url}  {company.name[:50]}")
                    if options["fetch"]:
                        check = websites.fetch(company, force=True)
                        self.stdout.write(f"      contacts: {check.status}")
        summary = ", ".join(f"{status}: {count:,}" for status, count in sorted(outcome.items()))
        self.stdout.write(self.style.SUCCESS(f"Done. {summary or 'nothing to do'}"))
