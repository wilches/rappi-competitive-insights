"""Match raw product names from platforms to our canonical products."""
import json
import re
import unicodedata
from pathlib import Path
from typing import Optional

_PRODUCTS_PATH = Path(__file__).parent.parent / "config" / "products.json"
with open(_PRODUCTS_PATH, encoding="utf-8") as f:
    _CATALOG = json.load(f)


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).lower().strip()
    return text


_ALIAS_INDEX = {}  # normalized_alias -> canonical
_EXCLUDES = {}     # canonical -> list of normalized excluded substrings
for prod in _CATALOG["products"]:
    for alias in prod["aliases"]:
        _ALIAS_INDEX[_normalize(alias)] = prod["canonical"]
    _EXCLUDES[prod["canonical"]] = [_normalize(x) for x in prod.get("exclude_if_contains", [])]


def match_product(raw_name: str) -> Optional[str]:
    """Return canonical product name if raw_name matches an alias AND doesn't
    contain any excluded keywords for that canonical."""
    if not raw_name:
        return None
    norm = _normalize(raw_name)

    candidate = None
    # Exact match wins
    if norm in _ALIAS_INDEX:
        candidate = _ALIAS_INDEX[norm]
    else:
        # Substring match
        for alias_norm, canonical in _ALIAS_INDEX.items():
            if alias_norm in norm or norm in alias_norm:
                candidate = canonical
                break

    if not candidate:
        return None

    # Exclusion check — reject if raw name contains any excluded substring
    for excl in _EXCLUDES.get(candidate, []):
        if excl and excl in norm:
            return None

    return candidate
