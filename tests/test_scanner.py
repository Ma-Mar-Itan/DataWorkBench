"""Tests for the scan engine."""
from __future__ import annotations

from core.scanner import scan_workbook
from core.workbook_reader import load_workbook_from_bytes
from models.enums import ValueClass

from ._helpers import make_test_workbook


def _loaded(sheets):
    return load_workbook_from_bytes(make_test_workbook(sheets), filename="test.xlsx")


class TestScanAggregation:
    def test_counts_unique_values(self):
        wb = _loaded({"S1": [["col"], ["A"], ["A"], ["B"]]})
        result = scan_workbook(wb)
        values = {v.raw_value: v for v in result.values}
        assert values["A"].total_count == 2
        assert values["B"].total_count == 1

    def test_per_sheet_breakdown(self):
        wb = _loaded({
            "A": [["x"], ["val"], ["val"]],
            "B": [["y"], ["val"]],
        })
        result = scan_workbook(wb)
        val = next(v for v in result.values if v.raw_value == "val")
        assert val.per_sheet == {"A": 2, "B": 1}

    def test_per_column_breakdown(self):
        wb = _loaded({"S": [["c1", "c2"], ["hit", "miss"], ["hit", "hit"]]})
        result = scan_workbook(wb)
        hit = next(v for v in result.values if v.raw_value == "hit")
        assert hit.per_column == {"S::c1": 2, "S::c2": 1}

    def test_examples_captured(self):
        wb = _loaded({"S": [["c"], ["same"], ["same"], ["same"]]})
        result = scan_workbook(wb)
        same = next(v for v in result.values if v.raw_value == "same")
        assert len(same.examples) >= 1
        # row numbers are 1-based Excel rows; header is 1, data starts 2
        assert same.examples[0].row == 2


class TestValueClasses:
    def test_missing_tokens_classified(self):
        wb = _loaded({"S": [["c"], ["N/A"], ["N/A"], ["N/A"]]})
        result = scan_workbook(wb)
        na = next(v for v in result.values if v.raw_value == "N/A")
        assert na.value_class is ValueClass.MISSING

    def test_numeric_like_strings_classified(self):
        wb = _loaded({"S": [["c"], ["42"], ["42"], ["42"]]})
        result = scan_workbook(wb)
        v = next(v for v in result.values if v.raw_value == "42")
        assert v.value_class is ValueClass.NUMERIC_LIKE

    def test_categorical_for_repeated_short_text(self):
        wb = _loaded({"S": [["c"], ["Yes"], ["Yes"], ["Yes"]]})
        result = scan_workbook(wb)
        v = next(v for v in result.values if v.raw_value == "Yes")
        assert v.value_class is ValueClass.CATEGORICAL


class TestWorkbookSummary:
    def test_sheet_count_preserved(self):
        wb = _loaded({
            "S1": [["c"], ["a"]],
            "S2": [["c"], ["b"]],
            "S3": [["c"], ["c"]],
        })
        result = scan_workbook(wb)
        assert result.workbook.sheet_count == 3

    def test_missing_token_total(self):
        wb = _loaded({"S": [["c"], ["N/A"], ["N/A"], ["ok"]]})
        result = scan_workbook(wb)
        # 2 N/A cells flagged as missing
        assert result.workbook.total_missing_tokens >= 2
