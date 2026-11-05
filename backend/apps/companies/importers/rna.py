import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import transaction

from ..models import Assurance, Company, FieldProvenance, Source, SourceSnapshot, StateAid
from ..text import clean_text
from .opencoesione import _checksum

LISTING_URL = "https://www.incentivitalia.gov.it/rna/rna-open-data/aiuti?page={page}"
FILE_URL = "https://www.incentivitalia.gov.it/open-data/aiuti/{name}"
USER_AGENT = "apulia-intelligence-importer"
REMOTE_NAME = re.compile(r"OpenData_Aiuti_\d{4}_\d{2}(?:_\d{3})?\.zip")
LOCAL_NAME = re.compile(r"rna_aiuti_(\d{4})_(\d{2})(?:_\d{3})?\.zip")
CONTROL_CHARS = bytes(c for c in range(32) if c not in (9, 10, 13))
MAX_PAGES = 60

SOURCE = {
    "code": "rna",
    "name": "Registro Nazionale degli Aiuti di Stato (RNA)",
    "kind": Source.Kind.OPEN_DATA,
    "url": "https://www.incentivitalia.gov.it/rna/rna-open-data/aiuti",
    "licence": "Open data (no licence stated)",
    "attribution": "Fonte: Registro Nazionale degli Aiuti di Stato",
}

SIZES = {"pmi": Company.SizeClass.SME, "grande impresa": Company.SizeClass.LARGE}

AID_FIELDS = [
    "company", "measure_code", "measure_title", "measure_type", "granting_body", "project_title",
    "project_description", "granted_on", "cup", "procedures", "objectives", "instruments", "sector",
    "aid_amount", "nominal_amount", "beneficiary_size", "transparency_url", "snapshot",
]


def get_source():
    source, _ = Source.objects.update_or_create(code=SOURCE["code"], defaults=SOURCE)
    return source


def raw_dir() -> Path:
    path = Path(settings.DATA_DIR) / "raw" / "rna"
    path.mkdir(parents=True, exist_ok=True)
    return path


def local_name(remote: str) -> str:
    return remote.replace("OpenData_Aiuti_", "rna_aiuti_")


def period(name: str):
    match = LOCAL_NAME.fullmatch(name)
    return date(int(match.group(1)), int(match.group(2)), 1) if match else None


def _listing_page(page: int) -> str:
    request = Request(LISTING_URL.format(page=page), headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def discover_files():
    names = set()
    for page in range(MAX_PAGES):
        found = set(REMOTE_NAME.findall(_listing_page(page)))
        if not found - names:
            break
        names |= found
    return sorted(names)


def _fetch(url: str, target: Path):
    tmp = target.with_suffix(".tmp")
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=300) as response, open(tmp, "wb") as out:
        shutil.copyfileobj(response, out)
    tmp.replace(target)


def download_missing(directory: Path, progress=None):
    downloaded = []
    for remote in discover_files():
        target = directory / local_name(remote)
        if target.exists():
            continue
        if progress:
            progress(remote)
        _fetch(FILE_URL.format(name=remote), target)
        downloaded.append(target)
    return downloaded


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def iter_aids(path: Path):
    parser = ET.XMLPullParser(events=("end",))
    with zipfile.ZipFile(path) as archive:
        name = next(n for n in archive.namelist() if n.lower().endswith(".xml"))
        with archive.open(name) as raw:
            for chunk in iter(lambda: raw.read(1 << 20), b""):
                parser.feed(chunk.translate(None, CONTROL_CHARS))
                for _, element in parser.read_events():
                    if _local(element.tag) == "AIUTO":
                        yield element
                        element.clear()


def _text(element, tag):
    for child in element:
        if _local(child.tag) == tag:
            return (child.text or "").strip()
    return ""


def _all_texts(element, tag):
    return [(e.text or "").strip() for e in element.iter() if _local(e.tag) == tag and (e.text or "").strip()]


def _unique(values):
    return "; ".join(dict.fromkeys(values))


def _amount(values):
    total, found = Decimal("0"), False
    for value in values:
        try:
            total += Decimal(value.replace(",", "."))
            found = True
        except InvalidOperation:
            continue
    return total.quantize(Decimal("0.01")) if found else None


