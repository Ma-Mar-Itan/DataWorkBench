"""
Rule evaluation engine.

Given a list of ``CleaningRule`` objects and a cell's context
(sheet name, column label, raw value), return the rule — if any — that
applies to that cell. The engine is used by both the exporter and the
preview builder, guaranteeing the user sees the same result in both.

Rule priority
-------------
When multiple rules could match one cell, we apply the **most specific**:

  1. COLUMN-scoped rule (matches this sheet and this column)
  2. SHEET-scoped rule  (matches this sheet)
  3. GLOBAL-scoped rule (matches any sheet/column)

Within the same specificity tier, ``EXACT_RAW`` wins over
``EXACT_NORMALIZED``. Within the same scope *and* mode, the first rule in
the input order wins — the UI is responsible for presenting rules in a
meaningful order (e.g. most-recently-edited first).

Never substring
---------------
The engine never performs substring matching. A rule's source value must
equal the whole cell's value (raw or normalized, depending on mode). This
preserves the safety invariant: a rule mapping "home" to "house" will not
touch a cell whose value is "homework".

Formula cells
-------------
The engine never sees formula cells; the caller (exporter / preview)
filters them out upstream. The engine doesn't know about formulas at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from core.normalizer import normalize_value
from models.schemas import ActionType, CleaningRule, MatchMode, ScopeType


# --------------------------------------------------------------------------- #
# Context & outcome
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class CellContext:
    """Where a cell lives. All fields are required — the engine doesn't guess."""

    sheet: str
    column: str
    raw_value: str          # always a string; the caller converts numerics out

    @property
    def normalized_value(self) -> str:
        return normalize_value(self.raw_value)


@dataclass(frozen=True)
class RuleApplication:
    """The outcome of applying a rule to a cell."""

    rule_id: str
    source_value: str
    target_value: str                    # the value to write (may be "")
    action_type: ActionType
    clear_cell: bool                     # True for SET_BLANK (write None)


# --------------------------------------------------------------------------- #
# Indexing
# --------------------------------------------------------------------------- #

class RuleIndex:
    """Precomputed lookup tables over a rule set.

    Indexing at construction time means the per-cell evaluation is O(1) on
    the scope tier, regardless of rule-set size. For a workbook with
    hundreds of thousands of cells, this matters.

    The indices are keyed so that the same source value can appear under
    different scopes and modes simultaneously without collision.
    """

    def __init__(self, rules: Iterable[CleaningRule]) -> None:
        # Only enabled, valid rules enter the index.
        self._rules: List[CleaningRule] = []

        # Column-scoped: {(sheet, column, mode): {key: rule}}
        self._column: Dict[Tuple[str, str, MatchMode], Dict[str, CleaningRule]] = {}
        # Sheet-scoped: {(sheet, mode): {key: rule}}
        self._sheet: Dict[Tuple[str, MatchMode], Dict[str, CleaningRule]] = {}
        # Global: {mode: {key: rule}}
        self._global: Dict[MatchMode, Dict[str, CleaningRule]] = {}

        for rule in rules:
            if not rule.enabled:
                continue
            if rule.validate():
                # Invalid rules silently ignored — the UI validates before save.
                continue
            self._rules.append(rule)

            key = self._key_for(rule)
            if rule.scope_type == ScopeType.COLUMN:
                assert rule.scope_sheet is not None and rule.scope_column is not None
                bucket = self._column.setdefault(
                    (rule.scope_sheet, rule.scope_column, rule.match_mode), {}
                )
            elif rule.scope_type == ScopeType.SHEET:
                assert rule.scope_sheet is not None
                bucket = self._sheet.setdefault(
                    (rule.scope_sheet, rule.match_mode), {}
                )
            else:
                bucket = self._global.setdefault(rule.match_mode, {})

            # First rule wins on collision (input order is stable).
            bucket.setdefault(key, rule)

    # ------------------------------------------------------------------ #

    @staticmethod
    def _key_for(rule: CleaningRule) -> str:
        """The index key is whichever form the rule matches on."""
        if rule.match_mode == MatchMode.EXACT_NORMALIZED:
            return rule.normalized_source_value
        return rule.source_value

    # ------------------------------------------------------------------ #

    def match(self, ctx: CellContext) -> Optional[CleaningRule]:
        """Return the most-specific rule that applies, or None.

        Priority order:
          1. COLUMN + EXACT_RAW
          2. COLUMN + EXACT_NORMALIZED
          3. SHEET  + EXACT_RAW
          4. SHEET  + EXACT_NORMALIZED
          5. GLOBAL + EXACT_RAW
          6. GLOBAL + EXACT_NORMALIZED

        Within raw-mode tiers the lookup key is the cell's raw value; within
        normalized-mode tiers it's the normalized form.
        """
        raw = ctx.raw_value
        norm = ctx.normalized_value

        # Column-scoped.
        r = self._column.get((ctx.sheet, ctx.column, MatchMode.EXACT_RAW), {}).get(raw)
        if r: return r
        r = self._column.get((ctx.sheet, ctx.column, MatchMode.EXACT_NORMALIZED), {}).get(norm)
        if r: return r

        # Sheet-scoped.
        r = self._sheet.get((ctx.sheet, MatchMode.EXACT_RAW), {}).get(raw)
        if r: return r
        r = self._sheet.get((ctx.sheet, MatchMode.EXACT_NORMALIZED), {}).get(norm)
        if r: return r

        # Global.
        r = self._global.get(MatchMode.EXACT_RAW, {}).get(raw)
        if r: return r
        r = self._global.get(MatchMode.EXACT_NORMALIZED, {}).get(norm)
        if r: return r

        return None

    # ------------------------------------------------------------------ #

    def apply(self, ctx: CellContext) -> Optional[RuleApplication]:
        """Match and resolve to a concrete write decision, or None."""
        rule = self.match(ctx)
        if rule is None:
            return None

        if rule.action_type == ActionType.SET_BLANK:
            return RuleApplication(
                rule_id=rule.rule_id,
                source_value=rule.source_value,
                target_value="",
                action_type=rule.action_type,
                clear_cell=True,
            )

        return RuleApplication(
            rule_id=rule.rule_id,
            source_value=rule.source_value,
            target_value=rule.target_value,
            action_type=rule.action_type,
            clear_cell=False,
        )

    # ------------------------------------------------------------------ #

    @property
    def active_rule_count(self) -> int:
        return len(self._rules)
