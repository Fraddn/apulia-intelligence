from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

username_validators = [
    RegexValidator(
        r"^[a-zA-Z0-9._-]+$",
        _("Use only letters, numbers and the characters . - _"),
        code="invalid_username",
    ),
]

