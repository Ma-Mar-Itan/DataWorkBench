"""
Enums for the rule system and scan classification.

Kept in their own module so both the schemas and engine modules can
import them without circular dependencies.
"""
from __future__ import annotations

from enum import Enum


class ScopeType(str, Enum):
    WORKBOOK = "workbook"
    SHEET    = "sheet"
    COLUMN   = "column"


class MatchMode(str, Enum):
    EXACT_RAW        = "exact_raw"
    EXACT_NORMALIZED = "exact_normalized"


class ActionType(str, Enum):
    REPLACE   = "replace"
    SET_BLANK = "set_blank"


class ValueClass(str, Enum):
    CATEGORICAL   = "categorical"
    MISSING       = "missing"
    NUMERIC_LIKE  = "numeric-like"
    DATE_LIKE     = "date-like"
    FREE_TEXT     = "free text"
    LOW_FREQUENCY = "low frequency"


class ColumnType(str, Enum):
    NUMERIC     = "numeric"
    CATEGORICAL = "categorical"
    FREE_TEXT   = "free text"
    DATE        = "date"
    MIXED       = "mixed"
