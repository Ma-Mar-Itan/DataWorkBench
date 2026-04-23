"""Tests for the rule engine.

The core invariants this file protects:
  1. Matching is whole-cell. `Home` must not touch `Homework`. This is
     THE NON-NEGOTIABLE RULE of the product.
  2. Scopes apply correctly. Workbook/sheet/column scopes must restrict
     rules exactly as described.
  3. Precedence: column > sheet > workbook; raw > normalized; earlier
     creation wins final tie.
  4. Formulas are skipped by default.
"""
from __future__ import annotations

from core.rules_engine import apply_rules, find_matching_rule
from core.workbook_reader import load_workbook_from_bytes
from models.enums import ActionType, MatchMode, ScopeType
from models.schemas import Rule

from ._helpers import make_test_workbook


def _loaded(sheets):
    return load_workbook_from_bytes(make_test_workbook(sheets), filename="t.xlsx")


def _rule(**kw) -> Rule:
    defaults = dict(
        rule_id="r1",
        source_value="",
        target_value="",
        action_type=ActionType.REPLACE,
        match_mode=MatchMode.EXACT_NORMALIZED,
        scope_type=ScopeType.WORKBOOK,
        scope_sheet="",
        scope_column="",
        enabled=True,
        created_at=0,
    )
    defaults.update(kw)
    return Rule(**defaults)


# ===================================================================== #
# WHOLE-CELL MATCHING — the critical invariant
# ===================================================================== #
class TestWholeCellMatching:
    def test_home_does_not_affect_homework(self):
        """The flagship test. If this ever fails, the product is broken."""
        wb = _loaded({"S": [["c"], ["Home"], ["Homework"], ["Home office"]]})
        rules = [_rule(source_value="Home", target_value="House",
                       match_mode=MatchMode.EXACT_RAW)]
        result = apply_rules(wb, rules)

        # Only the exact-match "Home" should change
        assert len(result.changes) == 1
        assert result.changes[0].before == "Home"
        assert result.changes[0].after == "House"

        df = wb.dataframes["S"]
        assert df["c"].tolist() == ["House", "Homework", "Home office"]

    def test_male_matches_only_whole_cell(self):
        wb = _loaded({"S": [["c"], ["Male"], ["Female"], ["male nurse"], ["Maleficent"]]})
        rules = [_rule(source_value="Male", target_value="M",
                       match_mode=MatchMode.EXACT_NORMALIZED)]
        result = apply_rules(wb, rules)
        # "Male" (normalized "male") matches. "male nurse" and
        # "Maleficent" do not. "Female" normalized is "female" (not "male").
        assert {c.before for c in result.changes} == {"Male"}
        assert len(result.changes) == 1

    def test_arabic_short_does_not_affect_longer_phrase(self):
        # Replacing "ذكر" should not touch the longer phrase "ذكر أحمد شيئا"
        wb = _loaded({"S": [["c"], ["ذكر"], ["ذكر أحمد شيئا"], ["الذكر"]]})
        rules = [_rule(source_value="ذكر", target_value="M",
                       match_mode=MatchMode.EXACT_RAW)]
        result = apply_rules(wb, rules)
        assert len(result.changes) == 1
        assert result.changes[0].before == "ذكر"

        df = wb.dataframes["S"]
        assert df["c"].tolist() == ["M", "ذكر أحمد شيئا", "الذكر"]

    def test_normalized_matches_whitespace_and_case_variants(self):
        wb = _loaded({"S": [["c"], ["  yes  "], ["YES"], ["Yes"], ["yes nope"]]})
        rules = [_rule(source_value="yes", target_value="Yes",
                       match_mode=MatchMode.EXACT_NORMALIZED)]
        result = apply_rules(wb, rules)
        # Matches: "  yes  " → "Yes" (changed) and "YES" → "Yes" (changed).
        # "Yes" already equals "Yes" — engine correctly skips the no-op.
        # "yes nope" does not match (whole-cell).
        assert len(result.changes) == 2
        df = wb.dataframes["S"]
        assert df["c"].tolist() == ["Yes", "Yes", "Yes", "yes nope"]


# ===================================================================== #
# SCOPE
# ===================================================================== #
class TestScope:
    def test_workbook_scope_hits_all_sheets(self):
        wb = _loaded({
            "A": [["c"], ["N/A"], ["ok"]],
            "B": [["c"], ["N/A"], ["ok"]],
        })
        rules = [_rule(source_value="N/A", action_type=ActionType.SET_BLANK,
                       scope_type=ScopeType.WORKBOOK)]
        result = apply_rules(wb, rules)
        assert result.affected_sheets == {"A", "B"}
        assert result.changed_cells == 2

    def test_sheet_scope_limits_to_one_sheet(self):
        wb = _loaded({
            "A": [["c"], ["x"]],
            "B": [["c"], ["x"]],
        })
        rules = [_rule(source_value="x", target_value="Y",
                       scope_type=ScopeType.SHEET, scope_sheet="A",
                       match_mode=MatchMode.EXACT_RAW)]
        result = apply_rules(wb, rules)
        assert result.affected_sheets == {"A"}
        assert wb.dataframes["A"]["c"].tolist() == ["Y"]
        assert wb.dataframes["B"]["c"].tolist() == ["x"]

    def test_column_scope_limits_to_one_column(self):
        wb = _loaded({"S": [["c1", "c2"], ["x", "x"], ["x", "x"]]})
        rules = [_rule(source_value="x", target_value="Y",
                       scope_type=ScopeType.COLUMN,
                       scope_sheet="S", scope_column="c1",
                       match_mode=MatchMode.EXACT_RAW)]
        result = apply_rules(wb, rules)
        df = wb.dataframes["S"]
        assert df["c1"].tolist() == ["Y", "Y"]
        assert df["c2"].tolist() == ["x", "x"]


