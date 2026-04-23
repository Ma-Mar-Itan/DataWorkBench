"""Tests for the preset templates."""

from __future__ import annotations

from core.presets import (
    PRESET_REGISTRY,
    gender_coding,
    likert_5_point,
    missing_value_cleanup,
    yes_no_coding,
)
from models.schemas import ActionType, MatchMode, ScopeType


def test_gender_coding_returns_two_global_rules() -> None:
    rules = gender_coding()
    assert len(rules) == 2
    sources = {r.source_value for r in rules}
    assert sources == {"male", "female"}
    for r in rules:
        assert r.action_type == ActionType.MAP_CODE
        assert r.match_mode == MatchMode.EXACT_NORMALIZED
        assert r.scope_type == ScopeType.GLOBAL


def test_gender_coding_accepts_column_scope() -> None:
    rules = gender_coding(scope_sheet="Survey", scope_column="Gender")
    for r in rules:
        assert r.scope_type == ScopeType.COLUMN
        assert r.scope_sheet == "Survey"
        assert r.scope_column == "Gender"


def test_yes_no_coding_maps_to_one_and_zero() -> None:
    rules = yes_no_coding()
    targets = {r.source_value: r.target_value for r in rules}
    assert targets == {"yes": "1", "no": "0"}


def test_likert_5_point_has_five_rules() -> None:
    rules = likert_5_point()
    assert len(rules) == 5
    codes = sorted(r.target_value for r in rules)
    assert codes == ["1", "2", "3", "4", "5"]


def test_missing_value_cleanup_blanks_by_default() -> None:
    rules = missing_value_cleanup()
    for r in rules:
        assert r.action_type == ActionType.SET_BLANK
    # A sampling of the tokens we expect to cover.
    sources = {r.source_value for r in rules}
    assert "N/A" in sources
    assert "-" in sources
    assert "." in sources


def test_missing_value_cleanup_with_target_uses_replace() -> None:
    rules = missing_value_cleanup(target="99")
    for r in rules:
        assert r.action_type == ActionType.REPLACE
        assert r.target_value == "99"


def test_preset_registry_covers_scoped_and_plain() -> None:
    scoped_count = sum(1 for v in PRESET_REGISTRY.values() if v["scoped"])
    plain_count = sum(1 for v in PRESET_REGISTRY.values() if not v["scoped"])
    # We should have at least one of each kind so the UI exercises both paths.
    assert scoped_count >= 1
    assert plain_count >= 1
