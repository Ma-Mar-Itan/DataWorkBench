"""
Terminology workbench — inline value editor + rules list in one card.

Design
------
The common case is "I see a cell that says 'yes', I want it to become 1."
That is one row of thought for the user. Any UI that makes them type a
source value into a separate form when it was visible on screen a moment
ago is wasting their attention.

So: the main surface is a single grid where every row is a unique value
extracted from the workbook. A **Replace with** column lets the user type
the target inline. A **Scope** dropdown lets them pick where the rule
applies (Global / This sheet / This column). That's it. A rule is
created, updated, or deleted based on whether the cell has text in it.

Power features (``SET_BLANK`` action, ``EXACT_RAW`` match mode, mass
enable/disable) remain available behind an "Advanced rule editor"
expander below the grid. That keeps the common case one row, while
surveys-cleaners who need precision still have the tools they want.

Rule identity
-------------
Inline-edited rules are keyed by ``(normalized_source, scope_signature)``.
The scope_signature distinguishes "map 'yes' globally" from "map 'yes'
in the Approval column". When the user clears a cell's Replace-with
field, we delete the rule that has that identity. When they edit it,
we update the existing rule in place rather than creating a duplicate.
"""

from __future__ import annotations

from html import escape as _esc
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

from core.presets import PRESET_REGISTRY
from models.schemas import (
    ActionType,
    CleaningRule,
    ExtractedValue,
    MatchMode,
    ScopeType,
    ValueClass,
)
from ui.layout import caption, card, chip, html_block, rule as divider


# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

_CLASS_FILTER_OPTIONS = [
    ("All classes",   None),
    ("Category",      ValueClass.TEXT_CATEGORY),
    ("Numeric-like",  ValueClass.NUMERIC_LIKE),
    ("Mixed alnum",   ValueClass.MIXED_ALNUM),
    ("Missing token", ValueClass.MISSING_TOKEN),
    ("Header label",  ValueClass.HEADER_LABEL),
    ("Date-like",     ValueClass.DATE_LIKE),
    ("Free text",     ValueClass.FREE_TEXT),
    ("Low frequency", ValueClass.LOW_FREQUENCY),
]

# Scope options shown in the inline grid. We intentionally keep them
# coarse — fine-grained (sheet/column) scope goes through Advanced.
_INLINE_SCOPE_GLOBAL = "Global"
_INLINE_SCOPE_SHEET  = "This sheet"
_INLINE_SCOPE_COLUMN = "This column"


# --------------------------------------------------------------------------- #
# Step state
# --------------------------------------------------------------------------- #

def _step_state() -> str:
    result = st.session_state.get("scan_result")
    if result is None:
        return "idle"
    if st.session_state.get("rules"):
        return "active"
    return "active"


# --------------------------------------------------------------------------- #
# Inline-rule identity
# --------------------------------------------------------------------------- #

def _inline_rule_signature(
    normalized_source: str,
    inline_scope: str,
    representative_sheet: Optional[str],
    representative_column: Optional[str],
) -> Tuple[str, str, Optional[str], Optional[str]]:
    """Stable identity for a rule created via the inline grid.

    Two inline rules are the same iff they share this signature. The
    signature deliberately does NOT include action_type or match_mode,
    because inline rules always use ``REPLACE`` + ``EXACT_NORMALIZED``.
    """
    if inline_scope == _INLINE_SCOPE_COLUMN:
        return (normalized_source, "column", representative_sheet, representative_column)
    if inline_scope == _INLINE_SCOPE_SHEET:
        return (normalized_source, "sheet", representative_sheet, None)
    return (normalized_source, "global", None, None)


def _is_inline_rule(rule: CleaningRule) -> bool:
    """Heuristic: was this rule created from the inline grid?

    Inline rules always use REPLACE + EXACT_NORMALIZED. Rules touched by
    the Advanced editor may change those; once a rule's action is
    SET_BLANK or mode is EXACT_RAW, it's treated as "advanced" and the
    inline grid ignores it.
    """
    return (
        rule.action_type == ActionType.REPLACE
        and rule.match_mode == MatchMode.EXACT_NORMALIZED
    )


