import csv
import hashlib
import io
import re
import shutil
import zipfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import transaction

from ..ateco import normalize_ateco
from ..models import Assurance, Company, FieldProvenance, Source, SourceSnapshot
from ..provinces import ISTAT_PROVINCE_CODES, PUGLIA_REGION_CODE
from ..text import clean_text
from ..vat import is_valid_vat, province_from_vat

DOWNLOAD_URL = "https://opencoesione.gov.it/it/opendata/soggetti.zip"
FILE_PREFIX = "opencoesione_soggetti_"
VAT_PROVINCE_CONFIDENCE = 0.7

# ISTAT legal forms: partnerships, limited companies, cooperatives, consortia, foreign companies.
BUSINESS_LEGAL_FORMS = ("1.2.", "1.3.", "1.4.", "1.5.", "1.9.")

SOURCE = {
    "code": "opencoesione",
    "name": "OpenCoesione",
    "kind": Source.Kind.OPEN_DATA,
    "url": "https://opencoesione.gov.it/it/opendata/",
    "licence": "CC BY 4.0",
    "attribution": "Fonte: OpenCoesione",
}

SIZES = {
    "microimpresa": Company.SizeClass.MICRO,
    "piccola impresa": Company.SizeClass.SMALL,
    "media impresa": Company.SizeClass.MEDIUM,
    "grande impresa": Company.SizeClass.LARGE,
}

FIRST_VALUE_COLUMNS = [
    "OC_DENOMINAZIONE_SOGG", "COD_FORMA_GIURIDICA_SOGG", "DESCR_FORMA_GIURIDICA_SOGG",
    "INDIRIZZO_SOGG", "CAP_SOGG", "COD_ATECO_SOGG", "DESCRIZIONE_ATECO_SOGG",
    "DESCR_ADDETTI_SOGG", "DESCR_DIMENSIONE_SOGG",
]

EMPTY_VALUES = {"", Company.SizeClass.UNKNOWN, Company.Status.UNKNOWN}


def get_source():
    source, _ = Source.objects.update_or_create(code=SOURCE["code"], defaults=SOURCE)
    return source


def latest_file(raw_dir: Path):
    files = sorted(raw_dir.glob(f"{FILE_PREFIX}*.zip"))
    return files[-1] if files else None


def raw_dir() -> Path:
    path = Path(settings.DATA_DIR) / "raw"
    path.mkdir(parents=True, exist_ok=True)
    return path


def download(directory: Path) -> Path:
    tmp = directory / f".{FILE_PREFIX}download.tmp"
    request = Request(DOWNLOAD_URL, headers={"User-Agent": "apulia-intelligence-importer"})
    with urlopen(request, timeout=120) as response, open(tmp, "wb") as out:
        shutil.copyfileobj(response, out)
    data_date = _data_date(tmp)
    stamp = data_date.strftime("%Y%m%d") if data_date else date.today().strftime("%Y%m%d")
    target = directory / f"{FILE_PREFIX}{stamp}.zip"
    tmp.replace(target)
    return target


def _csv_name(archive: zipfile.ZipFile) -> str:
    names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
    if not names:
        raise ValueError("No CSV file found in archive")
    return names[0]


def _data_date(path: Path):
    with zipfile.ZipFile(path) as archive:
        match = re.search(r"(\d{8})", _csv_name(archive))
    if not match:
        return None
    value = match.group(1)
    return date(int(value[:4]), int(value[4:6]), int(value[6:]))


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rows(path: Path):
    csv.field_size_limit(10**8)
    with zipfile.ZipFile(path) as archive, archive.open(_csv_name(archive)) as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8", errors="replace", newline="")
        yield from csv.DictReader(text, delimiter=";")


def _collect(path: Path, stats):
    """Group rows by VAT number, keeping candidate Puglia businesses only."""
    companies = {}
    comuni = defaultdict(Counter)
    projects = defaultdict(set)
    skipped = stats["skipped_rows"]

    for row in _rows(path):
        stats["rows_read"] += 1
        vat = (row.get("OC_CODICE_FISCALE_SOGG") or "").strip()
        if len(vat) != 11 or not vat.isdigit():
            skipped["not_company_code"] += 1
            continue
        if not (row.get("COD_FORMA_GIURIDICA_SOGG") or "").startswith(BUSINESS_LEGAL_FORMS):
            skipped["not_business"] += 1
            continue
        if not is_valid_vat(vat):
            skipped["invalid_vat"] += 1
            continue
        comune = (row.get("COD_COMUNE_SEDE_SOGG") or "").strip()
        if not comune.startswith(PUGLIA_REGION_CODE) and province_from_vat(vat) is None:
            skipped["outside_puglia"] += 1
            continue

        stats["rows_matched"] += 1
        record = companies.setdefault(vat, {})
        for column in FIRST_VALUE_COLUMNS:
            value = (row.get(column) or "").strip()
            if value and not record.get(column):
                record[column] = value
        if comune:
            comuni[vat][comune] += 1
        projects[vat].add(row.get("COD_LOCALE_PROGETTO"))

    for vat, record in companies.items():
        record["comune"] = comuni[vat].most_common(1)[0][0] if comuni[vat] else ""
    return companies, {vat: len(p) for vat, p in projects.items()}


