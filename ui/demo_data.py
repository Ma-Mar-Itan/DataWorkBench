"""
Demo/mock data that mirrors the real backend schema.

The frontend renders against these structures. Once the real engine is
wired in, the views swap `demo_*` calls for real calls without changing
the component layer.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


# --------------------------------------------------------------------- #
# Workbook metadata
# --------------------------------------------------------------------- #
def demo_workbook_meta() -> dict:
    return {
        "filename":       "customer_survey_q3.xlsx",
        "size_bytes":     482_116,
        "sheet_count":    4,
        "row_count":      12_438,
        "column_count":   27,
        "uploaded_at":    "2026-04-23 11:02",
        "sheets": [
            {"name": "Responses",   "rows": 8_912, "cols": 14},
            {"name": "Demographics","rows": 3_104, "cols": 8},
            {"name": "Free text",   "rows":   290, "cols": 3},
            {"name": "Lookup",      "rows":   132, "cols": 2},
        ],
    }


# --------------------------------------------------------------------- #
# Scan summary + repeated values
# --------------------------------------------------------------------- #
def demo_scan_summary() -> dict:
    return {
        "sheets":               4,
        "rows":                 12_438,
        "columns":              27,
        "unique_string_values": 1_842,
        "missing_tokens":       318,
    }


def demo_repeated_values() -> list[dict]:
    """Repeated values found during scan."""
    return [
        {"value": "Male",        "normalized": "male",        "count": 4_201, "sheets": "Responses, Demographics", "columns": "gender", "class": "categorical"},
        {"value": "Female",      "normalized": "female",      "count": 3_987, "sheets": "Responses, Demographics", "columns": "gender", "class": "categorical"},
        {"value": "N/A",         "normalized": "n/a",         "count":   214, "sheets": "Responses",              "columns": "region, income", "class": "missing"},
        {"value": "  N/A ",      "normalized": "n/a",         "count":    48, "sheets": "Responses",              "columns": "region", "class": "missing"},
        {"value": "unknown",     "normalized": "unknown",     "count":    92, "sheets": "Demographics",           "columns": "employer", "class": "missing"},
        {"value": "Yes",         "normalized": "yes",         "count": 2_311, "sheets": "Responses",              "columns": "consent, subscribed", "class": "categorical"},
        {"value": "yes",         "normalized": "yes",         "count":    87, "sheets": "Responses",              "columns": "consent", "class": "categorical"},
        {"value": "No",          "normalized": "no",          "count": 1_902, "sheets": "Responses",              "columns": "consent, subscribed", "class": "categorical"},
        {"value": "USA",         "normalized": "usa",         "count": 1_231, "sheets": "Demographics",           "columns": "country", "class": "categorical"},
        {"value": "U.S.A.",      "normalized": "u.s.a.",      "count":    64, "sheets": "Demographics",           "columns": "country", "class": "categorical"},
        {"value": "United States","normalized":"united states","count":   118, "sheets": "Demographics",           "columns": "country", "class": "categorical"},
        {"value": "ذكر",          "normalized": "ذكر",         "count":   187, "sheets": "Demographics",           "columns": "gender_ar", "class": "categorical"},
        {"value": "أنثى",          "normalized": "أنثى",        "count":   203, "sheets": "Demographics",           "columns": "gender_ar", "class": "categorical"},
        {"value": "-",            "normalized": "-",          "count":    41, "sheets": "Responses",              "columns": "notes", "class": "missing"},
        {"value": "Student",      "normalized": "student",    "count":   612, "sheets": "Demographics",           "columns": "occupation", "class": "categorical"},
    ]


# --------------------------------------------------------------------- #
# Rules
# --------------------------------------------------------------------- #
def demo_rules() -> list[dict]:
    return [
        {
            "rule_id":       "r1",
            "source_value":  "N/A",
            "target_value":  "",
            "action_type":   "set_blank",
            "match_mode":    "exact_normalized",
            "scope_type":    "workbook",
            "scope_sheet":   "",
            "scope_column":  "",
            "enabled":       True,
        },
        {
            "rule_id":       "r2",
            "source_value":  "yes",
            "target_value":  "Yes",
            "action_type":   "replace",
            "match_mode":    "exact_normalized",
            "scope_type":    "column",
            "scope_sheet":   "Responses",
            "scope_column":  "consent",
            "enabled":       True,
        },
        {
            "rule_id":       "r3",
            "source_value":  "U.S.A.",
            "target_value":  "USA",
            "action_type":   "replace",
            "match_mode":    "exact_raw",
            "scope_type":    "column",
            "scope_sheet":   "Demographics",
            "scope_column":  "country",
            "enabled":       True,
        },
        {
            "rule_id":       "r4",
            "source_value":  "United States",
            "target_value":  "USA",
            "action_type":   "replace",
            "match_mode":    "exact_raw",
            "scope_type":    "column",
            "scope_sheet":   "Demographics",
            "scope_column":  "country",
            "enabled":       False,
        },
    ]


def new_rule() -> dict:
    return {
        "rule_id":       f"r-{uuid.uuid4().hex[:6]}",
        "source_value":  "",
        "target_value":  "",
        "action_type":   "replace",
        "match_mode":    "exact_normalized",
        "scope_type":    "workbook",
        "scope_sheet":   "",
        "scope_column":  "",
        "enabled":       True,
    }


# --------------------------------------------------------------------- #
# Preview
# --------------------------------------------------------------------- #
def demo_preview_rows(sheet: str) -> list[dict]:
    base = [
        {"row": 12,  "column": "consent",  "before": "yes",        "after": "Yes", "rule": "r2"},
        {"row": 47,  "column": "country",  "before": "U.S.A.",     "after": "USA", "rule": "r3"},
        {"row": 81,  "column": "region",   "before": "N/A",        "after": "",    "rule": "r1"},
        {"row": 112, "column": "income",   "before": "N/A",        "after": "",    "rule": "r1"},
        {"row": 204, "column": "consent",  "before": "yes",        "after": "Yes", "rule": "r2"},
        {"row": 318, "column": "country",  "before": "U.S.A.",     "after": "USA", "rule": "r3"},
        {"row": 402, "column": "region",   "before": "  N/A ",     "after": "",    "rule": "r1"},
    ]
    return base


def demo_rules_summary() -> list[dict]:
    return [
        {"rule_id": "r1", "fires": 262, "label": "N/A → (blank) — workbook"},
        {"rule_id": "r2", "fires":  87, "label": "yes → Yes — Responses.consent"},
        {"rule_id": "r3", "fires":  64, "label": "U.S.A. → USA — Demographics.country"},
    ]


# --------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------- #
def demo_numeric_stats() -> list[dict]:
    return [
        {"column": "age",           "sheet": "Demographics", "count": 3_098, "missing":  6, "mean": 41.2, "median": 39, "std": 12.8, "min": 18, "q1": 31, "q3": 52, "max": 84},
        {"column": "income",        "sheet": "Demographics", "count": 2_874, "missing":230, "mean": 62_430, "median": 58_000, "std": 24_111, "min": 0, "q1": 42_000, "q3": 78_000, "max": 245_000},
        {"column": "score",         "sheet": "Responses",    "count": 8_901, "missing": 11, "mean":  7.4, "median":  8, "std":  1.9, "min":  0, "q1":  6, "q3":  9, "max": 10},
        {"column": "tenure_years",  "sheet": "Demographics", "count": 3_040, "missing": 64, "mean":  6.1, "median":  5, "std":  4.2, "min":  0, "q1":  2, "q3":  9, "max": 38},
    ]


def demo_categorical_stats() -> list[dict]:
    return [
        {"column": "gender",     "sheet": "Demographics", "non_missing": 3_100, "missing":  4, "unique": 2, "mode": "Female", "top": "Female 50.8% · Male 49.2%"},
        {"column": "country",    "sheet": "Demographics", "non_missing": 3_050, "missing": 54, "unique": 38, "mode": "USA",    "top": "USA 40% · UK 12% · DE 9%"},
        {"column": "consent",    "sheet": "Responses",    "non_missing": 8_801, "missing":111, "unique": 2, "mode": "Yes",    "top": "Yes 54.8% · No 45.2%"},
        {"column": "occupation", "sheet": "Demographics", "non_missing": 3_012, "missing": 92, "unique": 47, "mode": "Employed", "top": "Employed 48% · Student 20% · Retired 14%"},
    ]


def demo_missingness() -> list[dict]:
    return [
        {"sheet": "Responses",    "column": "notes",      "missing": 4_122, "total": 8_912, "pct": 46.2},
        {"sheet": "Demographics", "column": "income",     "missing":   230, "total": 3_104, "pct":  7.4},
        {"sheet": "Responses",    "column": "score",      "missing":    11, "total": 8_912, "pct":  0.1},
        {"sheet": "Demographics", "column": "age",        "missing":     6, "total": 3_104, "pct":  0.2},
        {"sheet": "Free text",    "column": "complaint",  "missing":    24, "total":   290, "pct":  8.3},
    ]


def demo_before_after() -> dict:
    return {
        "changed_cells":    413,
        "affected_sheets":  3,
        "affected_columns": 7,
        "category_reduction": "country: 38 → 34 categories",
        "missing_added":    262,   # cells blanked via set_blank
    }
