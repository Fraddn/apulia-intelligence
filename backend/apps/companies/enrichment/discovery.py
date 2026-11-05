import re
import socket
import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta

from django.db.models import Q
from django.utils import timezone

from ..models import Assurance, Company, Source, SourceSnapshot, WebsiteDiscovery
from . import websites

TLDS = ("it", "com", "eu")
MAX_CANDIDATES = 12
CONFIDENCE = 0.95
RETRY_DAYS = 180

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
    domains = [f"{stem}.{tld}" for stem in dict.fromkeys(stems) if len(stem) >= 4 for tld in TLDS]
    return list(dict.fromkeys(domains))[:MAX_CANDIDATES]


def _resolves(domain: str) -> bool:
    try:
        socket.getaddrinfo(domain, 443)
        return True
    except OSError:
        return False


def _shows_vat(url: str, html: str, vat: str, robots) -> bool:
    if websites.shows_vat(websites.visible_text(html), vat):
        return True
    for link in websites.candidate_links(html, url)[:2]:
        if not robots.can_fetch(websites.ROBOTS_AGENT, link):
            continue
        try:
            status, page = websites._get(link)
        except Exception:
            continue
        if status == 200 and websites.shows_vat(websites.visible_text(page), vat):
            return True
    return False


def probe(name: str, vat: str) -> ProbeResult:
    """Network-only: guess domains for a company and return the first one showing its VAT number."""
    domains = candidate_domains(name)
    if not domains:
        return ProbeResult(WebsiteDiscovery.Status.NO_CANDIDATES)
    for domain in (d for d in domains if _resolves(d)):
        for url in (f"https://www.{domain}/", f"https://{domain}/"):
            robots = websites._robots(url)
            if not robots.can_fetch(websites.ROBOTS_AGENT, url):
                continue
            try:
                status, html = websites._get(url)
            except Exception:
                continue
            if status != 200 or not html:
                continue
            if _shows_vat(url, html, vat, robots):
                return ProbeResult(WebsiteDiscovery.Status.FOUND, url, domains)
            break
    return ProbeResult(WebsiteDiscovery.Status.NOT_FOUND, "", domains)


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
