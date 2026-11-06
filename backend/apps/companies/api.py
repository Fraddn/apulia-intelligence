from datetime import date, datetime
from typing import Literal

from django.core.cache import cache
from django.db.models import Case, Count, Exists, F, IntegerField, Max, OuterRef, Q, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from ninja import Field, FilterSchema, Query, Router, Schema
from ninja.pagination import PageNumberPagination, paginate

from .enrichment import discovery
from .models import Company, FieldProvenance, Project, ProjectRole, Source, SourceSnapshot, StateAid

router = Router(tags=["companies"])

PROJECTS_LIMIT = 50
AID_LIMIT = 50

ProvinceCode = Literal["BA", "BT", "BR", "FG", "LE", "TA"]
SectionCode = Literal[
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U"
]


class CompanyListOut(Schema):
    vat_number: str
    name: str
    province: str
    city: str
    ateco_section: str
    ateco_code: str
    size_class: str


class CompanyListItemOut(CompanyListOut):
    beneficiary_projects: int
    sole_beneficiary_funding: float | None


class SourceOut(Schema):
    name: str
    url: str
    licence: str
    attribution: str


class ProvenanceOut(Schema):
    field: str
    raw_value: str
    assurance: str
    confidence: float | None
    source: SourceOut
    reference: str
    data_date: date | None
    collected_at: datetime


class FundingOut(Schema):
    beneficiary_projects: int
    sole_beneficiary_projects: int
    shared_projects: int
    sole_beneficiary_funding: float | None
    roles: dict[str, int]


class ProjectOut(Schema):
    code: str
    title: str
    summary: str
    theme_code: str
    theme: str
    cycle: str
    status: str
    role: str
    public_funding: float | None
    beneficiaries_count: int
    start_date: date | None
    expected_end_date: date | None
    actual_end_date: date | None
    url: str


class StateAidOut(Schema):
    cor: str
    granted_on: date | None
    measure_title: str
    granting_body: str
    project_title: str
    objectives: str
    procedures: str
    instruments: str
    aid_amount: float | None
    transparency_url: str


class CompanyAidOut(Schema):
    count: int
    total_amount: float | None
    latest_date: date | None
    items: list[StateAidOut]


class WebsiteCheckOut(Schema):
    url: str
    status: str
    pages: int
    checked_at: datetime


class CompanyDetailOut(CompanyListOut):
    tax_code: str
    legal_form_code: str
    legal_form: str
    ateco_description: str
    ateco_version: str
    municipality_code: str
    address: str
    postcode: str
    website: str
    phone: str
    email: str
    pec: str
    latitude: float | None
    longitude: float | None
    status: str
    employees_band: str
    founded_on: date | None
    profile_level: str
    provenance: list[ProvenanceOut]
    funding: FundingOut
    projects: list[ProjectOut]
    projects_total: int
    aid: CompanyAidOut
    website_check: WebsiteCheckOut | None


class DiscoveryOut(Schema):
    status: str
    found_url: str = ""
    attempted_at: datetime | None = None


class DiscoverResultOut(Schema):
    discovery: DiscoveryOut | None
    company: CompanyDetailOut


SizeOption = Literal["micro", "small", "medium", "sme", "large", "unknown"]
SME_CLASSES = ["micro", "small", "medium", "sme"]


class CompanyFilters(FilterSchema):
    search: str | None = None
    province: ProvinceCode | None = None
    section: str | None = None
    division: str | None = Field(None, pattern=r"^\d{2}$")
    ateco: str | None = None
    funded: bool | None = None
    theme: str | None = Field(None, pattern=r"^\d{2}$")
    size: SizeOption | None = None
    min_projects: int | None = Field(None, ge=1)
    min_funding: int | None = Field(None, ge=1)

    def filter_size(self, value):
        if not value:
            return Q()
        if value == Company.SizeClass.SME:
            return Q(size_class__in=SME_CLASSES)
        return Q(size_class=value)

    def filter_min_projects(self, value):
        return Q(beneficiary_projects__gte=value) if value else Q()

    def filter_min_funding(self, value):
        return Q(sole_beneficiary_funding__gte=value) if value else Q()

    def filter_search(self, value):
        return Q(name__icontains=value) | Q(vat_number__startswith=value) if value else Q()

    def filter_section(self, value):
        return Q(ateco_section=value.upper()) if value else Q()

    def filter_ateco(self, value):
        return Q(ateco_code__startswith=value) if value else Q()

    def filter_division(self, value):
        return Q(ateco_code__startswith=value) if value else Q()

    def filter_funded(self, value):
        return Q(Exists(_beneficiary_roles())) if value else Q()

    def filter_theme(self, value):
        return Q(Exists(_beneficiary_roles().filter(project__theme_code=value))) if value else Q()


SortOption = Literal["name", "funding", "projects"]


def _beneficiary_roles():
    return ProjectRole.objects.filter(company=OuterRef("pk"), role=ProjectRole.Role.BENEFICIARY)


