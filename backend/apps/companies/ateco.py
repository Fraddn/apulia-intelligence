import re

# ATECO 2007 (NACE Rev. 2) sections by division range.
_SECTIONS = [
    ("A", 1, 3), ("B", 5, 9), ("C", 10, 33), ("D", 35, 35), ("E", 36, 39),
    ("F", 41, 43), ("G", 45, 47), ("H", 49, 53), ("I", 55, 56), ("J", 58, 63),
    ("K", 64, 66), ("L", 68, 68), ("M", 69, 75), ("N", 77, 82), ("O", 84, 84),
    ("P", 85, 85), ("Q", 86, 88), ("R", 90, 93), ("S", 94, 96), ("T", 97, 98),
    ("U", 99, 99),
]

_CODE = re.compile(r"^(?:([A-Z])-)?(\d{2}(?:\.\d{1,2}){0,2})$")


def section_for_division(division: int):
    for section, start, end in _SECTIONS:
        if start <= division <= end:
            return section
    return None


def normalize_ateco(value):
    """Return (section, code) from 'C-25.62.00' or '25.62.00', or (None, None)."""
    if not value or not value.strip():
        return None, None
    match = _CODE.match(value.strip().upper())
    if not match:
        return None, None
    section, code = match.groups()
    derived = section_for_division(int(code[:2]))
    if derived is None:
        return None, None
    return section or derived, code
