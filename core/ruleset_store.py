"""
Ruleset persistence.

Rulesets are stored as JSON. The schema is versioned (schema_version: 1)
so the loader can migrate older formats if needed.

A loaded ruleset is always validated — any malformed rule is rejected
with a clear error rather than silently dropped, because silently
dropping a rule can change cleaning output in ways the user won't
notice.
"""
from __future__ import annotations

import json
from typing import Any, Iterable

from models.enums import ActionType, MatchMode, ScopeType
from models.schemas import Rule


SCHEMA_VERSION = 1


class RulesetValidationError(ValueError):
    """Raised when a ruleset JSON blob fails schema validation."""


# --------------------------------------------------------------------- #
# Save
# --------------------------------------------------------------------- #
def save_ruleset(rules: Iterable[Rule], metadata: dict | None = None) -> str:
    """Serialize a ruleset to a JSON string."""
    payload = {
        "schema_version": SCHEMA_VERSION,
        "metadata":       metadata or {},
        "rules":          [r.to_dict() for r in rules],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def save_ruleset_to_file(path: str, rules: Iterable[Rule], metadata: dict | None = None) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(save_ruleset(rules, metadata))


# --------------------------------------------------------------------- #
# Load
# --------------------------------------------------------------------- #
def load_ruleset(blob: str | bytes) -> tuple[list[Rule], dict]:
    """
    Parse and validate a JSON ruleset.

    Returns (rules, metadata). Raises RulesetValidationError on any
    schema problem.
    """
    if isinstance(blob, bytes):
        blob = blob.decode("utf-8")
    try:
        data = json.loads(blob)
    except json.JSONDecodeError as e:
        raise RulesetValidationError(f"Invalid JSON: {e}") from e

    _validate_payload(data)
    rules = [_validate_rule(r, i) for i, r in enumerate(data["rules"])]
    metadata = data.get("metadata", {})
    return rules, metadata


def load_ruleset_from_file(path: str) -> tuple[list[Rule], dict]:
    with open(path, "r", encoding="utf-8") as f:
        return load_ruleset(f.read())


# --------------------------------------------------------------------- #
# Validation internals
# --------------------------------------------------------------------- #
def _validate_payload(data: Any) -> None:
    if not isinstance(data, dict):
        raise RulesetValidationError("Top-level JSON must be an object.")
    if "rules" not in data or not isinstance(data["rules"], list):
        raise RulesetValidationError("Missing or malformed 'rules' array.")
    version = data.get("schema_version", 1)
    if version != SCHEMA_VERSION:
        raise RulesetValidationError(
            f"Unsupported schema_version {version}. Expected {SCHEMA_VERSION}."
        )


_VALID_SCOPES  = {s.value for s in ScopeType}
_VALID_MATCH   = {m.value for m in MatchMode}
_VALID_ACTIONS = {a.value for a in ActionType}


def _validate_rule(r: Any, idx: int) -> Rule:
    if not isinstance(r, dict):
        raise RulesetValidationError(f"Rule at index {idx} is not an object.")
    required = ("rule_id", "source_value")
    for k in required:
        if k not in r:
            raise RulesetValidationError(f"Rule at index {idx} missing '{k}'.")

    scope  = r.get("scope_type",  ScopeType.WORKBOOK.value)
    match  = r.get("match_mode",  MatchMode.EXACT_NORMALIZED.value)
    action = r.get("action_type", ActionType.REPLACE.value)
    if scope  not in _VALID_SCOPES:  raise RulesetValidationError(f"Rule '{r['rule_id']}': bad scope_type '{scope}'.")
    if match  not in _VALID_MATCH:   raise RulesetValidationError(f"Rule '{r['rule_id']}': bad match_mode '{match}'.")
    if action not in _VALID_ACTIONS: raise RulesetValidationError(f"Rule '{r['rule_id']}': bad action_type '{action}'.")

    if scope == ScopeType.SHEET.value and not r.get("scope_sheet"):
        raise RulesetValidationError(f"Rule '{r['rule_id']}': sheet scope requires scope_sheet.")
    if scope == ScopeType.COLUMN.value and (not r.get("scope_sheet") or not r.get("scope_column")):
        raise RulesetValidationError(f"Rule '{r['rule_id']}': column scope requires scope_sheet and scope_column.")

    try:
        return Rule.from_dict(r)
    except Exception as e:
        raise RulesetValidationError(f"Rule '{r.get('rule_id', idx)}': {e}") from e
