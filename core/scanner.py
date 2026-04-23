"""
Scan engine.

Walks every sheet and builds:
  - a map of (raw_value, normalized_value) -> ValueOccurrence
  - workbook-level totals

For each unique raw string value we record total count, per-sheet and
per-column counts, a few example coordinates, and a value class.

Performance note: we iterate the pandas DataFrames, not openpyxl cells.
DataFrame iteration is ~10x faster, and we only need positions for a
handful of examples per value, which we can derive from row/column index.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd

from models.enums import ValueClass
from models.schemas import (
    CellCoord, ScanResult, ValueOccurrence, WorkbookMeta,
)

from .normalizer import MISSING_TOKENS, is_missing_token, normalize, to_text
from .type_inference import _looks_date, _looks_numeric
from .workbook_reader import LoadedWorkbook


# How many example coordinates to keep per value
_MAX_EXAMPLES = 5


def scan_workbook(loaded: LoadedWorkbook, low_freq_threshold: int = 2) -> ScanResult:
    """
    Produce a full ScanResult for a loaded workbook.

    `low_freq_threshold`: values with count <= this are marked
    LOW_FREQUENCY (useful for triaging typos/singletons).
    """
    # Aggregate by raw value string; each raw value has exactly one
    # normalized form, so it's a safe key.
    occurrences: dict[str, ValueOccurrence] = {}
    missing_token_count = 0

    for sheet_name, df in loaded.dataframes.items():
        if df.empty:
            continue

        # Convert to object so we treat everything uniformly
        for col in df.columns:
            series = df[col]
            col_key = f"{sheet_name}::{col}"

            for row_idx, value in enumerate(series):
                if value is None or (isinstance(value, float) and pd.isna(value)):
                    # Record empty string once so missing counts still show
                    # up in scan stats
                    _record(occurrences, "", sheet_name, col, row_idx + 2)
                    continue

                raw = to_text(value)
                _record(occurrences, raw, sheet_name, col, row_idx + 2)

    # Classify each occurrence
    for occ in occurrences.values():
        occ.value_class = _classify(occ, low_freq_threshold)
        if occ.value_class is ValueClass.MISSING:
            missing_token_count += occ.total_count

    # Compile workbook meta (copy and enrich from loader's meta)
    unique_strings = sum(1 for o in occurrences.values() if o.raw_value != "")
    wb_meta = WorkbookMeta(
        filename=loaded.meta.filename,
        sheet_count=loaded.meta.sheet_count,
        total_rows=loaded.meta.total_rows,
        total_cols=loaded.meta.total_cols,
        sheets=loaded.meta.sheets,
        total_unique_strings=unique_strings,
        total_missing_tokens=missing_token_count,
    )

    # Sorted by count desc — the UI wants the big hitters first
    values_sorted = sorted(occurrences.values(), key=lambda v: -v.total_count)
    return ScanResult(workbook=wb_meta, values=values_sorted)


# --------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------- #
def _record(
    occurrences: dict[str, ValueOccurrence],
    raw: str,
    sheet: str,
    column: str,
    row_number: int,
) -> None:
    occ = occurrences.get(raw)
    if occ is None:
        occ = ValueOccurrence(
            raw_value=raw,
            normalized_value=normalize(raw),
            total_count=0,
        )
        occurrences[raw] = occ

    occ.total_count += 1
    occ.per_sheet[sheet]  = occ.per_sheet.get(sheet, 0) + 1
    key = f"{sheet}::{column}"
    occ.per_column[key]   = occ.per_column.get(key, 0) + 1
    if len(occ.examples) < _MAX_EXAMPLES:
        occ.examples.append(CellCoord(sheet=sheet, row=row_number, column=column))


def _classify(occ: ValueOccurrence, low_freq_threshold: int) -> ValueClass:
    """Assign a ValueClass to a ValueOccurrence."""
    if occ.normalized_value in MISSING_TOKENS:
        return ValueClass.MISSING

    # Low frequency check first so a singleton free-text isn't labeled as
    # "categorical" just because it happens to be short.
    if occ.total_count <= low_freq_threshold:
        # But a low-frequency numeric-like or date-like value should
        # still get its structural class
        if _looks_numeric(occ.raw_value):
            return ValueClass.NUMERIC_LIKE
        if _looks_date(occ.raw_value):
            return ValueClass.DATE_LIKE
        return ValueClass.LOW_FREQUENCY

    if _looks_numeric(occ.raw_value):
        return ValueClass.NUMERIC_LIKE
    if _looks_date(occ.raw_value):
        return ValueClass.DATE_LIKE

    # Anything seen multiple times with reasonable length is treated as
    # categorical; very long values are free text.
    if len(occ.normalized_value) > 40:
        return ValueClass.FREE_TEXT
    return ValueClass.CATEGORICAL
