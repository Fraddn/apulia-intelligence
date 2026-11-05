from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from .provinces import Province
from .vat import validate_vat


class Assurance(models.TextChoices):
    OFFICIAL = "official", "Official record"
    COMPANY = "company", "Supplied by the company"
    INFERRED = "inferred", "AI-inferred"
    DERIVED = "derived", "Derived by rule"
    MANUAL = "manual", "Entered manually"


class Source(models.Model):
    class Kind(models.TextChoices):
        OPEN_DATA = "open_data", "Open data"
        WEBSITE = "website", "Company website"
        AI_MODEL = "ai_model", "AI model"
        MANUAL = "manual", "Manual entry"

    code = models.SlugField(unique=True)
    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=20, choices=Kind)
    url = models.URLField(blank=True)
    licence = models.CharField(max_length=100, blank=True)
    attribution = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name


class SourceSnapshot(models.Model):
    """One retrieval from a source: a downloaded file, a fetched page, a model run."""

    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="snapshots")
    reference = models.CharField(max_length=500)
    checksum = models.CharField(max_length=64, blank=True)
    data_date = models.DateField(null=True, blank=True)
    retrieved_at = models.DateTimeField(default=timezone.now)
    stats = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-retrieved_at"]

    def __str__(self):
        return f"{self.source.code}: {self.reference}"


class Company(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CEASED = "ceased", "Ceased"
        UNKNOWN = "unknown", "Unknown"

    class SizeClass(models.TextChoices):
        MICRO = "micro", "Micro"
        SMALL = "small", "Small"
        MEDIUM = "medium", "Medium"
        SME = "sme", "SME"
        LARGE = "large", "Large"
        UNKNOWN = "unknown", "Unknown"

    class ProfileLevel(models.TextChoices):
        CANDIDATE = "candidate", "Candidate"
        PROFILE = "profile", "Full profile"

    vat_number = models.CharField(max_length=11, unique=True, validators=[validate_vat])
    tax_code = models.CharField(max_length=16, blank=True)
    name = models.CharField(max_length=255)
    legal_form_code = models.CharField(max_length=10, blank=True)
    legal_form = models.CharField(max_length=255, blank=True)

    ateco_section = models.CharField(max_length=1, blank=True, db_index=True)
    ateco_code = models.CharField(max_length=10, blank=True, db_index=True)
    ateco_description = models.CharField(max_length=255, blank=True)
    ateco_version = models.CharField(max_length=4, blank=True)

    province = models.CharField(max_length=2, choices=Province, blank=True, db_index=True)
    municipality_code = models.CharField(max_length=6, blank=True)
    city = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=255, blank=True)
    postcode = models.CharField(max_length=5, blank=True)
    website = models.URLField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    pec = models.EmailField(blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    status = models.CharField(max_length=10, choices=Status, default=Status.UNKNOWN)
    size_class = models.CharField(max_length=10, choices=SizeClass, default=SizeClass.UNKNOWN)
    employees_band = models.CharField(max_length=50, blank=True)
    founded_on = models.DateField(null=True, blank=True)

    profile_level = models.CharField(
        max_length=10, choices=ProfileLevel, default=ProfileLevel.CANDIDATE, db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "companies"

    def __str__(self):
        return f"{self.name} ({self.vat_number})"

    @classmethod
    def tracked_fields(cls):
        excluded = {"id", "created_at", "updated_at", "profile_level"}
        return {f.name for f in cls._meta.concrete_fields if f.name not in excluded}

    def record_provenance(self, field, raw_value, snapshot, assurance, confidence=None):
        if field not in self.tracked_fields():
            raise ValueError(f"Unknown company field: {field}")
        provenance, _ = FieldProvenance.objects.get_or_create(
            company=self,
            field=field,
            snapshot=snapshot,
            raw_value="" if raw_value is None else str(raw_value),
            defaults={"assurance": assurance, "confidence": confidence},
        )
        return provenance

    def provenance_for(self, field):
        return self.provenance.filter(field=field).select_related("snapshot__source").first()


class FieldProvenance(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="provenance")
    field = models.CharField(max_length=50)
    raw_value = models.TextField(blank=True)
    snapshot = models.ForeignKey(SourceSnapshot, on_delete=models.PROTECT, related_name="provenance")
    assurance = models.CharField(max_length=10, choices=Assurance)
    confidence = models.FloatField(
        null=True, blank=True, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    collected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-collected_at", "-id"]
        indexes = [models.Index(fields=["company", "field"])]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "field", "snapshot", "raw_value"], name="unique_provenance_value"
            )
        ]

    def __str__(self):
        return f"{self.company.vat_number}.{self.field} ← {self.snapshot}"


