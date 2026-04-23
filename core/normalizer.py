"""
Arabic-safe conservative normalizer.

Design intent:
  * Normalization is for *matching* only — it never rewrites the user's
    data. The raw value is always preserved; we just derive a canonical
    form so "Male", "male ", and "MALE" collide under `exact_normalized`.
  * Arabic is treated with minimal changes: NFKC, tatweel removal, and
    whitespace cleanup. No diacritic stripping, no letter folding (no
    ا/أ/إ merging, no ي/ى merging, no ة/ه merging). Those are opinionated
    transformations that can silently change meaning, and this app
    defaults to safety over aggressiveness.
  * Latin text is casefolded so "YES" == "yes" == "Yes".
  * We never do substring work. That is a property of the rules engine,
    not the normalizer, but the normalizer is designed so the normalized
    form is a full-cell canonical value, not a token sequence.

If a future mode wants more aggressive folding, add it as an explicit
match_mode variant; do not change the default.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

# U+0640 ARABIC TATWEEL — purely decorative, safe to strip
_TATWEEL = "\u0640"

# Collapse runs of any Unicode whitespace to a single space
_WS_RUN = re.compile(r"\s+")

# Arabic Unicode block range (for is_arabic)
# 0600-06FF: Arabic, 0750-077F: Arabic Supplement, FB50-FDFF and FE70-FEFF: presentation forms
_ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")


def is_arabic(s: str) -> bool:
    """True if the string contains at least one Arabic-script character."""
    return bool(_ARABIC_RE.search(s))


def to_text(value: Any) -> str:
    """
    Coerce any cell value to a string for normalization/display purposes.

    Returns '' for None. Does NOT convert numeric zero to blank — 0 stays
    as '0'. Booleans become 'True'/'False' (preserved case; not commonly
    needed for scan but kept consistent with str()).
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def normalize(value: Any) -> str:
    """
    Produce the canonical form used by `exact_normalized` matching.

    Steps, in order:
      1. Coerce to string.
      2. Unicode NFKC — merges compatibility forms (e.g. Arabic presentation
         forms → base letters, fullwidth Latin → ASCII).
      3. Strip tatweel.
      4. Collapse any whitespace runs to a single ASCII space.
      5. Trim leading/trailing whitespace.
      6. Casefold — Unicode-aware lowercasing for Latin; a no-op for Arabic.

    Empty string in → empty string out.
    """
    s = to_text(value)
    if s == "":
        return ""

    s = unicodedata.normalize("NFKC", s)
    s = s.replace(_TATWEEL, "")
    s = _WS_RUN.sub(" ", s)
    s = s.strip()
    # casefold is safe on Arabic (it's identity there) and handles Latin,
    # German ß, Greek, etc. more correctly than .lower()
    s = s.casefold()
    return s


# --------------------------------------------------------------------- #
# Missing-token detection
# --------------------------------------------------------------------- #
# These are *normalized* forms. The scanner compares normalize(cell) to
# this set to flag likely missing values.
MISSING_TOKENS: frozenset[str] = frozenset({
    "",
    "n/a",
    "na",
    "n.a.",
    "n/a.",
    "-",
    "--",
    ".",
    "..",
    "missing",
    "null",
    "none",
    "nil",
    "unknown",
    "tbd",
    "#n/a",
    "لا يوجد",    # "no value" in Arabic
    "غير معروف",   # "unknown" in Arabic
})


def is_missing_token(value: Any) -> bool:
    """True if the normalized value matches a known missing token."""
    n = normalize(value)
    return n in MISSING_TOKENS
