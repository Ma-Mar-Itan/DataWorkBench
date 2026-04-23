"""
Data schemas for the data cleaning workbench.

Three families of objects live here:

- ``ExtractedValue`` — one unique value harvested from the workbook, with
  enough context (where it appears, how often, what type it looks like) for
  the user to make a cleaning decision.
- ``CleaningRule`` — one transformation (source → target) with a scope
  (global / sheet / column), a match mode (raw / normalized), and an action
  (replace / set_blank / map_code). Rules are the unit the exporter consumes.
- ``RuleSet`` — a named, reusable bundle of rules persisted to disk.

The enums (``MatchMode``, ``ScopeType``, ``ActionType``, ``ValueClass``) are
string enums so they serialize trivially to JSON and read cleanly in tracebacks.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def _utc_now_iso() -> str:
    """Return an ISO-8601 UTC timestamp with seconds precision."""
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #

class MatchMode(str, Enum):
    """How strictly a rule's source value must match a cell's value.

    Both modes match the *whole cell*, never a substring. The difference is
    only in how the cell's value is compared to the rule's source value.
    """

    #: Match only when the raw string values are byte-identical.
    EXACT_RAW = "exact_raw"

    #: Match after whitespace collapse + trim + lowercase (optional tatweel
    #: removal) on both sides. Lets " Male ", "male", "MALE" all match one rule.
    EXACT_NORMALIZED = "exact_normalized"


class ScopeType(str, Enum):
    """Where a rule may apply."""

    #: Anywhere in the workbook.
    GLOBAL = "global"

    #: Only on the named sheet.
    SHEET = "sheet"

    #: Only in the named column (header label) of the named sheet.
    COLUMN = "column"


class ActionType(str, Enum):
    """What a rule does to a matching cell."""

    #: Replace the cell's value with ``target_value``. The common case.
    REPLACE = "replace"

    #: Clear the cell. ``target_value`` is ignored. Common for missing
    #: placeholders like "N/A", "-", ".".
    SET_BLANK = "set_blank"

    #: Same mechanism as REPLACE, but semantically marks a categorical
    #: recoding (e.g. "male" → "1"). Lets the UI group/display rules differently.
    MAP_CODE = "map_code"


class ValueClass(str, Enum):
    """Best-effort classification of an extracted value.

    Used to help the user prioritize cleaning work, never to trigger
    automatic replacement.
    """

    TEXT_CATEGORY = "text_category"          # short, repeated text — likely categorical
    NUMERIC_LIKE = "numeric_like"            # "1", "2.5" stored as string
    MIXED_ALNUM = "mixed_alnum"              # "A1", "Q3-2024"
    MISSING_TOKEN = "missing_token"          # "N/A", "-", ".", "missing"
    HEADER_LABEL = "header_label"            # appears in a header row
    DATE_LIKE = "date_like"                  # "2024-01-15", "01/15/2024"
    FREE_TEXT = "free_text"                  # long strings — don't batch-recode
    LOW_FREQUENCY = "low_frequency"          # only 1 occurrence
    OTHER = "other"


# --------------------------------------------------------------------------- #
# ExtractedValue
# --------------------------------------------------------------------------- #

@dataclass
class ExtractedValue:
    """A unique string value harvested from the workbook.

    Two values with different raw text but the same normalized form collapse
    into one ExtractedValue (the first ``raw_value`` seen is kept as the
    display form).
    """

    raw_value: str
    normalized_value: str
    frequency: int = 0
    sheets: List[str] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    sample_locations: List[str] = field(default_factory=list)
    value_class: ValueClass = ValueClass.OTHER
    likely_missing: bool = False
    appears_in_headers: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["value_class"] = self.value_class.value
        return d


# --------------------------------------------------------------------------- #
# CleaningRule
# --------------------------------------------------------------------------- #

@dataclass
class CleaningRule:
    """One cleaning transformation.

    A rule is considered *applicable* to a cell when all of the following hold:

    - ``enabled`` is True
    - scope matches (global / correct sheet / correct sheet+column)
    - ``match_mode`` rule matches the cell's value

    On match, the exporter performs the rule's ``action_type`` and, for
    ``REPLACE`` / ``MAP_CODE``, writes ``target_value`` into the cell.
    """

    source_value: str
    target_value: str = ""                    # ignored when action is SET_BLANK
    action_type: ActionType = ActionType.REPLACE
    match_mode: MatchMode = MatchMode.EXACT_RAW
    scope_type: ScopeType = ScopeType.GLOBAL
    scope_sheet: Optional[str] = None         # required if scope_type is SHEET or COLUMN
    scope_column: Optional[str] = None        # required if scope_type is COLUMN
    enabled: bool = True
    notes: str = ""
    rule_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    normalized_source_value: str = ""         # filled in by __post_init__
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)

    def __post_init__(self) -> None:
        # Import here to avoid a circular import at module load — schemas is
        # intentionally pure-data and must not pull in core/normalizer at
        # import time. The import is cheap and only runs on rule construction.
        from core.normalizer import normalize_value

        if not self.normalized_source_value:
            self.normalized_source_value = normalize_value(self.source_value)

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    def validate(self) -> List[str]:
        """Return a list of human-readable validation errors (empty = OK)."""
        errors: List[str] = []
        if not isinstance(self.source_value, str) or self.source_value == "":
            errors.append("Source value must be a non-empty string.")
        if self.action_type in (ActionType.REPLACE, ActionType.MAP_CODE):
            # Empty *target* is allowed; it means "write an empty string".
            # But None or non-string is a bug.
            if not isinstance(self.target_value, str):
                errors.append("Target value must be a string.")
        if self.scope_type == ScopeType.SHEET and not self.scope_sheet:
            errors.append("Sheet scope requires scope_sheet.")
        if self.scope_type == ScopeType.COLUMN:
            if not self.scope_sheet:
                errors.append("Column scope requires scope_sheet.")
            if not self.scope_column:
                errors.append("Column scope requires scope_column.")
        return errors

    # ------------------------------------------------------------------ #
    # Serialization
    # ------------------------------------------------------------------ #

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "source_value": self.source_value,
            "normalized_source_value": self.normalized_source_value,
            "target_value": self.target_value,
            "action_type": self.action_type.value,
            "match_mode": self.match_mode.value,
            "scope_type": self.scope_type.value,
            "scope_sheet": self.scope_sheet,
            "scope_column": self.scope_column,
            "enabled": self.enabled,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CleaningRule":
        # Defensive: missing fields get sensible defaults so older JSON still loads.
        return cls(
            rule_id=data.get("rule_id", uuid.uuid4().hex[:12]),
            source_value=data.get("source_value", ""),
            normalized_source_value=data.get("normalized_source_value", ""),
            target_value=data.get("target_value", ""),
            action_type=ActionType(data.get("action_type", "replace")),
            match_mode=MatchMode(data.get("match_mode", "exact_raw")),
            scope_type=ScopeType(data.get("scope_type", "global")),
            scope_sheet=data.get("scope_sheet"),
            scope_column=data.get("scope_column"),
            enabled=bool(data.get("enabled", True)),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", _utc_now_iso()),
            updated_at=data.get("updated_at", _utc_now_iso()),
        )


# --------------------------------------------------------------------------- #
# RuleSet
# --------------------------------------------------------------------------- #

@dataclass
class RuleSet:
    """A named, reusable collection of rules."""

    name: str
    description: str = ""
    rules: List[CleaningRule] = field(default_factory=list)
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "rules": [r.to_dict() for r in self.rules],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuleSet":
        return cls(
            name=data.get("name", "Untitled"),
            description=data.get("description", ""),
            created_at=data.get("created_at", _utc_now_iso()),
            updated_at=data.get("updated_at", _utc_now_iso()),
            rules=[CleaningRule.from_dict(r) for r in data.get("rules", [])],
        )