class Project(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        ONGOING = "ongoing", "Ongoing"
        COMPLETED = "completed", "Completed"
        SETTLED = "settled", "Settled"
        UNKNOWN = "unknown", "Unknown"

    code = models.CharField(max_length=100, unique=True)
    cup = models.CharField(max_length=20, blank=True)
    title = models.TextField()
    summary = models.TextField(blank=True)
    theme_code = models.CharField(max_length=2, blank=True, db_index=True)
    theme = models.CharField(max_length=100, blank=True)
    cycle = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=12, choices=Status, default=Status.UNKNOWN)
    public_funding = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    eu_funding = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    payments = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    expected_end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    beneficiaries_count = models.PositiveIntegerField(default=0)
    url = models.URLField(blank=True)
    snapshot = models.ForeignKey(SourceSnapshot, on_delete=models.PROTECT, related_name="projects")

    class Meta:
        ordering = ["-start_date", "code"]

    def __str__(self):
        return f"{self.code}: {self.title[:60]}"


class ProjectRole(models.Model):
    class Role(models.TextChoices):
        BENEFICIARY = "beneficiary", "Beneficiary"
        IMPLEMENTER = "implementer", "Implementer"
        CONTRACTOR = "contractor", "Contractor"
        PROGRAMMER = "programmer", "Programming authority"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="project_roles")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="roles")
    role = models.CharField(max_length=12, choices=Role)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["company", "project", "role"], name="unique_project_role")]
        indexes = [models.Index(fields=["company", "role"])]

    def __str__(self):
        return f"{self.company.vat_number} {self.role} {self.project.code}"


class StateAid(models.Model):
    """One aid grant from the national state-aid register (RNA), identified by its COR code."""

    cor = models.CharField(max_length=30, unique=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="aids")
    measure_code = models.CharField(max_length=30, blank=True)
    measure_title = models.TextField(blank=True)
    measure_type = models.CharField(max_length=100, blank=True)
    granting_body = models.CharField(max_length=255, blank=True)
    project_title = models.TextField(blank=True)
    project_description = models.TextField(blank=True)
    granted_on = models.DateField(null=True, blank=True, db_index=True)
    cup = models.CharField(max_length=20, blank=True)
    procedures = models.CharField(max_length=255, blank=True)
    objectives = models.TextField(blank=True)
    instruments = models.CharField(max_length=255, blank=True)
    sector = models.CharField(max_length=50, blank=True)
    aid_amount = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    nominal_amount = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    beneficiary_size = models.CharField(max_length=50, blank=True)
    transparency_url = models.CharField(max_length=1000, blank=True)
    snapshot = models.ForeignKey(SourceSnapshot, on_delete=models.PROTECT, related_name="aids")

    class Meta:
        ordering = ["-granted_on", "cor"]
        indexes = [models.Index(fields=["company", "granted_on"])]

    def __str__(self):
        return f"{self.cor}: {self.company.vat_number} {self.aid_amount}"



class WebsiteCheck(models.Model):
    """Outcome of the latest attempt to read a company's own website."""

    class Status(models.TextChoices):
        VERIFIED = "verified", "VAT number found"
        VAT_NOT_FOUND = "vat_not_found", "VAT number not found"
        UNREACHABLE = "unreachable", "Unreachable"
        BLOCKED = "blocked", "Blocked by robots.txt"
        NO_WEBSITE = "no_website", "No website"

    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name="website_check")
    url = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=15, choices=Status)
    pages = models.PositiveSmallIntegerField(default=0)
    error = models.CharField(max_length=255, blank=True)
    checked_at = models.DateTimeField()

    def __str__(self):
        return f"{self.company.vat_number}: {self.status}"


class WebsitePage(models.Model):
    """Text of a page read from a company's website, kept for classification."""

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="website_pages")
    url = models.CharField(max_length=500)
    status_code = models.PositiveSmallIntegerField()
    text = models.TextField(blank=True)
    vat_found = models.BooleanField(default=False)
    fetched_at = models.DateTimeField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["company", "url"], name="unique_website_page")]

    def __str__(self):
        return self.url


class WebsiteDiscovery(models.Model):
    """Attempt to find a company's website by guessing domains from its name."""

    class Status(models.TextChoices):
        FOUND = "found", "Found"
        NOT_FOUND = "not_found", "Not found"
        NO_CANDIDATES = "no_candidates", "Name too short to guess"

    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name="website_discovery")
    status = models.CharField(max_length=15, choices=Status)
    found_url = models.CharField(max_length=500, blank=True)
    tried = models.JSONField(default=list, blank=True)
    attempted_at = models.DateTimeField()

    def __str__(self):
        return f"{self.company.vat_number}: {self.status}"


class Municipality(models.Model):
    """Italian municipality from the official ISTAT list."""

    code = models.CharField(max_length=6, unique=True)
    name = models.CharField(max_length=200)
    province = models.CharField(max_length=2, blank=True)
    region_code = models.CharField(max_length=2, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "municipalities"

    def __str__(self):
        return f"{self.name} ({self.province})"
