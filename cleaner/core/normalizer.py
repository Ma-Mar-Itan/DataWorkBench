"""
Value normalization.

Used in two places:

1.  **Scanning.** When the extractor builds the unique-value registry, it
    groups values by their normalized form. Two cells holding " Male " and
    "male" collapse into one ExtractedValue with frequency 2.

2.  **Matching.** The exporter's EXACT_NORMALIZED match mode compares the
    cell's normalized value against the rule's ``normalized_source_value``.

Normalization steps (in order)
------------------------------
1. NFKC Unicode normalization — folds compatibility forms, full-width
   digits, composes decomposed characters.
2. Tatweel (U+0640) removal — purely cosmetic Arabic elongation.
3. Whitespace collapse — every run of Unicode whitespace becomes a single
   ASCII space, with leading/trailing spaces trimmed.
4. Lowercase (``casefold``) — case-insensitive matching for Latin text;
   harmless for Arabic since Arabic has no case.

What we deliberately do **not** do
----------------------------------
- Strip punctuation. "N/A" and "N.A." stay distinct unless the user writes
  rules for both. Folding them would risk collapsing codes that mean
  different things (e.g. "1.0" vs "1/0").
- Fold Arabic letter variants (alef forms, ya vs alef maqsura). In
  statistical vocabulary these distinctions can be meaningful.
- Strip leading zeros ("01" vs "1"). Often semantically meaningful in ID
  codes and survey answer keys.

The user who wants any of those collapsed can write a rule that maps both
forms to the canonical one.
"""

from __future__ import annotations

import re
import unicodedata


_TATWEEL = "\u0640"
_WHITESPACE_RUN = re.compile(r"\s+", re.UNICODE)


def normalize_value(value: object) -> str:
    """Return the normalized form of ``value`` suitable for grouping/matching.

    Non-strings return an empty string. The exporter never matches non-string
    cells, so this coercion is safe.
    """
    if not isinstance(value, str):
        return ""
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", value)
    if _TATWEEL in text:
        text = text.replace(_TATWEEL, "")
    text = _WHITESPACE_RUN.sub(" ", text).strip()
    return text.casefold()


def trim_and_collapse(value: str) -> str:
    """Lighter normalization: whitespace only, no case change.

    Useful where we need to present cleaned-up display text but mustn't
    alter the user's casing. Currently used by the extractor when recording
    a value's representative ``raw_value``.
    """
    if not isinstance(value, str) or not value:
        return ""
    text = unicodedata.normalize("NFKC", value)
    if _TATWEEL in text:
        text = text.replace(_TATWEEL, "")
    return _WHITESPACE_RUN.sub(" ", text).strip()


def is_blank(value: object) -> bool:
    """True if the value is None, an empty string, or whitespace-only."""
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    return value.strip() == ""
