from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.companies.importers import opencoesione, opencoesione_projects


class Command(BaseCommand):
    help = "Import OpenCoesione projects linked to the companies in the database."

    def add_arguments(self, parser):
        parser.add_argument("--projects-file", help="Path to a progetti zip (default: newest in data/raw/)")
        parser.add_argument("--soggetti-file", help="Path to a soggetti zip (default: newest in data/raw/)")
        parser.add_argument("--download", action="store_true", help="Download the latest projects file first")
        parser.add_argument("--force", action="store_true", help="Re-import even if these files were already imported")
        parser.add_argument("--batch-size", type=int, default=2000)

    def _resolve(self, value, prefix, raw_dir):
        if value:
            path = Path(value)
            if not path.exists():
                raise CommandError(f"File not found: {path}")
            return path
        path = opencoesione.latest_file(raw_dir, prefix)
        if path is None:
            raise CommandError(f"No {prefix}*.zip in {raw_dir}.")
        return path

    def handle(self, *args, **options):
        raw_dir = opencoesione.raw_dir()
        if options["download"]:
            self.stdout.write(f"Downloading {opencoesione_projects.DOWNLOAD_URL} ...")
            projects = opencoesione.download(raw_dir, opencoesione_projects.DOWNLOAD_URL, opencoesione_projects.FILE_PREFIX)
        else:
            projects = self._resolve(options["projects_file"], opencoesione_projects.FILE_PREFIX, raw_dir)
        soggetti = self._resolve(options["soggetti_file"], opencoesione.FILE_PREFIX, raw_dir)

        self.stdout.write(f"Importing {projects.name} with links from {soggetti.name} ...")
        stats = opencoesione_projects.run_import(
            projects, soggetti, force=options["force"], batch_size=options["batch_size"],
            progress=lambda s: self.stdout.write(f"  {s['projects_created'] + s['projects_updated'] + s['projects_unchanged']:,} projects processed"),
        )
        if stats["already_imported"]:
            self.stdout.write(self.style.WARNING("These files were already imported. Use --force to re-import."))
            return
        self.stdout.write(self.style.SUCCESS(f"Done: {projects.name}"))
        for key in ("links", "projects_created", "projects_updated", "projects_unchanged", "projects_missing", "projects_removed", "roles_created"):
            self.stdout.write(f"  {key.replace('_', ' ')}: {stats.get(key, 0):,}")
