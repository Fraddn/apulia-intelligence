import re
from datetime import date, timedelta
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

from django.db import transaction
from django.utils import timezone

from ..models import Assurance, Company, FieldProvenance, Source, SourceSnapshot, WebsiteCheck, WebsitePage

USER_AGENT = "apulia-intelligence/1.0 (Puglia Imprese; reads company contact pages)"
ROBOTS_AGENT = "apulia-intelligence"
MAX_PAGES = 5
MAX_BYTES = 2_000_000
REFRESH_DAYS = 90

SOURCE = {
    "code": "company_website",
    "name": "Company website",
    "kind": Source.Kind.WEBSITE,
    "url": "",
    "licence": "",
    "attribution": "Company website",
}

LINK_KEYWORDS = [
    ("contatti", "contattaci", "contatto", "contact", "contacts", "contact-us", "contattaci", "dove-siamo"),
    ("chi-siamo", "chisiamo", "chi siamo", "about", "about-us", "azienda", "l-azienda", "la-societa", "company", "profilo"),
    ("note-legali", "note legali", "legal", "legal-notes", "impressum", "dati-societari", "dati societari"),
    ("privacy", "privacy-policy", "privacy policy"),
]
_LINK_PATTERNS = [
    re.compile(r"(?:^|[/\s_.])(" + "|".join(re.escape(w) for w in words) + r")(?=$|[/\s_.?])") for words in LINK_KEYWORDS
]

GENERIC_MAILBOXES = {
    "info", "informazioni", "amministrazione", "commerciale", "segreteria", "contatti", "contact", "contacts",
    "sales", "office", "ufficio", "vendite", "ordini", "hello", "mail", "posta", "booking", "prenotazioni",
    "reception", "direzione", "marketing", "support", "assistenza", "servizioclienti", "customercare",
    "acquisti", "export", "tecnico", "qualita", "admin",
}
PEC_DOMAINS = ("pec.", "legalmail.", "postecert.", "arubapec.", "postacert.", "cert.", ".pec.")

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
VAT_CANDIDATE = re.compile(r"(?<![\d])(?:IT\s?)?(\d[\d .]{9,20}\d)(?![\d])")
PHONE_LABELLED = re.compile(
    r"(?:Tel(?:efono)?|Phone|Ph|Cell(?:ulare)?)\.?\s*:?\s*((?:\+39\s?)?(?:0\d{1,4}|3\d{2})[\s./-]?\d{3,8}(?:[\s./-]?\d{2,4})?)",
    re.IGNORECASE,
)
ADDRESS = re.compile(
    r"((?:Via|Viale|V\.le|Piazza|P\.zza|Piazzale|Corso|C\.so|Largo|Strada|Contrada|C\.da|Vico|Vicolo|Lungomare|"
    r"Traversa|Zona Industriale|Z\.I\.)\s[^,\n\d]{2,60}?,?\s*\d{1,4}[A-Za-z]?)"
    r"\s*[,–-]?\s*(7[0-46]\d{3})\s+([A-ZÀ-Ý][A-Za-zà-ÿ'. ]{1,60})"
)
CITY_STOPWORDS = {
    "c", "cf", "cap", "capitale", "soc", "p", "piva", "iva", "partita", "tel", "telefono", "fax", "email", "mail",
    "pec", "codice", "reg", "rea", "iscr", "iscritta", "n", "numero", "sede", "www", "italy", "italia",
}


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "template", "svg"}

    def __init__(self):
        super().__init__()
        self.parts, self.links, self._skip, self._in_link = [], [], 0, False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        if tag == "a":
            self.links.append([dict(attrs).get("href") or "", ""])
            self._in_link = True

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        if tag == "a":
            self._in_link = False

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)
            if self._in_link and self.links:
                self.links[-1][1] += data


def _parse(html: str) -> _TextExtractor:
    parser = _TextExtractor()
    parser.feed(html or "")
    return parser


