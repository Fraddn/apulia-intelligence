from functools import wraps

from allauth.core import ratelimit
from django.contrib import admin


def rate_limited(login_view):
    """Apply allauth's failed-login limits (per IP and per username) to the Django admin login."""

    @wraps(login_view)
    def view(request, *args, **kwargs):
        if request.method == "POST":
            username = (request.POST.get("username") or "").strip().lower()
            response = ratelimit.consume_or_429(request, action="login_failed", key=username)
            if response:
                return response
        return login_view(request, *args, **kwargs)

    return view


admin.site.login = rate_limited(admin.site.login)
