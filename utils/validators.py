import re


_CITY_TOKEN_RE = re.compile(r"^[\w\s\-,.'’]+$")


def is_plausible_city_text(text: str) -> bool:
    """Basic sanity check for free-form city input (UI-neutral)."""
    if not isinstance(text, str):
        return False
    value = text.strip()
    if not value:
        return False
    # Keep permissive: allow commas and common punctuation in city/country inputs
    return bool(_CITY_TOKEN_RE.match(value))
