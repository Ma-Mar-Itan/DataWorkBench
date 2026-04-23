"""
Descriptive statistics engine.

Everything returned here is derived from the pandas DataFrames held on
the LoadedWorkbook. Type inference decides which flavor of summary a
column gets.

Intentionally simple numerics (via pandas .describe() / quantile()) and
intentionally conservative categorical summaries (normalized counts so
"Male", "male  ", "MALE" collapse into one bucket when appropriate).
"""
from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd

from models.enums import ColumnType
from models.schemas import (
    BeforeAfterSummary, CategoricalStats, ColumnInference,
    NumericStats, WorkbookMeta,
)

from .normalizer import is_missing_token, normalize, to_text
from .type_inference import infer_column_type
from .workbook_reader import LoadedWorkbook


# --------------------------------------------------------------------- #
# Workbook-level summary
# --------------------------------------------------------------------- #
def workbook_summary(loaded: LoadedWorkbook) -> dict[str, Any]:
    total_missing = 0
    total_unique: set[str] = set()
    per_sheet: list[dict[str, Any]] = []

    for sheet_name, df in loaded.dataframes.items():
        sheet_missing = 0
        for col in df.columns:
            for v in df[col]:
                if v is None or (isinstance(v, float) and pd.isna(v)) or is_missing_token(v):
                    sheet_missing += 1
                else:
                    total_unique.add(to_text(v))
        total_missing += sheet_missing
        per_sheet.append({
            "sheet":   sheet_name,
            "rows":    len(df),
            "cols":    len(df.columns),
            "missing": sheet_missing,
        })

    return {
        "sheet_count":         loaded.meta.sheet_count,
        "total_rows":          loaded.meta.total_rows,
        "total_cols":          loaded.meta.total_cols,
        "total_missing":       total_missing,
        "total_unique_values": len(total_unique),
        "per_sheet":           per_sheet,
    }


# --------------------------------------------------------------------- #
# Per-column inference
# --------------------------------------------------------------------- #
def infer_all_columns(loaded: LoadedWorkbook) -> list[ColumnInference]:
    out: list[ColumnInference] = []
    for sheet_name, df in loaded.dataframes.items():
        for col in df.columns:
            dtype = infer_column_type(df[col].tolist())
            out.append(ColumnInference(sheet=sheet_name, column=col, dtype=dtype))
    return out


# --------------------------------------------------------------------- #
# Numeric
# --------------------------------------------------------------------- #
def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        try:
            return float(v) if not pd.isna(v) else None
        except Exception:
            return None
    if isinstance(v, str):
        s = v.strip().replace(",", "")
        if s == "" or is_missing_token(s):
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def numeric_stats(loaded: LoadedWorkbook) -> list[NumericStats]:
    inferred = {(ci.sheet, ci.column): ci.dtype for ci in infer_all_columns(loaded)}
    out: list[NumericStats] = []

    for sheet_name, df in loaded.dataframes.items():
        for col in df.columns:
            if inferred.get((sheet_name, col)) is not ColumnType.NUMERIC:
                continue
            floats = [_to_float(v) for v in df[col]]
            clean  = [f for f in floats if f is not None]
            missing = len(floats) - len(clean)

            if not clean:
                out.append(NumericStats(
                    column=col, sheet=sheet_name,
                    count=0, missing=missing,
                    mean=None, median=None, std=None,
                    min_=None, q1=None, q3=None, max_=None,
                ))
                continue

            s = pd.Series(clean)
            out.append(NumericStats(
                column=col, sheet=sheet_name,
                count=len(clean),
                missing=missing,
                mean=float(s.mean()),
                median=float(s.median()),
                std=float(s.std(ddof=1)) if len(clean) > 1 else 0.0,
                min_=float(s.min()),
                q1=float(s.quantile(0.25)),
                q3=float(s.quantile(0.75)),
                max_=float(s.max()),
            ))
    return out


