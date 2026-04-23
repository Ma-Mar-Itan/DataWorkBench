"""
Preview engine.

Runs the rule engine against a *copy* of the workbook so the user can
review what would change before committing. Returns the same ApplyResult
shape as the real engine, but the original LoadedWorkbook is untouched.

Design: we make a shallow copy of the LoadedWorkbook wrapper and deep-
copy the DataFrames. We do NOT deep-copy the openpyxl workbook — that's
expensive and unnecessary for preview, because we pass
`mutate_workbook=False` to the engine.
"""
from __future__ import annotations

import copy
from typing import Iterable

from models.schemas import ApplyResult, Rule

from .rules_engine import apply_rules
from .workbook_reader import LoadedWorkbook


def preview(
    loaded: LoadedWorkbook,
    rules: Iterable[Rule],
    sheet: str | None = None,
) -> ApplyResult:
    """
    Return the changes that the ruleset *would* produce.

    If `sheet` is provided, only that sheet is considered. The original
    workbook is not modified.
    """
    # Shallow copy the wrapper, then deep-copy the DataFrames we'll
    # actually touch. The openpyxl Workbook refs are reused untouched
    # because we pass mutate_workbook=False.
    preview_loaded = copy.copy(loaded)
    preview_loaded.dataframes = {
        name: df.copy(deep=True)
        for name, df in loaded.dataframes.items()
        if sheet is None or name == sheet
    }

    return apply_rules(
        preview_loaded,
        rules,
        mutate_workbook=False,
        skip_formulas=True,
    )


def changes_for_sheet(result: ApplyResult, sheet: str) -> list:
    """Filter an ApplyResult's changes to a single sheet."""
    return [c for c in result.changes if c.sheet == sheet]
