"""Tests for the preview builder."""

from __future__ import annotations

from core.preview import build_preview, list_sheet_names
from models.schemas import ActionType, CleaningRule, MatchMode, ScopeType


def test_list_sheet_names(survey_workbook_bytes: bytes) -> None:
    assert list_sheet_names(survey_workbook_bytes) == ["Survey"]


def test_build_preview_shapes_match(survey_workbook_bytes: bytes) -> None:
    rules = [CleaningRule(
        source_value="male", target_value="1",
        action_type=ActionType.MAP_CODE,
        match_mode=MatchMode.EXACT_NORMALIZED,
        scope_type=ScopeType.COLUMN,
        scope_sheet="Survey",
        scope_column="Gender",
    )]
    orig, clean, mask = build_preview(survey_workbook_bytes, "Survey", rules, max_rows=50)
    assert orig.shape == clean.shape == mask.shape
    assert not orig.empty


def test_preview_changed_mask_is_accurate(survey_workbook_bytes: bytes) -> None:
    rules = [CleaningRule(
        source_value="male", target_value="1",
        action_type=ActionType.MAP_CODE,
        match_mode=MatchMode.EXACT_NORMALIZED,
        scope_type=ScopeType.COLUMN,
        scope_sheet="Survey",
        scope_column="Gender",
    )]
    orig, clean, mask = build_preview(survey_workbook_bytes, "Survey", rules, max_rows=50)

    # Find the Gender column by name.
    gender_col = next(c for c in orig.columns if c == "Gender")

    # Row 2 of the workbook is index 1 here (row 1 is the header).
    # "male" → "1": should be marked changed.
    assert mask.loc[1, gender_col] is True or mask.loc[1, gender_col] == True  # noqa: E712
    assert clean.loc[1, gender_col] == "1"

    # The Note column free-text "male student…" must NOT be marked changed.
    note_col = next(c for c in orig.columns if c == "Note")
    assert mask.loc[1, note_col] is False or mask.loc[1, note_col] == False  # noqa: E712


def test_preview_respects_formula_skip(survey_workbook_bytes: bytes) -> None:
    """A rule that would otherwise match inside a formula must not mark it changed."""
    rules = [CleaningRule(
        source_value="CONCATENATE",
        target_value="X",
        match_mode=MatchMode.EXACT_NORMALIZED,
        scope_type=ScopeType.GLOBAL,
    )]
    orig, clean, mask = build_preview(survey_workbook_bytes, "Survey", rules, max_rows=50)
    # The formula cell is A8 → row index 7. The 'changed' flag must be False.
    import pandas as pd  # local import so the test file stays tight
    # Total changes should be zero.
    assert int(mask.sum().sum()) == 0
