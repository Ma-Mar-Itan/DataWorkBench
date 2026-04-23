"""Tests for the rule-set JSON store."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.ruleset_store import RuleSetStore
from models.schemas import ActionType, CleaningRule, MatchMode, RuleSet, ScopeType


@pytest.fixture
def store(tmp_path: Path) -> RuleSetStore:
    return RuleSetStore(tmp_path / "rulesets")


def test_empty_store_lists_nothing(store: RuleSetStore) -> None:
    assert store.list_names() == []


def test_save_and_load_round_trip(store: RuleSetStore) -> None:
    rs = RuleSet(
        name="Gender coding",
        description="male→1, female→2",
        rules=[
            CleaningRule(
                source_value="male", target_value="1",
                action_type=ActionType.MAP_CODE,
                match_mode=MatchMode.EXACT_NORMALIZED,
                scope_type=ScopeType.GLOBAL,
            ),
            CleaningRule(
                source_value="female", target_value="2",
                action_type=ActionType.MAP_CODE,
                match_mode=MatchMode.EXACT_NORMALIZED,
                scope_type=ScopeType.GLOBAL,
            ),
        ],
    )
    path = store.save(rs)
    assert path.exists()

    names = store.list_names()
    assert names == ["Gender coding"]

    loaded = store.load("Gender coding")
    assert loaded.name == "Gender coding"
    assert loaded.description == "male→1, female→2"
    assert len(loaded.rules) == 2
    assert loaded.rules[0].source_value == "male"
    assert loaded.rules[0].target_value == "1"
    assert loaded.rules[0].action_type == ActionType.MAP_CODE


def test_saved_file_is_utf8_and_readable(store: RuleSetStore, tmp_path: Path) -> None:
    rs = RuleSet(
        name="Arabic",
        rules=[CleaningRule(
            source_value="النسبة", target_value="Ratio",
            match_mode=MatchMode.EXACT_RAW, scope_type=ScopeType.GLOBAL,
        )],
    )
    path = store.save(rs)
    text = path.read_text(encoding="utf-8")
    # Arabic must appear as literal letters, not \uXXXX escapes.
    assert "النسبة" in text


def test_save_overwrites_existing_set(store: RuleSetStore) -> None:
    rs1 = RuleSet(name="Dup", rules=[CleaningRule(source_value="a", target_value="b")])
    rs2 = RuleSet(name="Dup", rules=[CleaningRule(source_value="x", target_value="y")])
    store.save(rs1)
    store.save(rs2)
    loaded = store.load("Dup")
    assert loaded.rules[0].source_value == "x"


def test_delete_removes_file(store: RuleSetStore) -> None:
    store.save(RuleSet(name="DeleteMe"))
    assert store.delete("DeleteMe") is True
    assert store.delete("DeleteMe") is False
    assert "DeleteMe" not in store.list_names()


def test_load_missing_raises(store: RuleSetStore) -> None:
    with pytest.raises(FileNotFoundError):
        store.load("does-not-exist")


def test_malformed_file_is_skipped_when_listing(store: RuleSetStore, tmp_path: Path) -> None:
    store.directory.mkdir(parents=True, exist_ok=True)
    (store.directory / "broken.json").write_text("{ not json", encoding="utf-8")
    # Shouldn't crash — just skip the broken file.
    assert store.list_names() == []
