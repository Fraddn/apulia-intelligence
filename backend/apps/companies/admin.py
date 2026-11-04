from django.contrib import admin

from .models import Company, FieldProvenance, Source, SourceSnapshot


class FieldProvenanceInline(admin.TabularInline):
    model = FieldProvenance
    extra = 0
    can_delete = False
    fields = ["field", "raw_value", "assurance", "confidence", "snapshot", "collected_at"]
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ["name", "vat_number", "province", "ateco_section", "ateco_code", "size_class", "profile_level"]
    list_filter = ["profile_level", "province", "ateco_section", "size_class", "status"]
    search_fields = ["name", "vat_number", "ateco_code", "city"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [FieldProvenanceInline]


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "kind", "licence"]


@admin.register(SourceSnapshot)
class SourceSnapshotAdmin(admin.ModelAdmin):
    list_display = ["source", "reference", "data_date", "retrieved_at"]
    list_filter = ["source"]
