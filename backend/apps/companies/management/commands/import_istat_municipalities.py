from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.companies.importers import istat


class Command(BaseCommand):
    help = "Import the ISTAT list of Italian municipalities and fill company towns from their municipality code."

    def add_arguments(self, parser):
        parser.add_argument("--file", help="Path to the ISTAT CSV (default: newest in data/raw/istat/)")
        parser.add_argument("--download", action="store_true", help="Download the current list first")

    def handle(self, *args, **options):
        directory = istat.raw_dir()
        if options["download"]:
            path = istat.download(directory)
        elif options["file"]:
            path = Path(options["file"])
        else:
            path = istat.latest_file(directory)
        if path is None or not path.exists():
            raise CommandError(f"No {istat.FILE_PREFIX}*.csv in {directory}. Use --download.")

        stats = istat.import_municipalities(path)
        cities = istat.fill_cities()
        self.stdout.write(self.style.SUCCESS(
            f"{path.name}: municipalities: {stats['municipalities']:,} ({stats['created']:,} new, {stats['updated']:,} updated), "
            f"cities filled: {cities.get('filled', 0):,}, unknown codes: {cities.get('unknown_code', 0):,}, "
            f"postcode conflicts: {cities.get('postcode_conflict', 0):,}"
        ))
