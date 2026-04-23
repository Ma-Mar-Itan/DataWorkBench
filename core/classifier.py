"""
Value classification heuristics.

Given a raw string, return a best-effort ``ValueClass`` that helps the user
prioritize cleaning work. This is **never** used to trigger replacement —
the user sees the classification in the Value Explorer and decides what to
do.

Design philosophy
-----------------
- Cheap. Every heuristic is a couple of regex/string checks, and each is
  evaluated once per unique value (not per cell occurrence).
- Conservative. When in doubt, we fall back to ``OTHER`` or ``FREE_TEXT``
  rather than mis-classifying. A wrong "MISSING_TOKEN" label is worse than
  no label because it invites the user to blank-out real data.
- Order matters. Classes are evaluated specific-first: missing → numeric →
  date → mixed alphanumeric → long free text → short text category.
"""

from __future__ import annotations

import re

from models.schemas import ValueClass


# --------------------------------------------------------------------------- #
# Patterns. Kept as module-level compiled regexes for performance.
# --------------------------------------------------------------------------- #

# Well-known missing-value tokens. Comparison uses the normalized form
# (casefolded, whitespace-collapsed), so we list lowercased variants only.
_MISSING_TOKENS: frozenset[str] = frozenset({
    "n/a", "na", "n.a.", "n.a", "not available",
    "missing", "unknown", "unk", "none", "null", "nil",
    "-", "--", ".", "?", "??",
    "n\\a",
})

# Numeric-looking: integer, decimal, optional sign, optional thousands sep.
# Explicitly forbid whitespace within (normalized already trimmed the outside).
_NUMERIC_RE = re.compile(
    r"""^
        [+-]?                  # optional sign
        (?:
          \d{1,3}(?:,\d{3})+   # 1,234,567 style
          |
          \d+                  # plain digits
        )
        (?:\.\d+)?             # optional decimal fraction
        $""",
    re.VERBOSE,
)

# Common date-like patterns — not exhaustive, and we only mark "date-like"
# on these because false positives here mean we *don't* batch-recode. OK.
_DATE_PATTERNS = (
    re.compile(r"^\d{4}-\d{1,2}-\d{1,2}$"),          # 2024-01-15
    re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}$"),        # 01/15/2024, 1/5/24
    re.compile(r"^\d{1,2}-\d{1,2}-\d{2,4}$"),        # 01-15-2024
    re.compile(r"^\d{4}/\d{1,2}/\d{1,2}$"),          # 2024/01/15
)

# Mixed alphanumeric: at least one letter AND at least one digit, no spaces.
_MIXED_ALNUM_RE = re.compile(r"^(?=.*[A-Za-z\u0600-\u06FF])(?=.*\d)[\w\-./]+$")

# Short text thresholds.
_SHORT_TEXT_MAX_CHARS = 40
_FREE_TEXT_MIN_CHARS = 60


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def classify_value(
    raw_value: str,
    normalized_value: str,
    *,
    frequency: int = 1,
    appears_in_headers: bool = False,
) -> ValueClass:
    """Classify one unique value.

    Parameters
    ----------
    raw_value:
        Representative raw text (first occurrence seen).
    normalized_value:
        Normalized form — lowercased, whitespace-collapsed.
    frequency:
        How many cells held this normalized value. Used to distinguish
        ``LOW_FREQUENCY`` from repeated category candidates.
    appears_in_headers:
        If True, we mark ``HEADER_LABEL`` — headers deserve their own
        category in the UI even if they also look numeric or free-text.

    Returns
    -------
    ValueClass
    """
    # 0. Empty — punt. The scanner shouldn't emit these, but be defensive.
    if not isinstance(raw_value, str) or not raw_value.strip():
        return ValueClass.OTHER

    # 1. Missing tokens — checked first so "NA" doesn't get swept into
    #    mixed-alphanumeric or text-category.
    if normalized_value in _MISSING_TOKENS:
        return ValueClass.MISSING_TOKEN

    # 2. Header label — orthogonal, but we prefer this tag when applicable.
    #    (Appears *after* missing because a literal "N/A" in a header should
    #    still be flagged as a missing token — the user likely wants to recode it.)
    if appears_in_headers:
        return ValueClass.HEADER_LABEL

    # 3. Numeric-looking strings (e.g. "1", "2.5", "1,000").
    if _NUMERIC_RE.match(raw_value.strip()):
        return ValueClass.NUMERIC_LIKE

    # 4. Date-like strings.
    if any(p.match(raw_value.strip()) for p in _DATE_PATTERNS):
        return ValueClass.DATE_LIKE

    # 5. Mixed alphanumeric codes ("A1", "Q3-2024").
    if _MIXED_ALNUM_RE.match(raw_value.strip()):
        return ValueClass.MIXED_ALNUM

    # 6. Length-based text classification.
    length = len(raw_value)
    if length >= _FREE_TEXT_MIN_CHARS:
        return ValueClass.FREE_TEXT
    if frequency == 1 and length > _SHORT_TEXT_MAX_CHARS:
        # Long, seen once → noise.
        return ValueClass.LOW_FREQUENCY
    if frequency == 1 and length <= _SHORT_TEXT_MAX_CHARS:
        return ValueClass.LOW_FREQUENCY

    # 7. Default: short, repeated text — likely a categorical value.
    if length <= _SHORT_TEXT_MAX_CHARS:
        return ValueClass.TEXT_CATEGORY

    return ValueClass.OTHER


def is_likely_missing(normalized_value: str) -> bool:
    """Cheap public check — used by the extractor to set the flag directly."""
    return normalized_value in _MISSING_TOKENS