def _with_funding(queryset):
    count = _beneficiary_roles().values("company").annotate(n=Count("id")).values("n")
    total = (
        _beneficiary_roles().filter(project__beneficiaries_count=1)
        .values("company").annotate(total=Sum("project__public_funding")).values("total")
    )
    return queryset.annotate(
        beneficiary_projects=Coalesce(Subquery(count, output_field=IntegerField()), 0),
        sole_beneficiary_funding=Subquery(total),
    )


ORDERINGS = {
    "name": ["name", "vat_number"],
    "funding": [F("sole_beneficiary_funding").desc(nulls_last=True), "name"],
    "projects": ["-beneficiary_projects", "name"],
}


class ProvinceCount(Schema):
    province: str
    count: int


class SectionCount(Schema):
    section: str
    count: int


class SourceStatsOut(SourceOut):
    data_date: date | None


class ThemeCount(Schema):
    theme_code: str
    theme: str
    count: int


class FundingStatsOut(Schema):
    beneficiary_companies: int
    beneficiary_projects: int
    sole_beneficiary_funding: float
    by_theme: list[ThemeCount]


class AidStatsOut(Schema):
    companies: int
    grants: int
    total_amount: float


class SizeCount(Schema):
    size: str
    count: int


class StatsOut(Schema):
    total: int
    with_ateco: int
    size_known: int
    by_province: list[ProvinceCount]
    by_section: list[SectionCount]
    by_size: list[SizeCount]
    sources: list[SourceStatsOut]
    funding: FundingStatsOut
    aid: AidStatsOut


@router.get("/companies", response=list[CompanyListItemOut])
@paginate(PageNumberPagination, page_size=25, max_page_size=100)
def list_companies(request, filters: Query[CompanyFilters], sort: SortOption = "name"):
    return filters.filter(_with_funding(Company.objects.all())).order_by(*ORDERINGS[sort])


@router.get("/companies/{vat_number}", response=CompanyDetailOut)
def get_company(request, vat_number: str):
    return _company_detail(get_object_or_404(Company, vat_number=vat_number))


@router.post("/companies/{vat_number}/discover", response=DiscoverResultOut)
def discover_company_website(request, vat_number: str):
    company = get_object_or_404(Company, vat_number=vat_number)
    outcome = discovery.discover_now(company)
    company = Company.objects.get(pk=company.pk)
    if isinstance(outcome, dict) or outcome is None:
        result = outcome
    else:
        result = {"status": outcome.status, "found_url": outcome.found_url, "attempted_at": outcome.attempted_at}
    return {"discovery": result, "company": _company_detail(company)}


def _company_detail(company):
    latest = {}
    for provenance in FieldProvenance.objects.filter(company=company).select_related("snapshot__source"):
        latest.setdefault(provenance.field, provenance)
    provenance = [
        {
            "field": p.field,
            "raw_value": p.raw_value,
            "assurance": p.assurance,
            "confidence": p.confidence,
            "source": p.snapshot.source,
            "reference": p.snapshot.reference,
            "data_date": p.snapshot.data_date,
            "collected_at": p.collected_at,
        }
        for p in latest.values()
    ]
    roles = company.project_roles.select_related("project")
    projects = roles.annotate(
        beneficiary_first=Case(
            When(role=ProjectRole.Role.BENEFICIARY, then=Value(0)), default=Value(1), output_field=IntegerField()
        )
    ).order_by("beneficiary_first", "-project__start_date", "project__code")
    return {
        **{f.name: getattr(company, f.name) for f in Company._meta.concrete_fields},
        "provenance": provenance,
        "funding": _company_funding(roles),
        "projects": [_project_out(r) for r in projects[:PROJECTS_LIMIT]],
        "projects_total": roles.count(),
        "aid": _company_aid(company),
        "website_check": getattr(company, "website_check", None),
    }


def _company_aid(company):
    aids = company.aids.all()
    summary = aids.aggregate(total=Sum("aid_amount"), latest=Max("granted_on"), count=Count("id"))
    return {
        "count": summary["count"],
        "total_amount": float(summary["total"]) if summary["total"] is not None else None,
        "latest_date": summary["latest"],
        "items": [
            {
                **{field: getattr(aid, field) for field in (
                    "cor", "granted_on", "measure_title", "granting_body", "project_title",
                    "objectives", "procedures", "instruments", "transparency_url",
                )},
                "aid_amount": float(aid.aid_amount) if aid.aid_amount is not None else None,
            }
            for aid in aids.order_by("-granted_on", "-cor")[:AID_LIMIT]
        ],
    }



def _company_funding(roles):
    beneficiary = roles.filter(role=ProjectRole.Role.BENEFICIARY)
    sole = beneficiary.filter(project__beneficiaries_count=1)
    total = sole.aggregate(total=Sum("project__public_funding"))["total"]
    return {
        "beneficiary_projects": beneficiary.count(),
        "sole_beneficiary_projects": sole.count(),
        "shared_projects": beneficiary.filter(project__beneficiaries_count__gt=1).count(),
        "sole_beneficiary_funding": float(total) if total is not None else None,
        "roles": dict(roles.values_list("role").annotate(n=Count("id")).order_by("role")),
    }