def _fields(vat, record, stats):
    """Map one aggregated record to {field: (value, raw, assurance, confidence)}, or None to exclude."""
    official = Assurance.OFFICIAL
    name = clean_text(record.get("OC_DENOMINAZIONE_SOGG"))
    if not name or name == vat:
        stats["excluded_companies"]["no_name"] += 1
        return None
    comune = record["comune"]
    fields = {}

    if comune:
        if not comune.startswith(PUGLIA_REGION_CODE):
            stats["excluded_companies"]["registered_outside_puglia"] += 1
            return None
        province = ISTAT_PROVINCE_CODES.get(comune[3:6])
        if province is None:
            stats["excluded_companies"]["unknown_province"] += 1
            return None
        fields["province"] = (province, comune, official, None)
        fields["municipality_code"] = (comune[3:], comune, official, None)
    else:
        fields["province"] = (province_from_vat(vat), vat, Assurance.DERIVED, VAT_PROVINCE_CONFIDENCE)

    def text(field, column):
        raw = record.get(column, "")
        fields[field] = (clean_text(raw), raw, official, None)

    fields["tax_code"] = (vat, vat, official, None)
    text("name", "OC_DENOMINAZIONE_SOGG")
    text("legal_form_code", "COD_FORMA_GIURIDICA_SOGG")
    text("legal_form", "DESCR_FORMA_GIURIDICA_SOGG")
    text("address", "INDIRIZZO_SOGG")
    text("postcode", "CAP_SOGG")
    text("ateco_description", "DESCRIZIONE_ATECO_SOGG")
    text("employees_band", "DESCR_ADDETTI_SOGG")

    raw_size = record.get("DESCR_DIMENSIONE_SOGG", "")
    size = SIZES.get(clean_text(raw_size).lower(), "")
    fields["size_class"] = (size, raw_size, official, None)

    raw_ateco = record.get("COD_ATECO_SOGG", "")
    ateco = normalize_ateco(raw_ateco)
    if raw_ateco and ateco is None:
        stats["ateco"]["unparsed"] += 1
    elif ateco:
        if ateco.version not in ("2007", "2022"):
            stats["ateco"][f"version_{ateco.version}"] += 1
        fields["ateco_section"] = (ateco.section, raw_ateco, official, None)
        fields["ateco_code"] = (ateco.code, raw_ateco, official, None)
        fields["ateco_version"] = (ateco.version, raw_ateco, official, None)

    return {k: v for k, v in fields.items() if v[0]}


def _owners(company_ids):
    """Source code of the latest provenance per (company, field)."""
    owners = {}
    rows = (
        FieldProvenance.objects.filter(company_id__in=company_ids)
        .order_by("company_id", "field", "-collected_at", "-id")
        .values_list("company_id", "field", "snapshot__source__code")
    )
    for company_id, field, source_code in rows:
        owners.setdefault((company_id, field), source_code)
    return owners


def _save_batch(batch, snapshot, stats):
    existing = {c.vat_number: c for c in Company.objects.filter(vat_number__in=[vat for vat, _ in batch])}
    owners = _owners([c.id for c in existing.values()])
    to_create, to_update, accepted = [], [], {}

    for vat, fields in batch:
        company = existing.get(vat)
        if company is None:
            company = Company(vat_number=vat, **{f: v[0] for f, v in fields.items()})
            to_create.append(company)
            accepted[vat] = fields
            stats["created"] += 1
            continue

        changed, kept = [], {}
        for field, entry in fields.items():
            current = getattr(company, field)
            owner = owners.get((company.id, field))
            if owner not in (None, SOURCE["code"]) and current not in EMPTY_VALUES:
                continue
            kept[field] = entry
            if current != entry[0]:
                setattr(company, field, entry[0])
                changed.append(field)
        accepted[vat] = kept
        if changed:
            to_update.append((company, changed))
            stats["updated"] += 1
        else:
            stats["unchanged"] += 1

    Company.objects.bulk_create(to_create)
    for company, changed in to_update:
        company.save(update_fields=[*changed, "updated_at"])

    by_vat = {c.vat_number: c for c in [*to_create, *existing.values()]}
    FieldProvenance.objects.bulk_create(
        [
            FieldProvenance(
                company=by_vat[vat], field=field, raw_value=raw, snapshot=snapshot,
                assurance=assurance, confidence=confidence,
            )
            for vat, fields in accepted.items()
            for field, (_, raw, assurance, confidence) in fields.items()
        ],
        ignore_conflicts=True,
    )


def _new_stats():
    return {
        "rows_read": 0,
        "rows_matched": 0,
        "companies_found": 0,
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped_rows": Counter(),
        "excluded_companies": Counter(),
        "ateco": Counter(),
    }


def run_import(path, *, force=False, batch_size=1000, progress=None):
    path = Path(path)
    source = get_source()
    checksum = _checksum(path)

    snapshot = SourceSnapshot.objects.filter(source=source, checksum=checksum).first()
    if snapshot and snapshot.stats.get("complete") and not force:
        return {"already_imported": True, "snapshot": snapshot.pk, "file": path.name}
    if snapshot is None:
        snapshot = SourceSnapshot.objects.create(
            source=source, reference=path.name, checksum=checksum, data_date=_data_date(path)
        )

    stats = _new_stats()
    companies, projects = _collect(path, stats)

    batch = []
    for vat, record in companies.items():
        fields = _fields(vat, record, stats)
        if fields is None:
            continue
        stats["companies_found"] += 1
        batch.append((vat, fields))
        if len(batch) >= batch_size:
            with transaction.atomic():
                _save_batch(batch, snapshot, stats)
            batch = []
            if progress:
                progress(stats)
    if batch:
        with transaction.atomic():
            _save_batch(batch, snapshot, stats)

    summary = {k: dict(v) if isinstance(v, Counter) else v for k, v in stats.items()}
    snapshot.stats = {**summary, "complete": True}
    snapshot.save(update_fields=["stats"])
    return {**summary, "already_imported": False, "file": path.name, "projects": projects}
