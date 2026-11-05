import csv
import io
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import transaction

from ..models import Assurance, Company, FieldProvenance, Municipality, Source, SourceSnapshot

DOWNLOAD_URL = "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv"
FILE_PREFIX = "istat_comuni_"

SOURCE = {
    "code": "istat",
    "name": "ISTAT – Elenco dei comuni italiani",
    "kind": Source.Kind.OPEN_DATA,
    "url": "https://www.istat.it/classificazione/codici-dei-comuni-delle-province-e-delle-regioni/",
    "licence": "CC BY",
    "attribution": "Fonte: ISTAT",
}

POSTCODE_PROVINCES = {"70": "BA", "71": "FG", "72": "BR", "73": "LE", "74": "TA", "76": "BT"}

COLUMNS = {
    "code": "Codice Comune formato alfanumerico",
    "name": "Denominazione in italiano",
    "province": "Sigla automobilistica",
    "region_code": "Codice Regione",
}


def raw_dir() -> Path:
    path = Path(settings.DATA_DIR) / "raw" / "istat"
    path.mkdir(parents=True, exist_ok=True)
    return path


def latest_file(directory: Path):
    files = sorted(directory.glob(f"{FILE_PREFIX}*.csv"))
    return files[-1] if files else None


def download(directory: Path) -> Path:
    request = Request(DOWNLOAD_URL, headers={"User-Agent": "apulia-intelligence-importer"})
    with urlopen(request, timeout=60) as response:
        content = response.read()
    target = directory / f"{FILE_PREFIX}{date.today():%Y%m%d}.csv"
    target.write_bytes(content)
    return target


def get_source():
    source, _ = Source.objects.update_or_create(code=SOURCE["code"], defaults=SOURCE)
    return source


def _rows(path: Path):
    text = path.read_bytes().decode("latin-1")
    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter=";")
    reader.fieldnames = [" ".join(name.split()) for name in reader.fieldnames]
    for row in reader:
        yield {key: (row.get(column) or "").strip() for key, column in COLUMNS.items()}


def import_municipalities(path) -> dict:
    path = Path(path)
    existing = {m.code: m for m in Municipality.objects.all()}
    to_create, to_update = [], []
    for row in _rows(path):
        if len(row["code"]) != 6:
            continue
        current = existing.get(row["code"])
        if current is None:
            to_create.append(Municipality(**row))
        elif (current.name, current.province, current.region_code) != (row["name"], row["province"], row["region_code"]):
            current.name, current.province, current.region_code = row["name"], row["province"], row["region_code"]
            to_update.append(current)
    with transaction.atomic():
        Municipality.objects.bulk_create(to_create)
        Municipality.objects.bulk_update(to_update, ["name", "province", "region_code"], batch_size=500)
    return {"municipalities": Municipality.objects.count(), "created": len(to_create), "updated": len(to_update)}


def fill_cities() -> dict:
    stats = Counter()
    municipalities = {code: (name, province) for code, name, province in Municipality.objects.values_list("code", "name", "province")}
    if not municipalities:
        return dict(stats)
    candidates = Company.objects.exclude(municipality_code="")
    owners = {}
    for company_id, code in (
        FieldProvenance.objects.filter(field="city", company__in=candidates)
        .order_by("company_id", "-collected_at", "-id")
        .values_list("company_id", "snapshot__source__code")
    ):
        owners.setdefault(company_id, code)

    snapshot = None
    with transaction.atomic():
        for company in candidates.only("id", "municipality_code", "city", "postcode"):
            if company.municipality_code not in municipalities:
                stats["unknown_code"] += 1
                continue
            name, province = municipalities[company.municipality_code]
            postcode_province = POSTCODE_PROVINCES.get(company.postcode[:2]) if company.postcode else None
            if postcode_province and postcode_province != province:
                stats["postcode_conflict"] += 1
                if company.city and owners.get(company.id) == SOURCE["code"]:
                    company.city = ""
                    company.save(update_fields=["city", "updated_at"])
                    stats["cleared"] += 1
                continue
            if company.city and owners.get(company.id) != SOURCE["code"]:
                continue
            if company.city == name:
                continue
            if snapshot is None:
                snapshot = SourceSnapshot.objects.create(source=get_source(), reference="municipality code → name", data_date=date.today())
            company.city = name
            company.save(update_fields=["city", "updated_at"])
            company.record_provenance("city", company.municipality_code, snapshot, Assurance.DERIVED)
            stats["filled"] += 1
    return {key: stats[key] for key in ("filled", "unknown_code", "postcode_conflict", "cleared")}
