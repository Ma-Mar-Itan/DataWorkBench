"""
Rules engine.

Core guarantee (non-negotiable):
  ALL matching is whole-cell. We compare either the full raw cell value
  to the rule's source_value, or the full normalized cell value to the
  normalized source_value. We never do substring or token matching.
  Therefore replacing "Home" cannot affect "Homework", and replacing a
  short Arabic word cannot affect a longer Arabic phrase that contains it.

Precedence (when multiple enabled rules match a single cell):
  1. Scope narrowness: column  >  sheet  >  workbook
  2. Match mode:       exact_raw  >  exact_normalized
  3. Creation order:   earlier-created rule wins

Formula cells are skipped by default — we never rewrite an '=SUM(...)'
cell even if the cached value matches.

The engine is stateless: `apply_rules` receives rules + workbook, returns
an ApplyResult plus (optionally) mutates the underlying openpyxl workbook
so the exporter can write it out.
"""
from __future__ import annotations

from typing import Iterable

from models.enums import ActionType, MatchMode, ScopeType
from models.schemas import ApplyResult, CellChange, Rule

from .normalizer import normalize, to_text
from .workbook_reader import LoadedWorkbook, is_formula_cell


# --------------------------------------------------------------------- #
# Precedence
# --------------------------------------------------------------------- #
_SCOPE_RANK = {
    ScopeType.COLUMN:   0,
    ScopeType.SHEET:    1,
    ScopeType.WORKBOOK: 2,
}
_MATCH_RANK = {
    MatchMode.EXACT_RAW:        0,
    MatchMode.EXACT_NORMALIZED: 1,
}


def _precedence_key(rule: Rule) -> tuple[int, int, int]:
    return (
        _SCOPE_RANK[rule.scope_type],
        _MATCH_RANK[rule.match_mode],
        rule.created_at,
    )


def _rule_applies_to_location(rule: Rule, sheet: str, column: str) -> bool:
    """True if the rule's scope covers the given (sheet, column)."""
    if rule.scope_type is ScopeType.WORKBOOK:
        return True
    if rule.scope_type is ScopeType.SHEET:
        return rule.scope_sheet == sheet
    if rule.scope_type is ScopeType.COLUMN:
        return rule.scope_sheet == sheet and rule.scope_column == column
    return False


def _rule_matches_value(rule: Rule, raw: str) -> bool:
    """
    Whole-cell match check. Returns True if the cell value matches the
    rule's source_value under the rule's match_mode.
    """
    if rule.match_mode is MatchMode.EXACT_RAW:
        return raw == rule.source_value
    if rule.match_mode is MatchMode.EXACT_NORMALIZED:
        return normalize(raw) == normalize(rule.source_value)
    return False


def find_matching_rule(
    rules: list[Rule],
    sheet: str,
    column: str,
    raw: str,
) -> Rule | None:
    """
    Return the single rule that wins precedence for this cell, or None.
    """
    candidates = [
        r for r in rules
        if r.enabled
        and _rule_applies_to_location(r, sheet, column)
        and _rule_matches_value(r, raw)
    ]
    if not candidates:
        return None
    candidates.sort(key=_precedence_key)
    return candidates[0]


# --------------------------------------------------------------------- #
# Apply
# --------------------------------------------------------------------- #
def apply_rules(
    loaded: LoadedWorkbook,
    rules: Iterable[Rule],
    *,
    mutate_workbook: bool = True,
    skip_formulas: bool = True,
) -> ApplyResult:
    """
    Apply the ruleset.

    If `mutate_workbook` is True, the underlying openpyxl Workbook is
    edited in place so the exporter can write it back. The pandas
    DataFrames are always updated so downstream stats reflect the change.

    Returns an ApplyResult describing every change.
    """
    rule_list = list(rules)
    result = ApplyResult()

    for sheet_name, df in loaded.dataframes.items():
        if df.empty:
            continue
        ws = loaded.wb[sheet_name] if mutate_workbook else None

        for col_index, col in enumerate(df.columns):
            # A cheap filter: skip whole columns for which no enabled rule
            # is in scope. For large workbooks this matters.
            col_rules = [
                r for r in rule_list
                if r.enabled and _rule_applies_to_location(r, sheet_name, col)
            ]
            if not col_rules:
                continue

            for row_index, value in enumerate(df[col]):
                raw = "" if value is None else to_text(value)

                rule = find_matching_rule(col_rules, sheet_name, col, raw)
                if rule is None:
                    continue

                # Determine the target value
                if rule.action_type is ActionType.SET_BLANK:
                    new_value: object = ""
                elif rule.action_type is ActionType.REPLACE:
                    new_value = rule.target_value
                else:
                    continue

                if new_value == raw:
                    continue  # no-op

                # openpyxl cell: row 1 is header, data starts row 2
                if ws is not None:
                    cell = ws.cell(row=row_index + 2, column=col_index + 1)
                    if skip_formulas and is_formula_cell(cell):
                        continue   # don't disturb formulas
                    cell.value = new_value if new_value != "" else None

                # Always update the DataFrame so stats see the change.
                # Cast column to object first if the new value's type doesn't
                # match — pandas otherwise raises on int64-to-str writes.
                new_cell = new_value if new_value != "" else None
                col_name = df.columns[col_index]
                try:
                    df.iat[row_index, col_index] = new_cell
                except (TypeError, ValueError):
                    df[col_name] = df[col_name].astype(object)
                    df.iat[row_index, col_index] = new_cell

                result.changes.append(CellChange(
                    sheet=sheet_name,
                    row=row_index + 2,
                    column=col,
                    before=value,
                    after=new_value,
                    rule_id=rule.rule_id,
                ))
                result.fires_per_rule[rule.rule_id] = result.fires_per_rule.get(rule.rule_id, 0) + 1
                result.affected_sheets.add(sheet_name)
                result.affected_columns.add(f"{sheet_name}::{col}")

    return result