def _signature_of_existing(rule: CleaningRule) -> Tuple[str, str, Optional[str], Optional[str]]:
    """Build a signature from an existing rule for index matching."""
    if rule.scope_type == ScopeType.COLUMN:
        return (rule.normalized_source_value, "column", rule.scope_sheet, rule.scope_column)
    if rule.scope_type == ScopeType.SHEET:
        return (rule.normalized_source_value, "sheet", rule.scope_sheet, None)
    return (rule.normalized_source_value, "global", None, None)


# --------------------------------------------------------------------------- #
# Filtering
# --------------------------------------------------------------------------- #

def _filter_values(
    values: List[ExtractedValue],
    *,
    search: str,
    sheet: str,
    column: str,
    klass: Optional[ValueClass],
    missing_only: bool,
    min_frequency: int,
    mapped_filter: str,
) -> List[ExtractedValue]:
    """Apply all active filters and return a new list."""
    out = values

    if search:
        needle = search.strip().casefold()
        if needle:
            out = [
                v for v in out
                if needle in v.raw_value.casefold() or needle in v.normalized_value
            ]
    if sheet != "All sheets":
        out = [v for v in out if sheet in v.sheets]
    if column != "All columns":
        out = [v for v in out if column in v.columns]
    if klass is not None:
        out = [v for v in out if v.value_class == klass]
    if missing_only:
        out = [v for v in out if v.likely_missing]
    if min_frequency > 1:
        out = [v for v in out if v.frequency >= min_frequency]
    if mapped_filter != "All":
        # We need to check against the current rules list for which
        # normalized sources have inline rules.
        inline_sources = {
            r.normalized_source_value
            for r in st.session_state.get("rules", [])
            if _is_inline_rule(r)
        }
        if mapped_filter == "Mapped":
            out = [v for v in out if v.normalized_value in inline_sources]
        elif mapped_filter == "Unmapped":
            out = [v for v in out if v.normalized_value not in inline_sources]
    return out


# --------------------------------------------------------------------------- #
# Preset chooser
# --------------------------------------------------------------------------- #

def _render_preset_chooser(sheet_names: List[str], columns_by_sheet: dict) -> None:
    """Preset dropdown + optional scope + add button."""
    html_block(
        '<div style="font-size:11px; letter-spacing:0.12em; text-transform:uppercase; '
        'color:var(--tw-ink-4); font-weight:800; margin-bottom:8px;">Preset templates</div>'
    )
    preset_names = list(PRESET_REGISTRY.keys())
    c1, c2, c3 = st.columns([3, 2, 1])
    with c1:
        selected = st.selectbox(
            "Preset", ["— Choose a starter preset —"] + preset_names,
            label_visibility="collapsed",
        )
    with c2:
        scope_sheet = None
        scope_column = None
        if selected in PRESET_REGISTRY and PRESET_REGISTRY[selected]["scoped"] and sheet_names:
            picked = st.selectbox(
                "Scope to sheet (optional)",
                ["— Global —"] + sheet_names,
                label_visibility="collapsed",
            )
            if picked != "— Global —":
                scope_sheet = picked
                cols = columns_by_sheet.get(picked, [])
                if cols:
                    col_pick = st.selectbox(
                        "Column (optional)",
                        ["— Whole sheet —"] + cols,
                        label_visibility="collapsed",
                        key=f"preset_col_{picked}",
                    )
                    if col_pick != "— Whole sheet —":
                        scope_column = col_pick
    with c3:
        add = st.button(
            "Add preset", use_container_width=True,
            disabled=(selected not in PRESET_REGISTRY),
        )

    if selected in PRESET_REGISTRY:
        caption(PRESET_REGISTRY[selected]["description"])

    if add and selected in PRESET_REGISTRY:
        factory = PRESET_REGISTRY[selected]["factory"]
        if PRESET_REGISTRY[selected]["scoped"]:
            new_rules = factory(scope_sheet=scope_sheet, scope_column=scope_column)
        else:
            new_rules = factory()
        rules = st.session_state.setdefault("rules", [])
        existing = {
            (r.source_value, r.scope_type, r.scope_sheet, r.scope_column) for r in rules
        }
        added = 0
        for r in new_rules:
            key = (r.source_value, r.scope_type, r.scope_sheet, r.scope_column)
            if key not in existing:
                rules.append(r)
                added += 1
        st.success(f"Added {added} rule{'s' if added != 1 else ''} from preset.")