def visible_text(html: str) -> str:
    return re.sub(r"\s+", " ", " ".join(_parse(html).parts)).strip()


def normalize_url(value: str) -> str:
    value = (value or "").strip()
    if not value or " " in value:
        return ""
    if not re.match(r"^https?://", value, re.I):
        value = f"https://{value}"
    parsed = urlparse(value)
    if "." not in parsed.netloc:
        return ""
    return parsed._replace(path=parsed.path or "/").geturl()


def shows_vat(text: str, vat: str) -> bool:
    return any(re.sub(r"\D", "", m.group(1)) == vat for m in VAT_CANDIDATE.finditer(text or ""))


def _host(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def candidate_links(html: str, base: str) -> list[str]:
    ranked = []
    for href, label in _parse(html).links:
        if not href or href.startswith(("mailto:", "tel:", "#", "javascript:")):
            continue
        url = urljoin(base, href).split("#")[0]
        if _host(url) != _host(base) or url.rstrip("/") == base.rstrip("/"):
            continue
        haystack = f"{urlparse(url).path} {label.strip()}".lower()
        rank = next((i for i, pattern in enumerate(_LINK_PATTERNS) if pattern.search(haystack)), None)
        if rank is not None:
            ranked.append((rank, url))
    seen, result = set(), []
    for _, url in sorted(ranked, key=lambda pair: pair[0]):
        if url not in seen:
            seen.add(url)
            result.append(url)
    return result


def _emails(text: str, html: str) -> list[str]:
    found = EMAIL.findall(text or "") + [m.split("?")[0] for m in re.findall(r'href=["\']mailto:([^"\']+)', html or "", re.I)]
    return list(dict.fromkeys(e.strip(".").lower() for e in found))


def _is_pec(email: str) -> bool:
    domain = email.split("@", 1)[1]
    return domain.startswith(PEC_DOMAINS) or any(d in domain for d in (".pec.", "legalmail", "postecert", "arubapec"))


def generic_email(text: str, html: str) -> str:
    for email in _emails(text, html):
        if not _is_pec(email) and email.split("@", 1)[0] in GENERIC_MAILBOXES:
            return email
    return ""


def pec(text: str) -> str:
    return next((e for e in _emails(text, "") if _is_pec(e)), "")


def phone(text: str, html: str) -> str:
    for link in re.findall(r'href=["\']tel:([^"\']+)', html or "", re.I):
        digits = re.sub(r"[^\d+]", "", link)
        if digits.startswith("+39"):
            return f"+39 {digits[3:]}"
        if digits:
            return digits
    match = PHONE_LABELLED.search(text or "")
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""


def _city(raw: str) -> str:
    words = []
    for word in raw.split():
        key = word.lower().replace(".", "")
        if key in CITY_STOPWORDS or len(key) < 2 and words:
            break
        words.append(word.strip("."))
    city = " ".join(w for w in words if w)
    return city.title() if city.isupper() else city


def address(text: str) -> dict:
    match = ADDRESS.search(text or "")
    if not match:
        return {}
    city = _city(match.group(3))
    if not city:
        return {}
    return {
        "address": re.sub(r"\s+", " ", match.group(1)).strip(),
        "postcode": match.group(2),
        "city": city,
    }


def _get(url: str, timeout: float = 15):
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain;q=0.9,*/*;q=0.5"})
    with urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        if "html" not in content_type and "text" not in content_type:
            return response.status, ""
        charset = response.headers.get_content_charset() or "utf-8"
        return response.status, response.read(MAX_BYTES).decode(charset, errors="replace")


def _robots(base: str, timeout: float = 15) -> RobotFileParser:
    parser = RobotFileParser()
    try:
        status, body = _get(urljoin(base, "/robots.txt"), timeout=timeout)
    except Exception:
        status, body = 404, ""
    parser.parse(body.splitlines() if status == 200 else [])
    return parser


def _owners(company: Company, fields) -> dict:
    owners = {}
    for field, code in (
        FieldProvenance.objects.filter(company=company, field__in=fields)
        .order_by("field", "-collected_at", "-id")
        .values_list("field", "snapshot__source__code")
    ):
        owners.setdefault(field, code)
    return owners


def _extract(pages) -> dict:
    """Return {field: (value, page_url)} from the first page that has each value."""
    found = {}
    for url, html, text in pages:
        candidates = {**address(text), "phone": phone(text, html), "email": generic_email(text, html), "pec": pec(text)}
        for field, value in candidates.items():
            if value and field not in found:
                found[field] = (value, url)
    return found


ADDRESS_FIELDS = ("address", "postcode", "city")


def _apply(company: Company, found: dict):
    source, _ = Source.objects.update_or_create(code=SOURCE["code"], defaults=SOURCE)
    owners = _owners(company, [*found, *ADDRESS_FIELDS])
    snapshots, changed = {}, []
    address_taken = any(
        getattr(company, field) and owners.get(field) != SOURCE["code"] for field in ADDRESS_FIELDS
    )
    if address_taken:
        for field in ADDRESS_FIELDS:
            found.pop(field, None)
            if getattr(company, field) and owners.get(field) == SOURCE["code"]:
                setattr(company, field, "")
                changed.append(field)
    for field, (value, url) in found.items():
        current = getattr(company, field)
        if current and owners.get(field) != SOURCE["code"]:
            continue
        if url not in snapshots:
            snapshots[url] = SourceSnapshot.objects.create(source=source, reference=url, data_date=date.today())
        if current != value:
            setattr(company, field, value)
            changed.append(field)
        company.record_provenance(field, value, snapshots[url], Assurance.COMPANY)
    if changed:
        company.save(update_fields=[*changed, "updated_at"])


def _save_check(company, url, status, pages=0, error=""):
    check, _ = WebsiteCheck.objects.update_or_create(
        company=company,
        defaults={"url": url, "status": status, "pages": pages, "error": error[:255], "checked_at": timezone.now()},
    )
    return check


def fetch(company: Company, force: bool = False) -> WebsiteCheck:
    existing = WebsiteCheck.objects.filter(company=company).first()
    if existing and not force and timezone.now() - existing.checked_at < timedelta(days=REFRESH_DAYS):
        return existing

    url = normalize_url(company.website)
    if not url:
        return _save_check(company, "", WebsiteCheck.Status.NO_WEBSITE)
    try:
        robots = _robots(url)
        if not robots.can_fetch(ROBOTS_AGENT, url):
            return _save_check(company, url, WebsiteCheck.Status.BLOCKED)
        status, home = _get(url)
        if status != 200 or not home:
            return _save_check(company, url, WebsiteCheck.Status.UNREACHABLE, error=f"HTTP {status}")
        pages = [(url, home)]
        for link in candidate_links(home, url)[: MAX_PAGES - 1]:
            if not robots.can_fetch(ROBOTS_AGENT, link):
                continue
            try:
                link_status, html = _get(link)
            except Exception:
                continue
            if link_status == 200 and html:
                pages.append((link, html))
    except Exception as error:
        return _save_check(company, url, WebsiteCheck.Status.UNREACHABLE, error=str(error))

    now = timezone.now()
    parsed = [(page_url, html, visible_text(html)) for page_url, html in pages]
    verified = False
    with transaction.atomic():
        WebsitePage.objects.filter(company=company).exclude(url__in=[p[0] for p in parsed]).delete()
        for page_url, _, text in parsed:
            found = shows_vat(text, company.vat_number)
            verified = verified or found
            WebsitePage.objects.update_or_create(
                company=company, url=page_url,
                defaults={"status_code": 200, "text": text, "vat_found": found, "fetched_at": now},
            )
        if verified:
            _apply(company, _extract(parsed))
        status = WebsiteCheck.Status.VERIFIED if verified else WebsiteCheck.Status.VAT_NOT_FOUND
        return _save_check(company, url, status, pages=len(parsed))
