"""
Rule engine tests — scope priority, match modes, invariants.

The single most important test in this file is
``test_no_substring_leak``, which proves the whole-cell-match invariant:
a rule mapping a short value cannot touch a cell whose value *contains*
that short value as a substring.
"""

from __future__ import annotations

from core.rules_engine import CellContext, RuleIndex
from models.schemas import ActionType, CleaningRule, MatchMode, ScopeType


# --------------------------------------------------------------------------- #
# Safety invariant — MOST IMPORTANT TEST IN THE SUITE.
# --------------------------------------------------------------------------- #

def test_no_substring_leak() -> None:
    """Rule source 'male' must NOT match a cell whose value is 'male student'."""
    index = RuleIndex([
        CleaningRule(
            source_value="male",
            target_value="1",
            match_mode=MatchMode.EXACT_NORMALIZED,
            scope_type=ScopeType.GLOBAL,
        ),
    ])
    # The cell contains "male" as a prefix — classic substring-leak scenario.
    app = index.apply(CellContext(sheet="S", column="Note", raw_value="male student"))
    assert app is None, "Substring match leaked through the engine"


def test_no_substring_leak_with_raw_mode() -> None:
    """Same invariant under EXACT_RAW mode."""
    index = RuleIndex([
        CleaningRule(
            source_value="male",
            target_value="1",
            match_mode=MatchMode.EXACT_RAW,
            scope_type=ScopeType.GLOBAL,
        ),
    ])
    app = index.apply(CellContext(sheet="S", column="Note", raw_value="male student"))
    assert app is None


# --------------------------------------------------------------------------- #
# Match modes
# --------------------------------------------------------------------------- #

def test_exact_raw_matches_only_exact_bytes() -> None:
    index = RuleIndex([
        CleaningRule(
            source_value="male",
            target_value="1",
            match_mode=MatchMode.EXACT_RAW,
            scope_type=ScopeType.GLOBAL,
        ),
    ])
    assert index.apply(CellContext("S", "C", "male")) is not None
    # Different case → no match under raw mode.
    assert index.apply(CellContext("S", "C", "Male")) is None
    # Extra whitespace → no match under raw mode.
    assert index.apply(CellContext("S", "C", " male ")) is None


def test_exact_normalized_matches_case_and_whitespace_variants() -> None:
    index = RuleIndex([
        CleaningRule(
            source_value="male",
            target_value="1",
            match_mode=MatchMode.EXACT_NORMALIZED,
            scope_type=ScopeType.GLOBAL,
        ),
    ])
    for variant in ("male", "Male", "MALE", "  male  ", "\tmale\n"):
        app = index.apply(CellContext("S", "C", variant))
        assert app is not None, f"Variant {variant!r} should have matched"
        assert app.target_value == "1"


# --------------------------------------------------------------------------- #
# Scope priority — column > sheet > global
# --------------------------------------------------------------------------- #

def test_column_scope_wins_over_global() -> None:
    """A column-scoped rule for the same value should override a global one."""
    rules = [
        CleaningRule(
            source_value="1",
            target_value="global_hit",
            scope_type=ScopeType.GLOBAL,
            match_mode=MatchMode.EXACT_RAW,
        ),
        CleaningRule(
            source_value="1",
            target_value="column_hit",
            scope_type=ScopeType.COLUMN,
            scope_sheet="Survey",
            scope_column="Gender",
            match_mode=MatchMode.EXACT_RAW,
        ),
    ]
    index = RuleIndex(rules)
    app = index.apply(CellContext("Survey", "Gender", "1"))
    assert app is not None
    assert app.target_value == "column_hit"


