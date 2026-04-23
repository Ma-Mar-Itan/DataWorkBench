"""
Preset cleaning templates.

These are **suggestions** — they populate editable rule rows, never
auto-apply. The user always reviews and commits.

Every preset is a function returning a fresh list of ``CleaningRule``
objects. We return lists (not a RuleSet) because the UI applies presets
additively on top of whatever the user has already built; if they want to
save the result as a named set, that's a separate, explicit action.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from models.schemas import ActionType, CleaningRule, MatchMode, ScopeType


# --------------------------------------------------------------------------- #

def gender_coding(scope_sheet: Optional[str] = None, scope_column: Optional[str] = None) -> List[CleaningRule]:
    """male → 1, female → 2 (normalized match, so case/whitespace tolerant)."""
    scope_type = ScopeType.COLUMN if scope_column else (ScopeType.SHEET if scope_sheet else ScopeType.GLOBAL)
    return [
        CleaningRule(
            source_value="male",
            target_value="1",
            action_type=ActionType.MAP_CODE,
            match_mode=MatchMode.EXACT_NORMALIZED,
            scope_type=scope_type,
            scope_sheet=scope_sheet,
            scope_column=scope_column,
            notes="Gender coding preset",
        ),
        CleaningRule(
            source_value="female",
            target_value="2",
            action_type=ActionType.MAP_CODE,
            match_mode=MatchMode.EXACT_NORMALIZED,
            scope_type=scope_type,
            scope_sheet=scope_sheet,
            scope_column=scope_column,
            notes="Gender coding preset",
        ),
    ]


def yes_no_coding(scope_sheet: Optional[str] = None, scope_column: Optional[str] = None) -> List[CleaningRule]:
    """Yes → 1, No → 0 (normalized)."""
    scope_type = ScopeType.COLUMN if scope_column else (ScopeType.SHEET if scope_sheet else ScopeType.GLOBAL)
    return [
        CleaningRule(
            source_value="yes",
            target_value="1",
            action_type=ActionType.MAP_CODE,
            match_mode=MatchMode.EXACT_NORMALIZED,
            scope_type=scope_type,
            scope_sheet=scope_sheet,
            scope_column=scope_column,
            notes="Yes/No coding preset",
        ),
        CleaningRule(
            source_value="no",
            target_value="0",
            action_type=ActionType.MAP_CODE,
            match_mode=MatchMode.EXACT_NORMALIZED,
            scope_type=scope_type,
            scope_sheet=scope_sheet,
            scope_column=scope_column,
            notes="Yes/No coding preset",
        ),
    ]


def likert_5_point() -> List[CleaningRule]:
    """5-point Likert → 1..5 (Very poor → 1 through Very good → 5), normalized."""
    scale = [
        ("Very poor", "1"),
        ("Poor",      "2"),
        ("Fair",      "3"),
        ("Good",      "4"),
        ("Very good", "5"),
    ]
    return [
        CleaningRule(
            source_value=label,
            target_value=code,
            action_type=ActionType.MAP_CODE,
            match_mode=MatchMode.EXACT_NORMALIZED,
            scope_type=ScopeType.GLOBAL,
            notes="Likert 5-point preset",
        )
        for label, code in scale
    ]


def missing_value_cleanup(target: str = "") -> List[CleaningRule]:
    """Common missing tokens → blank (or a chosen sentinel)."""
    tokens = ["N/A", "n/a", "NA", "na", "N.A.", "n.a.", "missing", "Missing",
              "unknown", "Unknown", "none", "None", "null", "Null",
              "-", "--", ".", "?"]
    action = ActionType.SET_BLANK if target == "" else ActionType.REPLACE
    return [
        CleaningRule(
            source_value=t,
            target_value=target,
            action_type=action,
            match_mode=MatchMode.EXACT_NORMALIZED,
            scope_type=ScopeType.GLOBAL,
            notes="Missing value cleanup preset",
        )
        for t in tokens
    ]


def marital_status() -> List[CleaningRule]:
    """Single → 1, Married → 2, Divorced → 3, Widowed → 4."""
    scale = [("Single", "1"), ("Married", "2"), ("Divorced", "3"), ("Widowed", "4")]
    return [
        CleaningRule(
            source_value=label,
            target_value=code,
            action_type=ActionType.MAP_CODE,
            match_mode=MatchMode.EXACT_NORMALIZED,
            scope_type=ScopeType.GLOBAL,
            notes="Marital status preset",
        )
        for label, code in scale
    ]


# --------------------------------------------------------------------------- #
# Registry for the UI.
# --------------------------------------------------------------------------- #

# ``scoped`` presets accept scope arguments; ``plain`` presets don't.
PRESET_REGISTRY: Dict[str, dict] = {
    "Gender coding (male/female → 1/2)": {
        "scoped": True,
        "factory": gender_coding,
        "description": "Map male → 1 and female → 2. Normalized match.",
    },
    "Yes / No coding (yes/no → 1/0)": {
        "scoped": True,
        "factory": yes_no_coding,
        "description": "Map yes → 1 and no → 0. Normalized match.",
    },
    "5-point Likert (Very poor…Very good → 1..5)": {
        "scoped": False,
        "factory": likert_5_point,
        "description": "Map a 5-point Likert scale to numeric codes 1–5.",
    },
    "Missing value cleanup (blank out)": {
        "scoped": False,
        "factory": missing_value_cleanup,
        "description": "Blank common missing placeholders: N/A, missing, -, ., ?.",
    },
    "Marital status (Single/Married/… → 1..4)": {
        "scoped": False,
        "factory": marital_status,
        "description": "Map four marital-status labels to codes 1–4.",
    },
}
