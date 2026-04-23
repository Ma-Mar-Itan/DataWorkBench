"""
Column type inference.

Called after the workbook has been loaded into pandas. We look at the
non-null values of a column and decide what it *is*, so the stats engine
can choose the right summary.

Heuristic, not exhaustive:
  * numeric   - >=90% of non-missing values are numbers (int/float or numeric-string)
  * date      - >=90% of non-missing values parse as dates
  * categorical - small cardinality relative to size (unique/size <= 0.5 and unique <= 50)
  * free text - otherwise text-heavy (mean length > 25 chars OR > 50 unique values)
  * mixed     - none of the above cleanly apply

These thresholds are deliberately conservative; we'd rather say "mixed"
than mislabel a free-text column as categorical.
"""
from __future__ import annotations

import re
from typing import Iterable

import pandas as pd

from models.enums import ColumnType

from .normalizer import is_missing_token, normalize


# Simple numeric-string matcher (integer/decimal, optional sign, optional thousands sep)
_NUMERIC_STR = re.compile(r"^-?\d{1,3}(,\d{3})*(\.\d+)?$|^-?\d+(\.\d+)?$")

# Common date patterns — these are cheap structural checks before pandas parse
_DATE_PATTERNS = [
    re.compile(r"^\d{4}-\d{1,2}-\d{1,2}"),                        # ISO 2024-01-15
    re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}$"),                     # 1/15/24
    re.compile(r"^\d{1,2}-\d{1,2}-\d{2,4}$"),                     # 1-15-2024
    re.compile(r"^\d{1,2}\.\d{1,2}\.\d{2,4}$"),                   # 1.15.2024
]


def _looks_numeric(v) -> bool:
    if isinstance(v, bool):
        return False
    if isinstance(v, (int, float)) and pd.notna(v):
        return True
    if isinstance(v, str):
        s = v.strip()
        return bool(_NUMERIC_STR.match(s))
    return False


def _looks_date(v) -> bool:
    if isinstance(v, pd.Timestamp):
        return True
    if not isinstance(v, str):
        return False
    s = v.strip()
    if any(p.match(s) for p in _DATE_PATTERNS):
        # Final validation via pandas — catches "13/40/2024"
        try:
            pd.to_datetime(s, errors="raise")
            return True
        except Exception:
            return False
    return False


def infer_column_type(values: Iterable) -> ColumnType:
    """Return the inferred ColumnType for a column's values."""
    # Filter out missing tokens and null values
    filtered = [v for v in values if not is_missing_token(v) and pd.notna(v)]
    n = len(filtered)
    if n == 0:
        return ColumnType.MIXED

    num_hits  = sum(1 for v in filtered if _looks_numeric(v))
    date_hits = sum(1 for v in filtered if _looks_date(v))

    if num_hits / n >= 0.9:
        return ColumnType.NUMERIC
    if date_hits / n >= 0.9:
        return ColumnType.DATE

    # Cardinality-based: categorical vs free text
    normalized = [normalize(v) for v in filtered]
    unique = len(set(normalized))
    ratio  = unique / n

    # Short strings with low cardinality → categorical
    mean_len = sum(len(s) for s in normalized) / n
    if unique <= 50 and ratio <= 0.5 and mean_len <= 25:
        return ColumnType.CATEGORICAL

    # Long text or high cardinality → free text
    if mean_len > 25 or unique > 50:
        return ColumnType.FREE_TEXT

    # If the column is e.g. 30% numeric, 60% categorical → mixed
    return ColumnType.MIXED
