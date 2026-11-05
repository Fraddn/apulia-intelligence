from collections import Counter

from django.contrib import admin, messages

from .enrichment import websites
from .management.commands.import_websites import manual_snapshot
from .models import Assurance, Company, FieldProvenance, Source, SourceSnapshot


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
    actions = ["fetch_website_contacts"]

    def save_model(self, request, obj, form, change):
        if "website" in form.changed_data:
            obj.website = websites.normalize_url(obj.website)
        super().save_model(request, obj, form, change)
        if "website" in form.changed_data and obj.website:
            obj.record_provenance("website", obj.website, manual_snapshot(f"admin: {request.user}"), Assurance.MANUAL)

    @admin.action(description="Fetch website contacts")
    def fetch_website_contacts(self, request, queryset):
        outcome = Counter(websites.fetch(company, force=True).status for company in queryset)
        summary = ", ".join(f"{status}: {count}" for status, count in sorted(outcome.items()))
        self.message_user(request, f"Website check finished. {summary}", messages.SUCCESS)


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "kind", "licence"]


@admin.register(SourceSnapshot)
class SourceSnapshotAdmin(admin.ModelAdmin):
    list_display = ["source", "reference", "data_date", "retrieved_at"]
    list_filter = ["source"]
