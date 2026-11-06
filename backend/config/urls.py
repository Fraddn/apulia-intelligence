from django.contrib import admin
from django.http import Http404
from django.urls import include, path, re_path

from config.api import api


def disabled(request, *args, **kwargs):
    raise Http404


urlpatterns = [
    path("admin/", admin.site.urls),
    # Password reset needs email delivery, which is not set up: reset in the Django admin instead.
    re_path(r"^_allauth/(browser|app)/v1/auth/password/(request|reset)$", disabled),
    path("_allauth/", include("allauth.headless.urls")),
    path("api/", api.urls),
]
