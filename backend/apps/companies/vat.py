from django.core.exceptions import ValidationError

from .provinces import ISTAT_PROVINCE_CODES


def is_valid_vat(value) -> bool:
    """Check if the VAT number is valid according to the Italian VAT number rules."""
    if not isinstance(value, str) or len(value) != 11 or not value.isdigit():
        return False
    digits = [int(c) for c in value]
    total = sum(digits[0:10:2])
    for d in digits[1:10:2]:
        doubled = d * 2
        total += doubled - 9 if doubled > 9 else doubled
    return (10 - total % 10) % 10 == digits[10]


def validate_vat(value):
    """Validate the VAT number and raise a ValidationError if it's invalid."""
    if not is_valid_vat(value):
        raise ValidationError("%(value)s is not a valid Italian VAT number.", params={"value": value})


def province_from_vat(value):
    """Province of the tax office that issued the VAT number (digits 8-10)."""
    if not isinstance(value, str) or len(value) != 11 or not value.isdigit():
        return None
    return ISTAT_PROVINCE_CODES.get(value[7:10])
