import re
import unicodedata


def clean_ward_name(raw: str) -> str:
    """Normalise ward names for concordance comparisons.

    Normalisation applies in this order:
    1. Strip leading/trailing whitespace
    2. NFC unicode normalisation
    3. Replace curly apostrophes with straight apostrophes
    4. Replace ' & ' (with surrounding spaces) with ' and '
    5. Replace bare '&' with 'and'
    6. Collapse consecutive whitespace to single spaces
    7. Title case the result

    Empty or non-string inputs return an empty string.
    """
    if not raw or not isinstance(raw, str):
        return ""

    cleaned = raw.strip()
    cleaned = unicodedata.normalize("NFC", cleaned)
    cleaned = cleaned.replace("\u2019", "'").replace("\u2018", "'")
    cleaned = re.sub(r"\s+&\s+", " and ", cleaned)
    cleaned = cleaned.replace("&", "and")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.title()
