from django.conf import settings
from django.db import models

from apps.companies.models import Company


class SavedCompany(models.Model):
    """A company a user keeps in their personal library."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_companies")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="saved_by")
    note = models.TextField(blank=True, max_length=500)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-saved_at", "-id"]
        constraints = [models.UniqueConstraint(fields=["user", "company"], name="unique_saved_company")]

    def __str__(self):
        return f"{self.user} · {self.company}"
