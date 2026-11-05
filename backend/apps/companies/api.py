from datetime import date, datetime
from typing import Literal

from django.db.models import Case, Count, IntegerField, Q, Sum, Value, When
from django.shortcuts import get_object_or_404
from ninja import FilterSchema, Query, Router, Schema
from ninja.pagination import PageNumberPagination, paginate

from .models import Company, FieldProvenance, Project, ProjectRole, Source

router = Router(tags=["companies"])

PROJECTS_LIMIT = 50

ProvinceCode = Literal["BA", "BT", "BR", "FG", "LE", "TA"]


class CompanyListOut(Schema):
    vat_number: str
    name: str
    province: str
    city: str
    ateco_section: str
    ateco_code: str
    size_class: str


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
    status: str
    employees_band: str
    founded_on: date | None
    profile_level: str
    provenance: list[ProvenanceOut]
    funding: FundingOut
    projects: list[ProjectOut]
    projects_total: int


class CompanyFilters(FilterSchema):
    search: str | None = None
    province: ProvinceCode | None = None
    section: str | None = None
    ateco: str | None = None

    def filter_search(self, value):
        return Q(name__icontains=value) | Q(vat_number__startswith=value) if value else Q()

    def filter_section(self, value):
        return Q(ateco_section=value.upper()) if value else Q()

    def filter_ateco(self, value):
        return Q(ateco_code__startswith=value) if value else Q()


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


class StatsOut(Schema):
    total: int
    with_ateco: int
    size_known: int
    by_province: list[ProvinceCount]
    by_section: list[SectionCount]
    sources: list[SourceStatsOut]
    funding: FundingStatsOut


@router.get("/companies", response=list[CompanyListOut])
@paginate(PageNumberPagination, page_size=25, max_page_size=100)
def list_companies(request, filters: Query[CompanyFilters]):
    return filters.filter(Company.objects.order_by("name", "vat_number"))


@router.get("/companies/{vat_number}", response=CompanyDetailOut)
def get_company(request, vat_number: str):
    company = get_object_or_404(Company, vat_number=vat_number)
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


def _funding_stats():
    beneficiary_roles = ProjectRole.objects.filter(role=ProjectRole.Role.BENEFICIARY)
    projects = Project.objects.filter(roles__role=ProjectRole.Role.BENEFICIARY).distinct()
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


@router.get("/stats", response=StatsOut)
def stats(request):
    companies = Company.objects.all()
    by_province = companies.exclude(province="").values("province").annotate(count=Count("id")).order_by("-count")
    by_section = (
        companies.exclude(ateco_section="").values("ateco_section").annotate(count=Count("id")).order_by("-count")
    )
    sources = []
    for source in Source.objects.filter(snapshots__isnull=False).distinct():
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
        "sources": sources,
        "funding": _funding_stats(),
    }
