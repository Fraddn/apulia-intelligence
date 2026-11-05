import re

_MOJIBAKE_MARKERS = ("Ã", "Â")


def _fix_mojibake(value: str) -> str:
    for _ in range(3):
        if not any(marker in value for marker in _MOJIBAKE_MARKERS):
            break
        for encoding in ("latin-1", "cp1252"):
            try:
                fixed = value.encode(encoding).decode("utf-8")
                break
            except UnicodeError:
                continue
        else:
            break
        value = fixed
    return value


def clean_text(value) -> str:
    """Fix multiply-encoded UTF-8, unescape '§;' and collapse whitespace."""
    if not value:
        return ""
    value = _fix_mojibake(value).replace("§;", ";")
    return re.sub(r"\s+", " ", value).strip()


def clean_name(value) -> str:
    """clean_text plus removal of CSV-escaped, wrapping and unbalanced quotes; accent apostrophes stay."""
    name = clean_text(value)
    wrapped_in_apostrophes = name.startswith("'")
    name = re.sub(r'"{2,}', '"', name).strip('" ')
    if name.count('"') % 2:
        name = name.replace('"', "")
    name = name.lstrip("' ")
    if wrapped_in_apostrophes or name.endswith(" '"):
        name = name.rstrip("' ")
    return re.sub(r"\s+", " ", name).strip()