# --------------------------------------------------------------------- #
# Categorical
# --------------------------------------------------------------------- #
def categorical_stats(
    loaded: LoadedWorkbook,
    top_n: int = 5,
) -> list[CategoricalStats]:
    inferred = {(ci.sheet, ci.column): ci.dtype for ci in infer_all_columns(loaded)}
    out: list[CategoricalStats] = []

    for sheet_name, df in loaded.dataframes.items():
        for col in df.columns:
            if inferred.get((sheet_name, col)) is not ColumnType.CATEGORICAL:
                continue

            non_missing_raw: list[str] = []
            missing = 0
            for v in df[col]:
                if v is None or (isinstance(v, float) and pd.isna(v)) or is_missing_token(v):
                    missing += 1
                else:
                    non_missing_raw.append(to_text(v))

            non_missing = len(non_missing_raw)
            if non_missing == 0:
                out.append(CategoricalStats(
                    column=col, sheet=sheet_name,
                    non_missing=0, missing=missing, unique=0,
                    mode=None, top_values=[],
                ))
                continue

            # Count by normalized form, but keep the most common *raw*
            # representation of each bucket as its display value.
            by_norm: dict[str, Counter] = {}
            for raw in non_missing_raw:
                n = normalize(raw)
                by_norm.setdefault(n, Counter())[raw] += 1

            buckets: list[tuple[str, int]] = []
            for n, raw_counter in by_norm.items():
                display = raw_counter.most_common(1)[0][0]
                buckets.append((display, sum(raw_counter.values())))
            buckets.sort(key=lambda kv: -kv[1])

            total = sum(c for _, c in buckets)
            top = [
                (raw, cnt, (cnt / total * 100.0) if total else 0.0)
                for raw, cnt in buckets[:top_n]
            ]

            out.append(CategoricalStats(
                column=col, sheet=sheet_name,
                non_missing=non_missing, missing=missing,
                unique=len(buckets),
                mode=buckets[0][0],
                top_values=top,
            ))
    return out


# --------------------------------------------------------------------- #
# Missingness
# --------------------------------------------------------------------- #
def missingness(loaded: LoadedWorkbook) -> list[dict[str, Any]]:
    out = []
    for sheet_name, df in loaded.dataframes.items():
        for col in df.columns:
            total = len(df[col])
            if total == 0:
                continue
            missing = sum(
                1 for v in df[col]
                if v is None or (isinstance(v, float) and pd.isna(v)) or is_missing_token(v)
            )
            out.append({
                "sheet":   sheet_name,
                "column":  col,
                "missing": missing,
                "total":   total,
                "pct":     (missing / total * 100.0) if total else 0.0,
            })
    out.sort(key=lambda d: -d["pct"])
    return out


# --------------------------------------------------------------------- #
# Before vs after
# --------------------------------------------------------------------- #
def before_after(
    before: LoadedWorkbook,
    after: LoadedWorkbook,
    apply_result,
) -> BeforeAfterSummary:
    """
    Summarize the impact of a cleaning pass.

    We compute category-reduction by comparing normalized unique counts
    per categorical column before vs after.
    """
    inferred = {(ci.sheet, ci.column): ci.dtype for ci in infer_all_columns(before)}

    cat_reduction: dict[str, tuple[int, int]] = {}
    for (sheet, col), dtype in inferred.items():
        if dtype is not ColumnType.CATEGORICAL:
            continue
        before_vals = before.dataframes[sheet][col]
        after_vals  = after.dataframes[sheet][col]
        b = {normalize(v) for v in before_vals if not is_missing_token(v) and v is not None}
        a = {normalize(v) for v in after_vals  if not is_missing_token(v) and v is not None}
        if len(b) != len(a):
            cat_reduction[f"{sheet}.{col}"] = (len(b), len(a))

    # "Missing added" = cells that became blank via set_blank
    missing_added = sum(
        1 for ch in apply_result.changes
        if ch.after in (None, "", "nan")
    )

    return BeforeAfterSummary(
        changed_cells=apply_result.changed_cells,
        affected_sheets=len(apply_result.affected_sheets),
        affected_columns=len(apply_result.affected_columns),
        category_reduction=cat_reduction,
        missing_added=missing_added,
    )
