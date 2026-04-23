"""Tests for the statistics engine."""
from __future__ import annotations

import math

from core.stats_engine import (
    categorical_stats, missingness, numeric_stats, workbook_summary,
)
from core.workbook_reader import load_workbook_from_bytes

from ._helpers import make_test_workbook


def _loaded(sheets):
    return load_workbook_from_bytes(make_test_workbook(sheets), filename="t.xlsx")


class TestWorkbookSummary:
    def test_counts(self):
        wb = _loaded({
            "S1": [["c"], ["a"], ["b"], ["N/A"]],
            "S2": [["c"], ["a"]],
        })
        s = workbook_summary(wb)
        assert s["sheet_count"] == 2
        assert s["total_rows"] == 4
        # "N/A" counts as missing
        assert s["total_missing"] >= 1


class TestNumeric:
    def test_basic_stats(self):
        # Column of 1..5
        wb = _loaded({"S": [["n"], [1], [2], [3], [4], [5]]})
        stats = numeric_stats(wb)
        assert len(stats) == 1
        n = stats[0]
        assert n.count == 5
        assert n.missing == 0
        assert n.mean == 3.0
        assert n.median == 3.0
        assert n.min_ == 1.0
        assert n.max_ == 5.0

    def test_handles_missing(self):
        wb = _loaded({"S": [["n"], [1], [None], [3], ["N/A"]]})
        stats = numeric_stats(wb)
        assert len(stats) == 1
        n = stats[0]
        assert n.count == 2     # 1 and 3
        assert n.missing == 2   # None and "N/A"
        assert n.mean == 2.0


class TestCategorical:
    def test_mode_and_counts(self):
        wb = _loaded({
            "S": [["g"], ["Male"], ["Female"], ["Male"], ["Male"], ["Female"]]
        })
        stats = categorical_stats(wb)
        assert len(stats) == 1
        c = stats[0]
        assert c.non_missing == 5
        assert c.missing == 0
        assert c.unique == 2
        assert c.mode == "Male"
        # top values percentages sum to 100
        assert math.isclose(sum(p for _, _, p in c.top_values), 100.0, abs_tol=0.1)

    def test_normalizes_before_counting(self):
        wb = _loaded({
            "S": [["g"], ["Male"], ["male"], ["MALE"], ["Female"]]
        })
        stats = categorical_stats(wb)
        c = stats[0]
        # All 3 male variants should collapse into one bucket
        assert c.unique == 2


class TestMissingness:
    def test_pct_calculated(self):
        wb = _loaded({"S": [["c"], ["x"], ["N/A"], ["-"], ["x"]]})
        rows = missingness(wb)
        assert len(rows) == 1
        m = rows[0]
        assert m["missing"] == 2
        assert m["total"] == 4
        assert math.isclose(m["pct"], 50.0, abs_tol=0.01)

    def test_sorted_by_worst_first(self):
        wb = _loaded({
            "S": [
                ["good", "bad"],
                ["x", "N/A"],
                ["x", "N/A"],
                ["x", "N/A"],
            ]
        })
        rows = missingness(wb)
        # "bad" should come first (100% missing) before "good" (0%)
        assert rows[0]["column"] == "bad"
        assert rows[0]["pct"] > rows[-1]["pct"]
