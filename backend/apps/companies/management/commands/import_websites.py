import csv
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.companies.enrichment.websites import normalize_url
from apps.companies.models import Assurance, Company, Source, SourceSnapshot

MANUAL_SOURCE = {"code": "manual", "name": "Manual entry", "kind": Source.Kind.MANUAL}


def manual_snapshot(reference: str) -> SourceSnapshot:
    source, _ = Source.objects.get_or_create(code=MANUAL_SOURCE["code"], defaults=MANUAL_SOURCE)
    return SourceSnapshot.objects.create(source=source, reference=reference, data_date=date.today())


class Command(BaseCommand):
    help = "Set company websites from a CSV file with columns vat_number,website."

    def add_arguments(self, parser):
        parser.add_argument("path")

    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")
        snapshot = manual_snapshot(path.name)
        updated = unknown = skipped = 0
        with open(path, newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                vat = (row.get("vat_number") or "").strip()
                website = normalize_url(row.get("website") or "")
                if not website:
                    skipped += 1
                    continue
                company = Company.objects.filter(vat_number=vat).first()
                if company is None:
                    unknown += 1
                    continue
                company.website = website
                company.save(update_fields=["website", "updated_at"])
                company.record_provenance("website", website, snapshot, Assurance.MANUAL)
                updated += 1
        self.stdout.write(self.style.SUCCESS(f"updated: {updated}, skipped (no website): {skipped}, unknown VAT numbers: {unknown}"))
