"""Conservative Unicode normalization with Arabic support."""

import unicodedata
import re
from typing import Optional


# Common missing value tokens
MISSING_TOKENS = {
    "n/a", "na", "-", ".", "missing", "null", "none", "unknown",
    "nan", "", " ", "nil", "undefined", "not available",
    "لا شيء", "فارغ", "غير متوفر", "مجهول",  # Arabic missing tokens
}

# Arabic tatweel character (used for elongation)
TATWEEL = "\u0640"


def normalize_value(value: any) -> str:
    """
    Normalize a value conservatively.
    
    This function:
    - Casts to string if needed
    - Applies Unicode NFKC normalization
    - Trims whitespace
    - Collapses repeated internal spaces
    - Removes tatweel (Arabic elongation)
    - Casefolds Latin text
    - Preserves Arabic letters safely
    
    Does NOT:
    - Do aggressive stemming
    - Do transliteration
    - Do semantic rewriting
    - Do substring matching
    """
    if value is None:
        return ""
    
    # Convert to string
    str_value = str(value)
    
    # Handle NaN/None strings from pandas
    if str_value.lower() in ("nan", "none"):
        return ""
    
    # Unicode normalize with NFKC
    normalized = unicodedata.normalize("NFKC", str_value)
    
    # Trim leading/trailing whitespace
    normalized = normalized.strip()
    
    # Collapse repeated internal spaces (including Arabic spaces)
    normalized = re.sub(r"[\s\u00A0\u200B]+", " ", normalized)
    
    # Remove tatweel (Arabic elongation character)
    normalized = normalized.replace(TATWEEL, "")
    
    # Casefold Latin text only (preserve Arabic)
    # We check if the string contains primarily Latin characters
    has_latin = any("\u0041" <= c <= "\u005A" or "\u0061" <= c <= "\u007A" 
                    for c in normalized)
    has_arabic = any("\u0600" <= c <= "\u06FF" for c in normalized)
    
    if has_latin and not has_arabic:
        normalized = normalized.casefold()
    elif has_latin and has_arabic:
        # Mixed content - casefold only Latin portions
        result = []
        for char in normalized:
            if "\u0041" <= char <= "\u005A":  # Uppercase Latin
                result.append(char.casefold())
            else:
                result.append(char)
        normalized = "".join(result)
    
    return normalized


def is_likely_missing(value: str) -> bool:
    """Check if a normalized value is likely a missing token."""
    normalized = normalize_value(value).lower()
    return normalized in MISSING_TOKENS or normalized == ""


def infer_value_type(value: str) -> str:
    """
    Infer the type of a value based on its content.
    
    Returns one of:
    - "numeric": Looks like a number
    - "date": Looks like a date
    - "categorical": Short, repeated value
    - "text": Free text
    - "empty": Empty or missing
    """
    normalized = normalize_value(value)
    
    if not normalized:
        return "empty"
    
    # Check for numeric
    try:
        float(normalized.replace(",", "").replace("%", ""))
        return "numeric"
    except ValueError:
        pass
    
    # Check for date patterns (common formats)
    date_patterns = [
        r"^\d{1,2}/\d{1,2}/\d{2,4}$",  # MM/DD/YYYY or DD/MM/YYYY
        r"^\d{4}-\d{2}-\d{2}$",  # YYYY-MM-DD
        r"^\d{1,2}-\d{1,2}-\d{2,4}$",  # MM-DD-YYYY
        r"^[A-Za-z]{3,9} \d{1,2},? \d{4}$",  # Month DD, YYYY
    ]
    for pattern in date_patterns:
        if re.match(pattern, normalized):
            return "date"
    
    # Short values are likely categorical
    if len(normalized) < 20:
        return "categorical"
    
    return "text"
