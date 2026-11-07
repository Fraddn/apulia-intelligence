from datetime import datetime

from django.db.models import F, OuterRef, Subquery
from django.shortcuts import get_object_or_404
from ninja import Field, Router, Schema

from apps.companies.api import CompanyListItemOut, _with_funding
from apps.companies.models import Company

from .models import SavedCompany

router = Router(tags=["library"])

MAX_SAVED = 1000


class SavedCompanyOut(CompanyListItemOut):
    saved_at: datetime
    note: str


class NoteIn(Schema):
    note: str = Field("", max_length=500)


class ErrorOut(Schema):
    detail: str


def _saved(request, vat_number: str | None = None):
    mine = SavedCompany.objects.filter(user=request.user, company=OuterRef("pk"))
    queryset = _with_funding(Company.objects.filter(saved_by__user=request.user)).annotate(
        saved_at=Subquery(mine.values("saved_at")),
        note=Subquery(mine.values("note")),
    )
    if vat_number is not None:
        return get_object_or_404(queryset, vat_number=vat_number)
    return queryset.order_by(F("saved_at").desc(), "name")


@router.get("/library", response=list[SavedCompanyOut])
def list_library(request):
    return _saved(request)


@router.post("/library/{vat_number}", response={200: SavedCompanyOut, 409: ErrorOut})
def save_company(request, vat_number: str):
    company = get_object_or_404(Company, vat_number=vat_number)
    mine = SavedCompany.objects.filter(user=request.user)
    if not mine.filter(company=company).exists() and mine.count() >= MAX_SAVED:
        return 409, {"detail": f"A library holds up to {MAX_SAVED} companies."}
    SavedCompany.objects.get_or_create(user=request.user, company=company)
    return 200, _saved(request, vat_number)


@router.patch("/library/{vat_number}", response=SavedCompanyOut)
def update_note(request, vat_number: str, payload: NoteIn):
    saved = get_object_or_404(SavedCompany, user=request.user, company__vat_number=vat_number)
    saved.note = payload.note.strip()
    saved.save(update_fields=["note"])
    return _saved(request, vat_number)


@router.delete("/library/{vat_number}", response={204: None})
def remove_company(request, vat_number: str):
    SavedCompany.objects.filter(user=request.user, company__vat_number=vat_number).delete()
    return 204, None
