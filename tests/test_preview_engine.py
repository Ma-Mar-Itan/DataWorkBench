"""Tests for the preview engine."""
from __future__ import annotations

from core.preview_engine import preview
from core.workbook_reader import load_workbook_from_bytes
from models.enums import ActionType, MatchMode, ScopeType
from models.schemas import Rule

from ._helpers import make_test_workbook


def _loaded(sheets):
    return load_workbook_from_bytes(make_test_workbook(sheets), filename="t.xlsx")


def _rule(**kw) -> Rule:
    defaults = dict(
        rule_id="r1", source_value="x", target_value="Y",
        action_type=ActionType.REPLACE,
        match_mode=MatchMode.EXACT_RAW,
        scope_type=ScopeType.WORKBOOK,
        scope_sheet="", scope_column="",
        enabled=True, created_at=0,
    )
    defaults.update(kw)
    return Rule(**defaults)


class TestPreview:
    def test_preview_does_not_mutate_original(self):
        wb = _loaded({"S": [["c"], ["x"], ["x"]]})
        rules = [_rule()]
        before = wb.dataframes["S"]["c"].tolist()

        result = preview(wb, rules)

        # Changes reported
        assert result.changed_cells == 2
        # But original untouched
        assert wb.dataframes["S"]["c"].tolist() == before

    def test_preview_for_single_sheet_ignores_others(self):
        wb = _loaded({
            "A": [["c"], ["x"]],
            "B": [["c"], ["x"]],
        })
        result = preview(wb, [_rule()], sheet="A")
        assert result.affected_sheets == {"A"}
        assert result.changed_cells == 1

    def test_preview_matches_apply_behavior(self):
        """What preview predicts should match what apply does."""
        from core.rules_engine import apply_rules
        wb1 = _loaded({"S": [["c"], ["x"], ["y"], ["x"]]})
        wb2 = _loaded({"S": [["c"], ["x"], ["y"], ["x"]]})

        rules = [_rule()]
        p = preview(wb1, rules)
        r = apply_rules(wb2, rules)

        assert p.changed_cells == r.changed_cells
        assert len(p.changes) == len(r.changes)
