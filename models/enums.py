"""Enum definitions for the spreadsheet cleaner application."""

from enum import Enum


class MatchMode(str, Enum):
    """Matching modes for cleaning rules."""
    EXACT_RAW = "exact_raw"
    EXACT_NORMALIZED = "exact_normalized"


class ScopeType(str, Enum):
    """Scope types for cleaning rules."""
    WORKBOOK = "workbook"
    SHEET = "sheet"
    COLUMN = "column"


class ActionType(str, Enum):
    """Action types for cleaning rules."""
    REPLACE = "replace"
    SET_BLANK = "set_blank"


class ColumnType(str, Enum):
    """Inferred column types."""
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    TEXT = "text"
    DATE = "date"
    MIXED = "mixed"


class RulePrecedence:
    """Rule precedence ordering (lower number = higher priority)."""
    COLUMN = 1
    SHEET = 2
    WORKBOOK = 3
    
    MATCH_EXACT_RAW = 1
    MATCH_EXACT_NORMALIZED = 2