# --------------------------------------------------------------------------- #
# Advanced rule editor
# --------------------------------------------------------------------------- #

def _render_advanced_editor() -> None:
    """Power editor — full grid with every field exposed."""
    rules = st.session_state.setdefault("rules", [])

    with st.expander(
        f"Advanced rule editor  ·  {len(rules):,} rule{'s' if len(rules) != 1 else ''} total",
        expanded=False,
    ):
        caption(
            "Use this for rules that blank cells (missing-token cleanup), "
            "rules that must match raw bytes exactly, or to mass-enable or "
            "mass-disable rules. Changes here override inline edits above."
        )

        if not rules:
            html_block(
                '<div style="padding:18px; text-align:center; color:var(--tw-ink-3); '
                'font-size:13px; background:var(--tw-surface-2); border:1px dashed '
                'var(--tw-border-strong); border-radius:var(--tw-radius);">'
                'No rules yet.</div>'
            )
            return

        rows = []
        for r in rules:
            rows.append({
                "On":     r.enabled,
                "Source": r.source_value,
                "Target": r.target_value,
                "Action": r.action_type.value,
                "Mode":   r.match_mode.value,
                "Scope":  r.scope_type.value,
                "Sheet":  r.scope_sheet or "",
                "Column": r.scope_column or "",
                "Delete": False,
                "_id":    r.rule_id,
            })
        df = pd.DataFrame(rows)

        edited = st.data_editor(
            df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "On":     st.column_config.CheckboxColumn("On", width="small"),
                "Source": st.column_config.TextColumn("Source value", width="large"),
                "Target": st.column_config.TextColumn("Target", width="medium"),
                "Action": st.column_config.SelectboxColumn(
                    "Action", options=[a.value for a in ActionType], width="small",
                ),
                "Mode":   st.column_config.SelectboxColumn(
                    "Mode", options=[m.value for m in MatchMode], width="small",
                ),
                "Scope":  st.column_config.SelectboxColumn(
                    "Scope", options=[s.value for s in ScopeType], width="small",
                ),
                "Sheet":  st.column_config.TextColumn("Sheet", width="medium"),
                "Column": st.column_config.TextColumn("Column", width="medium"),
                "Delete": st.column_config.CheckboxColumn("🗑", width="small"),
                "_id": None,
            },
            num_rows="fixed",
            height=min(420, 56 + 35 * len(rules)),
            key="advanced_rules_editor",
        )

        # Merge changes back, honour the Delete flag.
        from core.normalizer import normalize_value
        id_to_row = {row["_id"]: row for _, row in edited.iterrows()}
        new_rules: list[CleaningRule] = []
        for r in rules:
            row = id_to_row.get(r.rule_id)
            if row is None or bool(row.get("Delete")):
                continue
            r.enabled = bool(row.get("On", True))
            r.source_value = str(row.get("Source") or "")
            r.target_value = str(row.get("Target") or "")
            try:
                r.action_type = ActionType(row.get("Action", r.action_type.value))
                r.match_mode  = MatchMode(row.get("Mode", r.match_mode.value))
                r.scope_type  = ScopeType(row.get("Scope", r.scope_type.value))
            except ValueError:
                pass
            r.scope_sheet = (row.get("Sheet") or "") or None
            r.scope_column = (row.get("Column") or "") or None
            r.normalized_source_value = normalize_value(r.source_value)
            new_rules.append(r)
        st.session_state["rules"] = new_rules


# --------------------------------------------------------------------------- #
# Column profiles — compact grid
# --------------------------------------------------------------------------- #

