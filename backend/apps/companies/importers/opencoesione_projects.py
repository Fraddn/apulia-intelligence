import hashlib
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.db import transaction

from ..models import Company, Project, ProjectRole, SourceSnapshot
from ..text import clean_text
from . import opencoesione as oc

DOWNLOAD_URL = "https://opencoesione.gov.it/it/opendata/progetti.zip"
FILE_PREFIX = "opencoesione_progetti_"

ROLES = {
    "1": ProjectRole.Role.PROGRAMMER,
    "2": ProjectRole.Role.IMPLEMENTER,
    "3": ProjectRole.Role.BENEFICIARY,
    "4": ProjectRole.Role.CONTRACTOR,
}
BENEFICIARY_CODE = "3"

STATUSES = {
    "non avviato": Project.Status.NOT_STARTED,
    "in corso": Project.Status.ONGOING,
    "concluso": Project.Status.COMPLETED,
    "liquidato": Project.Status.SETTLED,
}

PROJECT_FIELDS = [
    "cup", "title", "summary", "theme_code", "theme", "cycle", "status", "public_funding", "eu_funding",
    "payments", "start_date", "expected_end_date", "actual_end_date", "beneficiaries_count", "url", "snapshot",
]


def parse_amount(value):
    text = (value or "").strip()
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    if not text:
        return None
    try:
        return Decimal(text).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def parse_date(value):
    value = (value or "").strip()
    if len(value) != 8 or not value.isdigit():
        return None
    try:
        return date(int(value[:4]), int(value[4:6]), int(value[6:]))
    except ValueError:
        return None


def _links(soggetti_path: Path, vats, stats):
    links = set()
    for row in oc._rows(soggetti_path):
        vat = (row.get("OC_CODICE_FISCALE_SOGG") or "").strip()
        role = ROLES.get((row.get("SOGG_COD_RUOLO") or "").strip())
        if vat in vats and role:
            links.add((vat, row["COD_LOCALE_PROGETTO"], role))
    stats["links"] = len(links)
    return links


def _beneficiary_counts(soggetti_path: Path, codes):
    beneficiaries = defaultdict(set)
    for row in oc._rows(soggetti_path):
        code = row.get("COD_LOCALE_PROGETTO")
        if code in codes and (row.get("SOGG_COD_RUOLO") or "").strip() == BENEFICIARY_CODE:
            beneficiaries[code].add(row.get("OC_CODICE_FISCALE_SOGG"))
    return {code: len(members) for code, members in beneficiaries.items()}


def _project(row, snapshot, beneficiaries_count):
    return Project(
        code=row["COD_LOCALE_PROGETTO"],
        cup=(row.get("CUP") or "").strip()[:20],
        title=clean_text(row.get("OC_TITOLO_PROGETTO")),
        summary=clean_text(row.get("OC_SINTESI_PROGETTO")),
        theme_code=(row.get("OC_COD_TEMA_SINTETICO") or "").strip()[:2],
        theme=clean_text(row.get("OC_TEMA_SINTETICO"))[:100],
        cycle=clean_text(row.get("OC_DESCR_CICLO"))[:100],
        status=STATUSES.get(clean_text(row.get("OC_STATO_PROGETTO")).lower(), Project.Status.UNKNOWN),
        public_funding=parse_amount(row.get("OC_FINANZ_TOT_PUB_NETTO")),
        eu_funding=parse_amount(row.get("OC_FINANZ_UE_NETTO")),
        payments=parse_amount(row.get("TOT_PAGAMENTI")),
        start_date=parse_date(row.get("OC_DATA_INIZIO_PROGETTO")),
        expected_end_date=parse_date(row.get("OC_DATA_FINE_PROGETTO_PREVISTA")),
        actual_end_date=parse_date(row.get("OC_DATA_FINE_PROGETTO_EFFETTIVA")),
        beneficiaries_count=beneficiaries_count,
        url=(row.get("OC_LINK") or "").strip(),
        snapshot=snapshot,
    )


DATA_FIELDS = [f for f in PROJECT_FIELDS if f != "snapshot"]


def _save_projects(batch, stats):
    existing = {p.code: p for p in Project.objects.filter(code__in=[p.code for p in batch])}
    to_create, to_update = [], []
    for project in batch:
        current = existing.get(project.code)
        if current is None:
            to_create.append(project)
        elif any(getattr(current, f) != getattr(project, f) for f in DATA_FIELDS):
            for field in PROJECT_FIELDS:
                setattr(current, field, getattr(project, field))
            to_update.append(current)
        else:
            stats["projects_unchanged"] += 1
    Project.objects.bulk_create(to_create)
    Project.objects.bulk_update(to_update, PROJECT_FIELDS, batch_size=200)
    stats["projects_created"] += len(to_create)
    stats["projects_updated"] += len(to_update)


def run_import(projects_path, soggetti_path, *, force=False, batch_size=2000, progress=None):
    projects_path, soggetti_path = Path(projects_path), Path(soggetti_path)
    source = oc.get_source()
    checksum = hashlib.sha256(f"{oc._checksum(projects_path)}:{oc._checksum(soggetti_path)}".encode()).hexdigest()

    snapshot = SourceSnapshot.objects.filter(source=source, checksum=checksum).first()
    if snapshot and snapshot.stats.get("complete") and not force:
        return {"already_imported": True, "file": projects_path.name}
    if snapshot is None:
        snapshot = SourceSnapshot.objects.create(
            source=source,
            reference=f"{projects_path.name} + {soggetti_path.name}",
            checksum=checksum,
            data_date=oc._data_date(projects_path),
        )

    stats = Counter()
    vats = set(Company.objects.values_list("vat_number", flat=True))
    links = _links(soggetti_path, vats, stats)
    codes = {code for _, code, _ in links}
    counts = _beneficiary_counts(soggetti_path, codes)

    batch, found = [], set()
    for row in oc._rows(projects_path):
        code = row.get("COD_LOCALE_PROGETTO")
        if code not in codes or code in found:
            continue
        found.add(code)
        batch.append(_project(row, snapshot, counts.get(code, 0)))
        if len(batch) >= batch_size:
            with transaction.atomic():
                _save_projects(batch, stats)
            batch = []
            if progress:
                progress(stats)
    if batch:
        with transaction.atomic():
            _save_projects(batch, stats)
    stats["projects_missing"] = len(codes - found)

    companies = dict(Company.objects.filter(vat_number__in={vat for vat, _, _ in links}).values_list("vat_number", "id"))
    projects = dict(Project.objects.filter(code__in=found).values_list("code", "id"))
    roles = [
        ProjectRole(company_id=companies[vat], project_id=projects[code], role=role)
        for vat, code, role in links
        if code in projects
    ]
    before = ProjectRole.objects.count()
    for start in range(0, len(roles), batch_size):
        with transaction.atomic():
            ProjectRole.objects.bulk_create(roles[start:start + batch_size], ignore_conflicts=True)
    stats["roles_created"] = ProjectRole.objects.count() - before
    stats["projects_removed"] = Project.objects.filter(roles__isnull=True).delete()[1].get("companies.Project", 0)

    summary = dict(stats)
    snapshot.stats = {**summary, "complete": True}
    snapshot.save(update_fields=["stats"])
    return {**summary, "already_imported": False, "file": projects_path.name}
