"""
Adapter between the Streamlit UI and the core backend.

The UI imports ONLY from this module, not from core/* directly. That
keeps the dependency graph clean: UI → integration → core. If the core
engine ever changes shape, only this file needs to be updated.

Every function here mirrors a UI action. Each returns plain dicts /
dataclasses so the views don't need to know about openpyxl or engine
internals.
"""
from __future__ import annotations

import time
from io import BytesIO
from typing import Any

from core.exporter import (
    export_cleaned_workbook, export_ruleset, export_stats_report,
)
from core.preview_engine import preview
from core.rules_engine import apply_rules
from core.ruleset_store import load_ruleset, save_ruleset
from core.scanner import scan_workbook
from core.stats_engine import (
    before_after, categorical_stats, missingness, numeric_stats,
    workbook_summary,
)
from core.workbook_reader import LoadedWorkbook, load_workbook_from_bytes
from models.enums import ActionType, MatchMode, ScopeType
from models.schemas import Rule


# --------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------- #
def load(data: bytes, filename: str) -> LoadedWorkbook:
    return load_workbook_from_bytes(data, filename=filename)


# --------------------------------------------------------------------- #
# Scan — shaped for the UI scan view
# --------------------------------------------------------------------- #
def scan(loaded: LoadedWorkbook) -> dict[str, Any]:
    result = scan_workbook(loaded)
    summary = {
        "sheets":               result.workbook.sheet_count,
        "rows":                 result.workbook.total_rows,
        "columns":              result.workbook.total_cols,
        "unique_string_values": result.workbook.total_unique_strings,
        "missing_tokens":       result.workbook.total_missing_tokens,
    }
    table = [
        {
            "value":      v.raw_value,
            "normalized": v.normalized_value,
            "count":      v.total_count,
            "sheets":     ", ".join(sorted(v.per_sheet.keys())),
            "columns":    ", ".join(sorted({k.split("::", 1)[1] for k in v.per_column})),
            "class":      v.value_class.value,
        }
        for v in result.values
    ]
    return {"summary": summary, "values": table}


# --------------------------------------------------------------------- #
# Rules — dict ↔ Rule conversion
# --------------------------------------------------------------------- #
def rules_from_dicts(dicts: list[dict]) -> list[Rule]:
    """Convert UI-editor dicts into typed Rule objects."""
    rules: list[Rule] = []
    for i, d in enumerate(dicts):
        rules.append(Rule(
            rule_id=str(d.get("rule_id") or f"r{i}"),
            source_value=str(d.get("source_value", "")),
            target_value=str(d.get("target_value", "")),
            action_type=ActionType(d.get("action_type") or ActionType.REPLACE.value),
            match_mode=MatchMode(d.get("match_mode") or MatchMode.EXACT_NORMALIZED.value),
            scope_type=ScopeType(d.get("scope_type") or ScopeType.WORKBOOK.value),
            scope_sheet=str(d.get("scope_sheet") or ""),
            scope_column=str(d.get("scope_column") or ""),
            enabled=bool(d.get("enabled", True)),
            created_at=int(d.get("created_at") or i),
        ))
    return rules


def rules_to_dicts(rules: list[Rule]) -> list[dict]:
    return [r.to_dict() for r in rules]


# --------------------------------------------------------------------- #
# Preview
# --------------------------------------------------------------------- #
def run_preview(loaded: LoadedWorkbook, rule_dicts: list[dict], sheet: str | None = None) -> dict:
    rules = rules_from_dicts(rule_dicts)
    result = preview(loaded, rules, sheet=sheet)
    return {
        "changed_cells":    result.changed_cells,
        "affected_sheets":  sorted(result.affected_sheets),
        "affected_columns": sorted(result.affected_columns),
        "fires_per_rule":   dict(result.fires_per_rule),
        "changes": [
            {"row": c.row, "column": c.column, "sheet": c.sheet,
             "before": c.before, "after": c.after, "rule": c.rule_id}
            for c in result.changes
        ],
    }


# --------------------------------------------------------------------- #
# Apply (destructive)
# --------------------------------------------------------------------- #
def run_apply(loaded: LoadedWorkbook, rule_dicts: list[dict]) -> dict:
    rules = rules_from_dicts(rule_dicts)
    result = apply_rules(loaded, rules, mutate_workbook=True, skip_formulas=True)
    return {
        "changed_cells":    result.changed_cells,
        "affected_sheets":  sorted(result.affected_sheets),
        "affected_columns": sorted(result.affected_columns),
    }


# --------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------- #
def compute_statistics(loaded: LoadedWorkbook) -> dict:
    return {
        "summary":     workbook_summary(loaded),
        "numeric":     [n.__dict__ for n in numeric_stats(loaded)],
        "categorical": [
            {**c.__dict__, "top_values": c.top_values}
            for c in categorical_stats(loaded)
        ],
        "missingness": missingness(loaded),
    }


def compute_before_after(before_wb: LoadedWorkbook, after_wb: LoadedWorkbook, rule_dicts: list[dict]) -> dict:
    rules = rules_from_dicts(rule_dicts)
    # Preview on `before` copy; the result is the apply result
    result = preview(before_wb, rules)
    ba = before_after(before_wb, after_wb, result)
    return ba.__dict__


# --------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------- #
def export_workbook_bytes(loaded: LoadedWorkbook) -> bytes:
    return export_cleaned_workbook(loaded)


def export_stats_bytes(loaded: LoadedWorkbook) -> bytes:
    return export_stats_report(
        workbook_summary=workbook_summary(loaded),
        numeric=numeric_stats(loaded),
        categorical=categorical_stats(loaded),
        missing_rows=missingness(loaded),
        before_after=None,
    )


def export_ruleset_bytes(rule_dicts: list[dict]) -> bytes:
    rules = rules_from_dicts(rule_dicts)
    return export_ruleset(rules, metadata={"exported_at": int(time.time())})


# --------------------------------------------------------------------- #
# Ruleset save/load
# --------------------------------------------------------------------- #
def save_rules_json(rule_dicts: list[dict], metadata: dict | None = None) -> str:
    rules = rules_from_dicts(rule_dicts)
    return save_ruleset(rules, metadata=metadata)


def load_rules_json(text: str) -> list[dict]:
    rules, _meta = load_ruleset(text)
    return rules_to_dicts(rules)