def _date(value):
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _aid(element, company_id, snapshot):
    cup = _text(element, "CUP")
    return StateAid(
        cor=_text(element, "COR"),
        company_id=company_id,
        measure_code=_text(element, "CAR")[:30],
        measure_title=clean_text(_text(element, "TITOLO_MISURA")),
        measure_type=clean_text(_text(element, "DES_TIPO_MISURA"))[:100],
        granting_body=clean_text(_text(element, "SOGGETTO_CONCEDENTE"))[:255],
        project_title=clean_text(_text(element, "TITOLO_PROGETTO")),
        project_description=clean_text(_text(element, "DESCRIZIONE_PROGETTO")),
        granted_on=_date(_text(element, "DATA_CONCESSIONE")),
        cup="" if cup.lower() in ("n.d.", "nd", "") else cup[:20],
        procedures=_unique(_all_texts(element, "DES_PROCEDIMENTO"))[:255],
        objectives=_unique(_all_texts(element, "DES_OBIETTIVO")),
        instruments=_unique(_all_texts(element, "DES_STRUMENTO"))[:255],
        sector=_unique(_all_texts(element, "SETTORE_ATTIVITA"))[:50],
        aid_amount=_amount(_all_texts(element, "ELEMENTO_DI_AIUTO")),
        nominal_amount=_amount(_all_texts(element, "IMPORTO_NOMINALE")),
        beneficiary_size=clean_text(_text(element, "DES_TIPO_BENEFICIARIO"))[:50],
        transparency_url=_text(element, "LINK_TRASPARENZA_NAZIONALE")[:1000],
        snapshot=snapshot,
    )


def _save(batch, stats):
    existing = {a.cor: a for a in StateAid.objects.filter(cor__in=[a.cor for a in batch])}
    to_create, to_update = [], []
    for record in batch:
        current = existing.get(record.cor)
        if current is None:
            to_create.append(record)
            existing[record.cor] = record
            continue
        for field in AID_FIELDS:
            setattr(current, field, getattr(record, field))
        to_update.append(current)
    StateAid.objects.bulk_create(to_create)
    StateAid.objects.bulk_update(to_update, AID_FIELDS, batch_size=200)
    stats["created"] += len(to_create)
    stats["updated"] += len(to_update)


def _update_sizes(company_ids, stats):
    owners = {}
    for company_id, source_code in (
        FieldProvenance.objects.filter(company_id__in=company_ids, field="size_class")
        .order_by("company_id", "-collected_at", "-id")
        .values_list("company_id", "snapshot__source__code")
    ):
        owners.setdefault(company_id, source_code)
    for company in Company.objects.filter(id__in=company_ids):
        owned_by_rna = owners.get(company.id) == SOURCE["code"]
        if company.size_class != Company.SizeClass.UNKNOWN and not owned_by_rna:
            continue
        latest = next(
            (
                aid for aid in company.aids.order_by("-granted_on", "-id").only("beneficiary_size", "snapshot")
                if aid.beneficiary_size.lower() in SIZES
            ),
            None,
        )
        if latest is None:
            continue
        size = SIZES[latest.beneficiary_size.lower()]
        if company.size_class != size:
            company.size_class = size
            company.save(update_fields=["size_class", "updated_at"])
            stats["sizes_set"] += 1
        company.record_provenance("size_class", latest.beneficiary_size, latest.snapshot, Assurance.OFFICIAL)


def import_file(path, *, force=False, batch_size=2000):
    path = Path(path)
    source = get_source()
    checksum = _checksum(path)
    snapshot = SourceSnapshot.objects.filter(source=source, checksum=checksum).first()
    if snapshot and snapshot.stats.get("complete") and not force:
        return {"already_imported": True, "file": path.name}
    if snapshot is None:
        snapshot = SourceSnapshot.objects.create(
            source=source, reference=path.name, checksum=checksum, data_date=period(path.name)
        )

    stats = Counter()
    companies = dict(Company.objects.values_list("vat_number", "id"))
    touched, batch = set(), []
    for element in iter_aids(path):
        stats["records"] += 1
        company_id = companies.get(_text(element, "CODICE_FISCALE_BENEFICIARIO"))
        cor = _text(element, "COR")
        if company_id is None or not cor:
            continue
        batch.append(_aid(element, company_id, snapshot))
        touched.add(company_id)
        if len(batch) >= batch_size:
            with transaction.atomic():
                _save(batch, stats)
            batch = []
    with transaction.atomic():
        if batch:
            _save(batch, stats)
        _update_sizes(touched, stats)

    stats["companies"] = len(touched)
    summary = dict(stats)
    snapshot.stats = {**summary, "complete": True}
    snapshot.save(update_fields=["stats"])
    return {**summary, "already_imported": False, "file": path.name}


def local_files(directory: Path):
    return sorted(p for p in directory.glob("rna_aiuti_*.zip") if LOCAL_NAME.fullmatch(p.name))
