import re
from typing import NamedTuple

# ATECO 2007 (NACE Rev. 2) sections by division range. Also valid for the 2022 update.
_SECTIONS = [
    ("A", 1, 3), ("B", 5, 9), ("C", 10, 33), ("D", 35, 35), ("E", 36, 39),
    ("F", 41, 43), ("G", 45, 47), ("H", 49, 53), ("I", 55, 56), ("J", 58, 63),
    ("K", 64, 66), ("L", 68, 68), ("M", 69, 75), ("N", 77, 82), ("O", 84, 84),
    ("P", 85, 85), ("Q", 86, 88), ("R", 90, 93), ("S", 94, 96), ("T", 97, 98),
    ("U", 99, 99),
]
_VALID_SECTIONS = {s for s, _, _ in _SECTIONS}
_MAPPED_VERSIONS = {"2007", "2022"}

_CODE = re.compile(r"^(?:([A-Z])-)?(\d{2}(?:\.\d{1,2}){0,2})$")
_SECTION_ONLY = re.compile(r"^([A-Z])$")


class Ateco(NamedTuple):
    section: str
    code: str
    version: str


def section_for_division(division: int):
    for section, start, end in _SECTIONS:
        if start <= division <= end:
            return section
    return None


def normalize_ateco(value):
    """Parse 'C-25.62.00', '25.62.00_2007', '62.01' or 'P_2007'. Returns Ateco or None."""
    if not value or not value.strip():
        return None
    main, *suffixes = value.strip().upper().split("_")
    version = next((s for s in suffixes if re.fullmatch(r"\d{4}", s)), "2007")

    if match := _SECTION_ONLY.match(main):
        section = match.group(1)
        return Ateco(section, "", version) if section in _VALID_SECTIONS else None

    match = _CODE.match(main)
    if not match:
        return None
    letter, code = match.groups()
    if version not in _MAPPED_VERSIONS:
        return Ateco("", code, version)

    derived = section_for_division(int(code[:2]))
    if derived is None or (letter and letter != derived):
        return None
    return Ateco(derived, code, version)
