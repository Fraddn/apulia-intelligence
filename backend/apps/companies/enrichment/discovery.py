import ipaddress
import re
import socket
import threading
import time
import unicodedata
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import date, timedelta

from django.db.models import Q
from django.utils import timezone

from ..models import Assurance, Company, Source, SourceSnapshot, WebsiteCheck, WebsiteDiscovery
from . import websites

TLDS = ("it", "com", "eu")
MAX_CANDIDATES = 12
MAX_LABEL = 63
CONNECT_TIMEOUT = 2
PAGE_TIMEOUT = 6
PARALLEL_DOMAINS = 4
CONFIDENCE = 0.95
RETRY_DAYS = 180
ON_DEMAND_DEADLINE = 25
TIMEOUT = "timeout"
BUSY = "busy"

_slots = threading.BoundedSemaphore(2)

SOURCE = {
    "code": "website_discovery",
    "name": "Website discovery (domain guessed, VAT number verified)",
    "kind": Source.Kind.WEBSITE,
    "url": "",
    "licence": "",
    "attribution": "",
}

LEGAL_WORDS = {
    "srl", "srls", "spa", "snc", "sas", "sapa", "scarl", "scrl", "soc", "societa", "cooperativa", "coop", "consortile",
    "sociale", "unipersonale", "semplificata", "responsabilita", "limitata", "per", "azioni", "nome", "collettivo",
    "accomandita", "semplice", "socio", "unico", "in", "sigla", "di", "e", "ed", "arl", "rl", "onlus",
}
OWNER_PART = re.compile(r"\b(?:s\.?\s?n\.?\s?c|s\.?\s?a\.?\s?s)\b\.?\s+di\b")


@dataclass
class ProbeResult:
    status: str
    url: str = ""
    tried: list = field(default_factory=list)


def name_tokens(name: str) -> list[str]:
    text = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    text = OWNER_PART.split(text)[0]
    return [w for w in re.sub(r"[^a-z0-9]+", " ", text).split() if len(w) > 1 and w not in LEGAL_WORDS]


def candidate_domains(name: str) -> list[str]:
    tokens = name_tokens(name)
    if not tokens:
        return []
    stems = ["".join(tokens), "".join(tokens[:2]), "-".join(tokens[:2]), tokens[0] if len(tokens[0]) >= 5 else ""]
    domains = [f"{stem}.{tld}" for stem in dict.fromkeys(stems) if 4 <= len(stem) <= MAX_LABEL for tld in TLDS]
    return list(dict.fromkeys(domains))[:MAX_CANDIDATES]


def _resolves(domain: str) -> bool:
    """True only for public addresses: some home routers answer every unknown name with 127.0.0.1."""
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(domain, 443)}
    except (OSError, UnicodeError):
        return False
    return any(ipaddress.ip_address(address.split("%")[0]).is_global for address in addresses)


def _listening(host: str, port: int) -> bool:
    try:
        socket.create_connection((host, port), timeout=CONNECT_TIMEOUT).close()
        return True
    except (OSError, UnicodeError):
        return False


def _shows_vat(url: str, html: str, vat: str, robots) -> bool:
    if websites.shows_vat(websites.visible_text(html), vat):
        return True
    for link in websites.candidate_links(html, url)[:2]:
        if not robots.can_fetch(websites.ROBOTS_AGENT, link):
            continue
        try:
            status, page = websites._get(link, timeout=PAGE_TIMEOUT)
        except Exception:
            continue
        if status == 200 and websites.shows_vat(websites.visible_text(page), vat):
            return True
    return False


def _check_domain(domain: str, vat: str) -> str:
    """Return the URL of this domain's site if it shows the VAT number; stop at the first site that answers."""
    if not _resolves(domain):
        return ""
    for scheme, port in (("https", 443), ("http", 80)):
        for host in (f"www.{domain}", domain):
            if not _listening(host, port):
                continue
            url = f"{scheme}://{host}/"
            robots = websites._robots(url, timeout=PAGE_TIMEOUT)
            if not robots.can_fetch(websites.ROBOTS_AGENT, url):
                continue
            try:
                status, html = websites._get(url, timeout=PAGE_TIMEOUT)
            except Exception:
                continue
            if status != 200 or not html:
                continue
            return url if _shows_vat(url, html, vat, robots) else ""
    return ""


def probe(name: str, vat: str, deadline: float | None = None) -> ProbeResult:
    """Network-only: check the guessed domains in parallel and return the first one showing the VAT number."""
    domains = candidate_domains(name)
    if not domains:
        return ProbeResult(WebsiteDiscovery.Status.NO_CANDIDATES)
    ends_at = time.monotonic() + deadline if deadline is not None else None
    pool = ThreadPoolExecutor(max_workers=PARALLEL_DOMAINS)
    pending = {pool.submit(_check_domain, domain, vat) for domain in domains}
    try:
        while pending:
            remaining = None if ends_at is None else ends_at - time.monotonic()
            if remaining is not None and remaining <= 0:
                return ProbeResult(TIMEOUT, "", domains)
            done, pending = wait(pending, timeout=remaining, return_when=FIRST_COMPLETED)
            for future in done:
                if future.result():
                    return ProbeResult(WebsiteDiscovery.Status.FOUND, future.result(), domains)
        return ProbeResult(WebsiteDiscovery.Status.NOT_FOUND, "", domains)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


def save(company: Company, result: ProbeResult) -> WebsiteDiscovery:
    record, _ = WebsiteDiscovery.objects.update_or_create(
        company=company,
        defaults={"status": result.status, "found_url": result.url, "tried": result.tried, "attempted_at": timezone.now()},
    )
    if result.status == WebsiteDiscovery.Status.FOUND and not company.website:
        source, _ = Source.objects.update_or_create(code=SOURCE["code"], defaults=SOURCE)
        snapshot = SourceSnapshot.objects.create(source=source, reference=result.url, data_date=date.today())
        company.website = result.url
        company.save(update_fields=["website", "updated_at"])
        company.record_provenance("website", result.url, snapshot, Assurance.DERIVED, confidence=CONFIDENCE)
    return record


def pending(force: bool = False):
    companies = Company.objects.filter(website="")
    if not force:
        cutoff = timezone.now() - timedelta(days=RETRY_DAYS)
        companies = companies.filter(Q(website_discovery__isnull=True) | Q(website_discovery__attempted_at__lt=cutoff))
    return companies.order_by("id")


def discover_now(company: Company, deadline: float = ON_DEMAND_DEADLINE):
    """On-demand discovery for one company. Returns a WebsiteDiscovery, a transient status dict, or None."""
    if company.website:
        if not WebsiteCheck.objects.filter(company=company).exists():
            websites.fetch(company)
        return None
    record = WebsiteDiscovery.objects.filter(company=company).first()
    if record and timezone.now() - record.attempted_at < timedelta(days=RETRY_DAYS):
        return record
    if not _slots.acquire(blocking=False):
        return {"status": BUSY}
    try:
        result = probe(company.name, company.vat_number, deadline=deadline)
    finally:
        _slots.release()
    if result.status == TIMEOUT:
        return {"status": TIMEOUT}
    record = save(company, result)
    if result.status == WebsiteDiscovery.Status.FOUND:
        websites.fetch(company, force=True)
    return record
