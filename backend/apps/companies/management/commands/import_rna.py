from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.companies.importers import rna


class Command(BaseCommand):
    help = "Import state aid from the national register (RNA) for the companies in the database."

    def add_arguments(self, parser):
        parser.add_argument("--download", action="store_true", help="Download missing monthly files first")
        parser.add_argument("--file", help="Import a single file instead of all files in data/raw/rna/")
        parser.add_argument("--force", action="store_true", help="Re-import files already imported")

    def handle(self, *args, **options):
        directory = rna.raw_dir()
        if options["download"]:
            downloaded = rna.download_missing(directory, progress=lambda name: self.stdout.write(f"Downloading {name} ..."))
            self.stdout.write(f"Downloaded {len(downloaded)} new file(s).")

        if options["file"]:
            files = [Path(options["file"])]
            if not files[0].exists():
                raise CommandError(f"File not found: {files[0]}")
        else:
            files = rna.local_files(directory)
            if not files:
                raise CommandError(f"No rna_aiuti_*.zip in {directory}. Use --download.")

        for path in files:
            stats = rna.import_file(path, force=options["force"])
            if stats["already_imported"]:
                self.stdout.write(f"  {path.name}: already imported")
                continue
            self.stdout.write(
                f"  {path.name}: {stats.get('records', 0):,} records, {stats.get('companies', 0):,} companies, "
                f"{stats.get('created', 0):,} created, {stats.get('updated', 0):,} updated, {stats.get('sizes_set', 0):,} sizes set"
            )
        self.stdout.write(self.style.SUCCESS("Done."))
