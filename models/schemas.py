"""
Core dataclasses.

Using `dataclass` rather than pydantic keeps zero runtime deps and is
plenty for internal engine state. Validation lives in the ruleset_store
loader for JSON input.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

from .enums import ActionType, ColumnType, MatchMode, ScopeType, ValueClass


# --------------------------------------------------------------------- #
# Rules
# --------------------------------------------------------------------- #
@dataclass
class Rule:
    rule_id:      str
    source_value: str
    target_value: str                                = ""
    action_type:  ActionType                         = ActionType.REPLACE
    match_mode:   MatchMode                          = MatchMode.EXACT_NORMALIZED
    scope_type:   ScopeType                          = ScopeType.WORKBOOK
    scope_sheet:  str                                = ""
    scope_column: str                                = ""
    enabled:      bool                               = True
    # order of creation — used as final tie-breaker in precedence
    created_at:   int                                = 0

    def to_dict(self) -> dict:
        d = asdict(self)
        # Convert Enums back to their string values
        for k in ("action_type", "match_mode", "scope_type"):
            v = d.get(k)
            if hasattr(v, "value"):
                d[k] = v.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Rule":
        return cls(
            rule_id=str(d["rule_id"]),
            source_value=str(d.get("source_value", "")),
            target_value=str(d.get("target_value", "")),
            action_type=ActionType(d.get("action_type", ActionType.REPLACE.value)),
            match_mode=MatchMode(d.get("match_mode", MatchMode.EXACT_NORMALIZED.value)),
            scope_type=ScopeType(d.get("scope_type", ScopeType.WORKBOOK.value)),
            scope_sheet=str(d.get("scope_sheet", "") or ""),
            scope_column=str(d.get("scope_column", "") or ""),
            enabled=bool(d.get("enabled", True)),
            created_at=int(d.get("created_at", 0)),
        )


# --------------------------------------------------------------------- #
# Scan artifacts
# --------------------------------------------------------------------- #
@dataclass
class CellCoord:
    sheet:  str
    row:    int          # 1-based (matches Excel row numbers)
    column: str          # header label (or A1-style if no header)


@dataclass
class ValueOccurrence:
    raw_value:        str
    normalized_value: str
    total_count:      int
    per_sheet:        dict[str, int]       = field(default_factory=dict)
    per_column:       dict[str, int]       = field(default_factory=dict)   # "Sheet::Column"
    examples:         list[CellCoord]      = field(default_factory=list)
    value_class:      ValueClass           = ValueClass.FREE_TEXT


@dataclass
class SheetMeta:
    name: str
    rows: int            # data rows (excluding header)
    cols: int
    headers: list[str]   = field(default_factory=list)


@dataclass
class WorkbookMeta:
    filename:             str
    sheet_count:          int
    total_rows:           int
    total_cols:           int
    sheets:               list[SheetMeta]         = field(default_factory=list)
    total_unique_strings: int                     = 0
    total_missing_tokens: int                     = 0


@dataclass
class ScanResult:
    workbook: WorkbookMeta
    values:   list[ValueOccurrence]               = field(default_factory=list)


# --------------------------------------------------------------------- #
# Preview / apply
# --------------------------------------------------------------------- #
@dataclass
class CellChange:
    sheet:     str
    row:       int
    column:    str
    before:    Any
    after:     Any
    rule_id:   str


@dataclass
class ApplyResult:
    changes:           list[CellChange]        = field(default_factory=list)
    fires_per_rule:    dict[str, int]          = field(default_factory=dict)
    affected_sheets:   set[str]                = field(default_factory=set)
    affected_columns:  set[str]                = field(default_factory=set)

    @property
    def changed_cells(self) -> int:
        return len(self.changes)


# --------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------- #
@dataclass
class NumericStats:
    column: str
    sheet: str
    count:   int
    missing: int
    mean:    float | None
    median:  float | None
    std:     float | None
    min_:    float | None
    q1:      float | None
    q3:      float | None
    max_:    float | None


@dataclass
class CategoricalStats:
    column:       str
    sheet:        str
    non_missing:  int
    missing:      int
    unique:       int
    mode:         str | None
    top_values:   list[tuple[str, int, float]] = field(default_factory=list)   # (value, count, pct)


@dataclass
class ColumnInference:
    sheet:   str
    column:  str
    dtype:   ColumnType


@dataclass
class BeforeAfterSummary:
    changed_cells:          int
    affected_sheets:        int
    affected_columns:       int
    category_reduction:     dict[str, tuple[int, int]]       # column -> (before_unique, after_unique)
    missing_added:          int                               # cells blanked by set_blank