def _render_column_profiles(profiles, sheet_filter: str) -> None:
    """Compact responsive grid of column profile cards."""
    if sheet_filter != "All sheets":
        profiles = [p for p in profiles if p.sheet == sheet_filter]
    if not profiles:
        return

    divider()
    # Sort: actionable (has missing tokens) first, then rich.
    profiles = sorted(profiles, key=lambda p: (-p.missing_like_count, -p.unique_count))[:24]

    html_block(
        f'<div style="display:flex; align-items:baseline; justify-content:space-between; '
        f'margin-bottom:10px;">'
        f'<div style="font-size:11px; letter-spacing:0.12em; text-transform:uppercase; '
        f'color:var(--tw-ink-4); font-weight:800;">Column profiles</div>'
        f'<div style="font-size:12px; color:var(--tw-ink-4); font-weight:600;">'
        f'{len(profiles)} shown · sorted by missing tokens, then uniqueness</div>'
        f'</div>'
    )

    cards: list[str] = []
    for p in profiles:
        if p.top_values:
            top_rows = "".join(
                f'<tr><td>{_esc(raw)}</td><td>{count:,}</td></tr>'
                for raw, count in p.top_values
            )
            details_html = (
                '<details>'
                '<summary>Top values</summary>'
                f'<table class="tw-profile__top">{top_rows}</table>'
                '</details>'
            )
        else:
            details_html = ""

        missing_chip = (
            f'<span class="tw-profile__stat--warn">'
            f'<b>{p.missing_like_count:,}</b> missing</span>'
            if p.missing_like_count else ""
        )
        cards.append(
            f'<div class="tw-profile">'
            f'  <div class="tw-profile__head">'
            f'    <div class="tw-profile__col" title="{_esc(p.column)}">{_esc(p.column)}</div>'
            f'    <div class="tw-profile__sheet" title="{_esc(p.sheet)}">{_esc(p.sheet)}</div>'
            f'  </div>'
            f'  <div class="tw-profile__stats">'
            f'    <span><b>{p.unique_count:,}</b> unique</span>'
            f'    <span><b>{p.non_empty_count:,}</b> filled</span>'
            f'    {missing_chip}'
            f'  </div>'
            f'  {details_html}'
            f'</div>'
        )
    html_block('<div class="tw-profile-grid">' + "".join(cards) + '</div>')


# --------------------------------------------------------------------------- #
# Main render
# --------------------------------------------------------------------------- #

