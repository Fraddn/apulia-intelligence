from collections import Counter

from django.core.management.base import BaseCommand

from apps.companies.enrichment import websites
from apps.companies.models import Company


class Command(BaseCommand):
    help = "Read company websites: verify the VAT number and extract address, phone, email and PEC."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Re-check sites checked in the last 90 days")
        parser.add_argument("--limit", type=int, help="Check at most this many companies")

    def handle(self, *args, **options):
        companies = Company.objects.exclude(website="").order_by("name")
        if options["limit"]:
            companies = companies[: options["limit"]]
        outcome = Counter()
        for company in companies:
            check = websites.fetch(company, force=options["force"])
            outcome[check.status] += 1
            self.stdout.write(f"  {check.status:<14} {company.name[:50]}  {check.url}")
        summary = ", ".join(f"{status}: {count}" for status, count in sorted(outcome.items()))
        self.stdout.write(self.style.SUCCESS(f"Done. {summary or 'no companies with a website'}"))
