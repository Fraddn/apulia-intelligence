from django.contrib import admin

from .models import SavedCompany


@admin.register(SavedCompany)
class SavedCompanyAdmin(admin.ModelAdmin):
    list_display = ["user", "company", "saved_at"]
    search_fields = ["user__username", "company__name", "company__vat_number"]
    raw_id_fields = ["user", "company"]