def test_sheet_scope_wins_over_global() -> None:
    rules = [
        CleaningRule(
            source_value="x",
            target_value="global",
            scope_type=ScopeType.GLOBAL,
            match_mode=MatchMode.EXACT_RAW,
        ),
        CleaningRule(
            source_value="x",
            target_value="sheet",
            scope_type=ScopeType.SHEET,
            scope_sheet="Survey",
            match_mode=MatchMode.EXACT_RAW,
        ),
    ]
    index = RuleIndex(rules)
    app = index.apply(CellContext("Survey", "A", "x"))
    assert app is not None
    assert app.target_value == "sheet"


def test_sheet_scope_does_not_leak_to_other_sheets() -> None:
    rules = [
        CleaningRule(
            source_value="male",
            target_value="1",
            scope_type=ScopeType.SHEET,
            scope_sheet="A",
            match_mode=MatchMode.EXACT_RAW,
        ),
    ]
    index = RuleIndex(rules)
    assert index.apply(CellContext("A", "X", "male")) is not None
    assert index.apply(CellContext("B", "X", "male")) is None


def test_column_scope_does_not_leak_to_other_columns() -> None:
    rules = [
        CleaningRule(
            source_value="1",
            target_value="hit",
            scope_type=ScopeType.COLUMN,
            scope_sheet="S",
            scope_column="Gender",
            match_mode=MatchMode.EXACT_RAW,
        ),
    ]
    index = RuleIndex(rules)
    assert index.apply(CellContext("S", "Gender", "1")) is not None
    assert index.apply(CellContext("S", "Response", "1")) is None


def test_raw_wins_over_normalized_at_same_scope() -> None:
    """If both match, EXACT_RAW at the same scope tier takes priority."""
    rules = [
        CleaningRule(
            source_value="Male",
            target_value="raw_hit",
            scope_type=ScopeType.GLOBAL,
            match_mode=MatchMode.EXACT_RAW,
        ),
        CleaningRule(
            source_value="male",
            target_value="norm_hit",
            scope_type=ScopeType.GLOBAL,
            match_mode=MatchMode.EXACT_NORMALIZED,
        ),
    ]
    index = RuleIndex(rules)
    app = index.apply(CellContext("S", "C", "Male"))
    assert app is not None
    assert app.target_value == "raw_hit"


# --------------------------------------------------------------------------- #
# Disabled / invalid rules
# --------------------------------------------------------------------------- #

def test_disabled_rules_are_ignored() -> None:
    index = RuleIndex([
        CleaningRule(
            source_value="male",
            target_value="1",
            scope_type=ScopeType.GLOBAL,
            match_mode=MatchMode.EXACT_RAW,
            enabled=False,
        ),
    ])
    assert index.apply(CellContext("S", "C", "male")) is None


def test_invalid_rules_are_ignored() -> None:
    # An empty source is invalid. The index must silently drop it
    # rather than crash or match everything.
    bad = CleaningRule(
        source_value="",
        target_value="x",
        scope_type=ScopeType.GLOBAL,
    )
    index = RuleIndex([bad])
    assert index.active_rule_count == 0
    assert index.apply(CellContext("S", "C", "anything")) is None


# --------------------------------------------------------------------------- #
# Actions
# --------------------------------------------------------------------------- #

def test_set_blank_action_marks_cell_for_clear() -> None:
    index = RuleIndex([
        CleaningRule(
            source_value="N/A",
            action_type=ActionType.SET_BLANK,
            match_mode=MatchMode.EXACT_NORMALIZED,
            scope_type=ScopeType.GLOBAL,
        ),
    ])
    app = index.apply(CellContext("S", "C", "n/a"))
    assert app is not None
    assert app.clear_cell is True


def test_map_code_treated_as_replace_for_write_semantics() -> None:
    index = RuleIndex([
        CleaningRule(
            source_value="male",
            target_value="1",
            action_type=ActionType.MAP_CODE,
            match_mode=MatchMode.EXACT_NORMALIZED,
            scope_type=ScopeType.GLOBAL,
        ),
    ])
    app = index.apply(CellContext("S", "C", "Male"))
    assert app is not None
    assert app.clear_cell is False
    assert app.target_value == "1"