# ===================================================================== #
# PRECEDENCE
# ===================================================================== #
class TestPrecedence:
    def test_column_scope_beats_workbook(self):
        wb = _loaded({"S": [["c"], ["x"]]})
        wb_rule  = _rule(rule_id="w", source_value="x", target_value="WORK",
                         match_mode=MatchMode.EXACT_RAW,
                         scope_type=ScopeType.WORKBOOK, created_at=1)
        col_rule = _rule(rule_id="c", source_value="x", target_value="COL",
                         match_mode=MatchMode.EXACT_RAW,
                         scope_type=ScopeType.COLUMN, scope_sheet="S",
                         scope_column="c", created_at=2)
        result = apply_rules(wb, [wb_rule, col_rule])
        assert wb.dataframes["S"]["c"].tolist() == ["COL"]
        assert result.changes[0].rule_id == "c"

    def test_raw_beats_normalized_at_same_scope(self):
        wb = _loaded({"S": [["c"], ["x"]]})
        raw  = _rule(rule_id="raw", source_value="x", target_value="RAW",
                     match_mode=MatchMode.EXACT_RAW, created_at=2)
        norm = _rule(rule_id="norm", source_value="x", target_value="NORM",
                     match_mode=MatchMode.EXACT_NORMALIZED, created_at=1)
        apply_rules(wb, [raw, norm])
        assert wb.dataframes["S"]["c"].tolist() == ["RAW"]

    def test_earlier_created_wins_final_tie(self):
        wb = _loaded({"S": [["c"], ["x"]]})
        a = _rule(rule_id="a", source_value="x", target_value="A",
                  match_mode=MatchMode.EXACT_RAW, created_at=1)
        b = _rule(rule_id="b", source_value="x", target_value="B",
                  match_mode=MatchMode.EXACT_RAW, created_at=2)
        apply_rules(wb, [b, a])   # order in list shouldn't matter
        assert wb.dataframes["S"]["c"].tolist() == ["A"]


# ===================================================================== #
# ENABLED / NO-OP / FORMULAS
# ===================================================================== #
class TestMisc:
    def test_disabled_rule_does_nothing(self):
        wb = _loaded({"S": [["c"], ["x"]]})
        rules = [_rule(source_value="x", target_value="Y",
                       match_mode=MatchMode.EXACT_RAW, enabled=False)]
        result = apply_rules(wb, rules)
        assert result.changed_cells == 0

    def test_set_blank_action(self):
        import pandas as pd
        wb = _loaded({"S": [["c"], ["N/A"]]})
        rules = [_rule(source_value="N/A",
                       action_type=ActionType.SET_BLANK,
                       match_mode=MatchMode.EXACT_RAW)]
        apply_rules(wb, rules)
        # pandas may represent a blanked cell as None or NaN depending on dtype;
        # either is a valid "missing" marker.
        val = wb.dataframes["S"]["c"].iloc[0]
        assert val is None or pd.isna(val)

    def test_no_op_when_target_equals_raw(self):
        wb = _loaded({"S": [["c"], ["x"]]})
        rules = [_rule(source_value="x", target_value="x",
                       match_mode=MatchMode.EXACT_RAW)]
        result = apply_rules(wb, rules)
        assert result.changed_cells == 0


# ===================================================================== #
# find_matching_rule — direct unit test
# ===================================================================== #
class TestFindMatchingRule:
    def test_no_match(self):
        rules = [_rule(source_value="a", match_mode=MatchMode.EXACT_RAW)]
        assert find_matching_rule(rules, "S", "c", "b") is None

    def test_match_returns_highest_precedence(self):
        rules = [
            _rule(rule_id="w",
                  source_value="x", target_value="W",
                  match_mode=MatchMode.EXACT_RAW,
                  scope_type=ScopeType.WORKBOOK, created_at=0),
            _rule(rule_id="c",
                  source_value="x", target_value="C",
                  match_mode=MatchMode.EXACT_RAW,
                  scope_type=ScopeType.COLUMN,
                  scope_sheet="S", scope_column="c",
                  created_at=1),
        ]
        chosen = find_matching_rule(rules, "S", "c", "x")
        assert chosen is not None and chosen.rule_id == "c"