def _project_out(role):
    project = role.project
    return {
        **{field: getattr(project, field) for field in (
            "code", "title", "summary", "theme_code", "theme", "cycle", "status", "beneficiaries_count",
            "start_date", "expected_end_date", "actual_end_date", "url",
        )},
        "role": role.role,
        "public_funding": float(project.public_funding) if project.public_funding is not None else None,
    }


STATS_CACHE_SECONDS = 6 * 60 * 60


def _scope(province, section, prefix=""):
    scope = {}
    if province:
        scope[f"{prefix}province"] = province
    if section:
        scope[f"{prefix}ateco_section"] = section
    return scope


def _funding_stats(scope):
    beneficiary_roles = ProjectRole.objects.filter(role=ProjectRole.Role.BENEFICIARY, **scope)
    projects = Project.objects.filter(id__in=beneficiary_roles.values("project_id"))
    sole = Project.objects.filter(
        beneficiaries_count=1, id__in=beneficiary_roles.values("project_id")
    ).aggregate(total=Sum("public_funding"))["total"]
    by_theme = (
        Project.objects.filter(id__in=beneficiary_roles.values("project_id"))
        .exclude(theme_code="")
        .values("theme_code", "theme")
        .annotate(count=Count("id"))
        .order_by("-count", "theme_code")
    )
    return {
        "beneficiary_companies": beneficiary_roles.values("company_id").distinct().count(),
        "beneficiary_projects": projects.count(),
        "sole_beneficiary_funding": float(sole or 0),
        "by_theme": list(by_theme),
    }


class SummaryOut(Schema):
    companies: int
    funded_projects: int
    aid_grants: int


@router.get("/summary", response=SummaryOut, auth=None)
def summary(request):
    """Three headline totals for the login page; public, unlike /stats."""
    latest = SourceSnapshot.objects.aggregate(latest=Max("id"))["latest"]
    return cache.get_or_set(f"summary:{latest}", _summary, STATS_CACHE_SECONDS)


def _summary():
    return {
        "companies": Company.objects.count(),
        "funded_projects": Project.objects.filter(
            id__in=ProjectRole.objects.filter(role=ProjectRole.Role.BENEFICIARY).values("project_id")
        ).count(),
        "aid_grants": StateAid.objects.count(),
    }


@router.get("/stats", response=StatsOut)
def stats(request, province: ProvinceCode | None = None, section: SectionCode | None = None):
    """Totals for the dashboard; each chart ignores its own filter so the other options stay visible."""
    latest = SourceSnapshot.objects.aggregate(latest=Max("id"))["latest"]
    key = f"stats:{province or '-'}:{section or '-'}:{latest}"
    return cache.get_or_set(key, lambda: _stats(province, section), STATS_CACHE_SECONDS)


def _stats(province, section):
    in_section = Company.objects.filter(ateco_section=section) if section else Company.objects.all()
    in_province = Company.objects.filter(province=province) if province else Company.objects.all()
    companies = in_section.filter(province=province) if province else in_section
    by_province = in_section.exclude(province="").values("province").annotate(count=Count("id")).order_by("-count")
    by_section = (
        in_province.exclude(ateco_section="").values("ateco_section").annotate(count=Count("id")).order_by("-count")
    )
    by_size = companies.values("size_class").annotate(count=Count("id")).order_by("-count", "size_class")
    sources = []
    for source in Source.objects.filter(snapshots__isnull=False).distinct().order_by("id"):
        snapshot = (
            source.snapshots.filter(provenance__isnull=False).distinct().order_by("-data_date", "-retrieved_at").first()
            or source.snapshots.order_by("-data_date", "-retrieved_at").first()
        )
        sources.append({**{f: getattr(source, f) for f in ("name", "url", "licence", "attribution")},
                        "data_date": snapshot.data_date})
    return {
        "total": companies.count(),
        "with_ateco": companies.exclude(ateco_code="").count(),
        "size_known": companies.exclude(size_class=Company.SizeClass.UNKNOWN).count(),
        "by_province": [{"province": r["province"], "count": r["count"]} for r in by_province],
        "by_section": [{"section": r["ateco_section"], "count": r["count"]} for r in by_section],
        "by_size": [{"size": r["size_class"], "count": r["count"]} for r in by_size],
        "sources": sources,
        "funding": _funding_stats(_scope(province, section, "company__")),
        "aid": _aid_stats(_scope(province, section, "company__")),
    }


def _aid_stats(scope):
    aids = StateAid.objects.filter(**scope)
    summary = aids.aggregate(total=Sum("aid_amount"), grants=Count("id"))
    return {
        "companies": aids.values("company_id").distinct().count(),
        "grants": summary["grants"],
        "total_amount": float(summary["total"] or 0),
    }
