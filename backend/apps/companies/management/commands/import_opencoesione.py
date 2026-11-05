from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.companies.importers import opencoesione


class Command(BaseCommand):
    help = "Import Puglia businesses from the OpenCoesione 'Soggetti' dataset."

    def add_arguments(self, parser):
        parser.add_argument("--file", help="Path to a soggetti zip file (default: newest in data/raw/)")
        parser.add_argument("--download", action="store_true", help="Download the latest file first")
        parser.add_argument("--force", action="store_true", help="Re-import even if this file was already imported")
        parser.add_argument("--prune", action="store_true", help="Delete companies no longer in the file (only if they have no other sources)")
        parser.add_argument("--batch-size", type=int, default=1000)

    def handle(self, *args, **options):
        raw_dir = opencoesione.raw_dir()
        if options["download"]:
            self.stdout.write(f"Downloading {opencoesione.DOWNLOAD_URL} ...")
            path = opencoesione.download(raw_dir)
        elif options["file"]:
            path = Path(options["file"])
            if not path.exists():
                raise CommandError(f"File not found: {path}")
        else:
            path = opencoesione.latest_file(raw_dir)
            if path is None:
                raise CommandError(f"No {opencoesione.FILE_PREFIX}*.zip in {raw_dir}. Use --download or --file.")

        self.stdout.write(f"Importing {path.name} ...")
        stats = opencoesione.run_import(
            path,
            force=options["force"],
            prune=options["prune"],
            batch_size=options["batch_size"],
            progress=lambda s: self.stdout.write(f"  {s['created'] + s['updated'] + s['unchanged']:,} companies saved"),
        )

        if stats["already_imported"]:
            self.stdout.write(self.style.WARNING(f"{path.name} was already imported. Use --force to re-import."))
            return

        self.stdout.write(self.style.SUCCESS(f"Done: {path.name}"))
        for key in ("rows_read", "rows_matched", "companies_found", "created", "updated", "unchanged", "stale", "pruned"):
            self.stdout.write(f"  {key.replace('_', ' ')}: {stats[key]:,}")
        for group in ("skipped_rows", "excluded_companies", "ateco"):
            if stats[group]:
                details = ", ".join(f"{k}: {v:,}" for k, v in sorted(stats[group].items()))
                self.stdout.write(f"  {group.replace('_', ' ')}: {details}")