def render_workbench_section() -> None:
    result = st.session_state.get("scan_result")

    with card(
        step=3,
        step_state=_step_state(),
        eyebrow="Terminology",
        title="Terminology workbench",
        subtitle=(
            "Every unique string value in the workbook, with an inline "
            "\"Replace with\" column. Type a replacement — the rule is "
            "created. Clear it — the rule is removed. Preset templates and "
            "the advanced editor sit below for less common cases."
        ),
    ):
        if result is None:
            caption("Scan the workbook above to populate the workbench.")
            return
        if result.unique_value_count == 0:
            caption("No string values were extracted.")
            return

        sheet_names = result.sheet_names
        columns_by_sheet = result.columns_by_sheet()
        rules: list[CleaningRule] = st.session_state.setdefault("rules", [])

        # ------------------------------------------------------------------ #
        # Status bar — live rule counts so the user sees effect at a glance.
        # Without this, the only rule-count indicator is in the left panel,
        # which may be off-screen while editing the grid below.
        # ------------------------------------------------------------------ #
        inline_count = sum(1 for r in rules if _is_inline_rule(r))
        advanced_count = sum(1 for r in rules if not _is_inline_rule(r))
        active_count = sum(1 for r in rules if r.enabled and not r.validate())
        total_count = len(rules)

        if total_count == 0:
            status_html = (
                '<div style="margin: 0 0 14px; padding: 10px 14px; '
                'border-radius: var(--tw-radius); background: var(--tw-surface-2); '
                'border: 1px solid var(--tw-border); font-size: 12.5px; '
                'color: var(--tw-ink-3); font-weight: 600;">'
                'No rules yet. Type in the <b style="color:var(--tw-ink);">Replace with</b> '
                'column below to create your first one.'
                '</div>'
            )
        else:
            badges: list[str] = []
            badges.append(f'<b style="color:var(--tw-ink); font-size:13px;">{total_count:,}</b>'
                          f' rule{"s" if total_count != 1 else ""} total')
            badges.append(f'<b style="color:var(--tw-accent); font-size:13px;">{active_count:,}</b> active')
            if inline_count:
                badges.append(f'{inline_count:,} inline')
            if advanced_count:
                badges.append(f'{advanced_count:,} advanced')
            status_html = (
                '<div style="margin: 0 0 14px; padding: 10px 14px; '
                'border-radius: var(--tw-radius); background: var(--tw-accent-soft); '
                'border: 1px solid var(--tw-accent-border); font-size: 12.5px; '
                'color: var(--tw-ink-3); font-weight: 600; display:flex; '
                'gap:18px; flex-wrap:wrap; align-items:baseline;">'
                + "<span style='display:flex; gap:5px; align-items:baseline;'></span>".join(
                    f'<span>{b}</span>' for b in badges
                )
                + '</div>'
            )
        html_block(status_html)

        # ------------------------------------------------------------------ #
        # Preset chooser (one-click bulk rule creation)
        # ------------------------------------------------------------------ #
        _render_preset_chooser(sheet_names, columns_by_sheet)
        divider()

        # ------------------------------------------------------------------ #
        # Filter bar
        # ------------------------------------------------------------------ #
        f1, f2, f3, f4 = st.columns([3, 2, 2, 2])
        with f1:
            search = st.text_input(
                "Search", placeholder="Filter by value text…",
                label_visibility="collapsed",
            )
        with f2:
            sheet_filter = st.selectbox(
                "Sheet", ["All sheets"] + sheet_names, label_visibility="collapsed",
            )
        with f3:
            if sheet_filter == "All sheets":
                all_cols: list[str] = []
                seen = set()
                for s in sheet_names:
                    for c in columns_by_sheet.get(s, []):
                        if c not in seen:
                            seen.add(c); all_cols.append(c)
                column_options = ["All columns"] + all_cols
            else:
                column_options = ["All columns"] + columns_by_sheet.get(sheet_filter, [])
            column_filter = st.selectbox(
                "Column", column_options, label_visibility="collapsed",
            )
        with f4:
            class_label = st.selectbox(
                "Class", [l for l, _ in _CLASS_FILTER_OPTIONS], label_visibility="collapsed",
            )
        class_filter = dict(_CLASS_FILTER_OPTIONS)[class_label]

        g1, g2, g3, g4 = st.columns([1, 1, 1, 3])
        with g1:
            missing_only = st.checkbox("Missing only", value=False)
        with g2:
            min_freq = st.number_input("Min. freq", min_value=1, max_value=10000, value=1, step=1)
        with g3:
            mapped_filter = st.selectbox(
                "Rules", ["All", "Unmapped", "Mapped"], label_visibility="collapsed",
            )
        # g4 intentionally empty — layout spacer.

        filtered = _filter_values(
            result.values,
            search=search,
            sheet=sheet_filter,
            column=column_filter,
            klass=class_filter,
            missing_only=missing_only,
            min_frequency=int(min_freq),
            mapped_filter=mapped_filter,
        )

        # ------------------------------------------------------------------ #
        # Summary line — how many values, how many already mapped
        # ------------------------------------------------------------------ #
        inline_rules_by_norm: Dict[str, CleaningRule] = {}
        for r in rules:
            if _is_inline_rule(r):
                # If multiple inline rules share a normalized source, take
                # the first one for display purposes — the advanced editor
                # handles collisions.
                inline_rules_by_norm.setdefault(r.normalized_source_value, r)

        mapped_in_view = sum(1 for v in filtered if v.normalized_value in inline_rules_by_norm)
        html_block(
            f'<div style="margin:4px 0 10px; font-size:12.5px; color:var(--tw-ink-3); '
            f'font-weight:600;">'
            f'<b style="color:var(--tw-ink);">{len(filtered):,}</b> of '
            f'<b style="color:var(--tw-ink);">{result.unique_value_count:,}</b> unique values match filters · '
            f'<b style="color:var(--tw-accent);">{mapped_in_view:,}</b> already mapped.'
            f'</div>'
        )

        if not filtered:
            html_block(
                '<div style="padding:18px; text-align:center; color:var(--tw-ink-3); '
                'font-size:13px; background:var(--tw-surface-2); border:1px dashed '
                'var(--tw-border-strong); border-radius:var(--tw-radius);">'
                'No values match the current filters.</div>'
            )
            return

        # ------------------------------------------------------------------ #
        # Inline editor grid — the main event
        # ------------------------------------------------------------------ #
        display = filtered[:500]
        rows = []
        for v in display:
            existing_rule = inline_rules_by_norm.get(v.normalized_value)
            existing_target = existing_rule.target_value if existing_rule else ""
            # Derive the display scope from the existing rule, or pick a smart default.
            if existing_rule:
                if existing_rule.scope_type == ScopeType.COLUMN:
                    scope_label = _INLINE_SCOPE_COLUMN
                elif existing_rule.scope_type == ScopeType.SHEET:
                    scope_label = _INLINE_SCOPE_SHEET
                else:
                    scope_label = _INLINE_SCOPE_GLOBAL
            else:
                scope_label = _INLINE_SCOPE_GLOBAL

            rows.append({
                "Value":        v.raw_value,
                "Replace with": existing_target,
                "Scope":        scope_label,
                "Class":        v.value_class.value,
                "Count":        v.frequency,
                "Columns":      (", ".join(v.columns) if len(v.columns) <= 2
                                 else f"{', '.join(v.columns[:2])} +{len(v.columns)-2}"),
                "_norm":        v.normalized_value,
                "_sheet":       v.sheets[0] if v.sheets else None,
                "_column":      v.columns[0] if v.columns else None,
                "_n_columns":   len(v.columns),
                "_n_sheets":    len(v.sheets),
            })
        df = pd.DataFrame(rows)

        edited = st.data_editor(
            df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Value": st.column_config.TextColumn(
                    "Value", disabled=True, width="large",
                    help="Source value — read-only. Type a replacement on the right.",
                ),
                "Replace with": st.column_config.TextColumn(
                    "Replace with", width="medium",
                    help="Type the replacement. Empty = no rule for this value.",
                ),
                "Scope": st.column_config.SelectboxColumn(
                    "Scope",
                    options=[_INLINE_SCOPE_GLOBAL, _INLINE_SCOPE_SHEET, _INLINE_SCOPE_COLUMN],
                    width="small",
                    help="Where the rule applies. Column scope uses this value's first column.",
                ),
                "Class": st.column_config.TextColumn("Class", disabled=True, width="small"),
                "Count": st.column_config.NumberColumn("Count", disabled=True, width="small"),
                "Columns": st.column_config.TextColumn("Columns", disabled=True, width="medium"),
                "_norm": None, "_sheet": None, "_column": None,
                "_n_columns": None, "_n_sheets": None,
            },
            num_rows="fixed",
            height=min(560, 56 + 35 * len(display)),
            key="workbench_editor",
        )

        if len(filtered) > 500:
            caption(f"Showing first 500 values. Narrow filters to see more.")

        # ------------------------------------------------------------------ #
        # Diff edited grid against current inline rules
        # ------------------------------------------------------------------ #
        # Build a signature -> rule index over CURRENT inline rules so we
        # can detect additions, edits, and deletions by comparing edited
        # row state to what's in session_state.
        inline_rules_by_sig: Dict[Tuple, CleaningRule] = {
            _signature_of_existing(r): r for r in rules if _is_inline_rule(r)
        }
        seen_sigs: set = set()

        for _, row in edited.iterrows():
            normalized = row["_norm"]
            target = str(row["Replace with"] or "").strip()
            scope_label = row["Scope"]
            repr_sheet  = row["_sheet"]
            repr_column = row["_column"]

            # Can't scope to column if the value appears in multiple columns
            # without the user picking one. We degrade gracefully to sheet
            # scope in that case — a best-effort so inline edits don't throw.
            if scope_label == _INLINE_SCOPE_COLUMN and row["_n_columns"] > 1:
                # Use the first-seen column as "this column".
                pass  # repr_column already holds columns[0]
            if scope_label == _INLINE_SCOPE_SHEET and row["_n_sheets"] > 1:
                pass  # repr_sheet already holds sheets[0]

            sig = _inline_rule_signature(normalized, scope_label, repr_sheet, repr_column)
            existing = inline_rules_by_sig.get(sig)

            if target:
                # Add or update.
                if existing is None:
                    # Try to find a same-source rule under a different scope —
                    # if the user changed the scope dropdown, we want to move
                    # the rule, not duplicate it.
                    moved = None
                    for other_sig, other_rule in list(inline_rules_by_sig.items()):
                        if other_sig[0] == normalized and other_sig not in seen_sigs:
                            moved = other_rule
                            del inline_rules_by_sig[other_sig]
                            break
                    if moved is not None:
                        # Move: reconfigure scope, update target.
                        moved.target_value = target
                        if scope_label == _INLINE_SCOPE_COLUMN:
                            moved.scope_type = ScopeType.COLUMN
                            moved.scope_sheet = repr_sheet
                            moved.scope_column = repr_column
                        elif scope_label == _INLINE_SCOPE_SHEET:
                            moved.scope_type = ScopeType.SHEET
                            moved.scope_sheet = repr_sheet
                            moved.scope_column = None
                        else:
                            moved.scope_type = ScopeType.GLOBAL
                            moved.scope_sheet = None
                            moved.scope_column = None
                        inline_rules_by_sig[sig] = moved
                    else:
                        # Fresh create.
                        scope_type = {
                            _INLINE_SCOPE_COLUMN: ScopeType.COLUMN,
                            _INLINE_SCOPE_SHEET:  ScopeType.SHEET,
                            _INLINE_SCOPE_GLOBAL: ScopeType.GLOBAL,
                        }[scope_label]
                        # Find the raw source text — the edited grid shows
                        # raw_value for display; the rule should record that
                        # same raw text so the user recognises it.
                        raw_source = row["Value"]
                        new_rule = CleaningRule(
                            source_value=raw_source,
                            target_value=target,
                            action_type=ActionType.REPLACE,
                            match_mode=MatchMode.EXACT_NORMALIZED,
                            scope_type=scope_type,
                            scope_sheet=(repr_sheet if scope_type != ScopeType.GLOBAL else None),
                            scope_column=(repr_column if scope_type == ScopeType.COLUMN else None),
                            notes="Inline edit",
                        )
                        rules.append(new_rule)
                        inline_rules_by_sig[sig] = new_rule
                else:
                    # Update in place.
                    if existing.target_value != target:
                        existing.target_value = target
            # Empty target — no rule should exist for this signature.
            seen_sigs.add(sig)

        # Delete inline rules the user cleared (target emptied, and no
        # surviving signature for the same normalized source).
        cleared_norms = {
            row["_norm"] for _, row in edited.iterrows()
            if not str(row["Replace with"] or "").strip()
        }
        surviving_norms = {sig[0] for sig in inline_rules_by_sig}
        rules[:] = [
            r for r in rules
            if not _is_inline_rule(r)
            or r.normalized_source_value not in cleared_norms
            or r.normalized_source_value in surviving_norms
        ]

        # ------------------------------------------------------------------ #
        # Advanced rule editor (power features)
        # ------------------------------------------------------------------ #
        divider()
        _render_advanced_editor()

        # ------------------------------------------------------------------ #
        # Column profiles (compact grid)
        # ------------------------------------------------------------------ #
        _render_column_profiles(result.column_profiles, sheet_filter)
