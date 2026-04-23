"""
Cleaning Rules card — the heart of the workbench.

Structured as:
- Preset chooser (adds a batch of draft rules)
- Add-rule quick form (one rule, fast path)
- Rule grid (edit every field inline; enable/disable; delete)
- Validation summary
"""

from __future__ import annotations

from typing import List, Optional

import pandas as pd
import streamlit as st

from core.presets import PRESET_REGISTRY
from models.schemas import (
    ActionType,
    CleaningRule,
    MatchMode,
    ScopeType,
)
from ui.layout import caption, card, chip, html_block, rule as divider


# --------------------------------------------------------------------------- #

def _rules() -> List[CleaningRule]:
    return st.session_state.setdefault("rules", [])


def _step_state() -> str:
    if not st.session_state.get("scan_result"):
        return "idle"
    if _rules():
        return "active"
    return "active"


# --------------------------------------------------------------------------- #

def _render_preset_chooser() -> None:
    """Lets the user drop a batch of draft rules into the workspace."""
    preset_names = list(PRESET_REGISTRY.keys())
    c1, c2, c3 = st.columns([3, 2, 1])
    with c1:
        selected = st.selectbox(
            "Preset",
            ["— Choose a starter preset —"] + preset_names,
            label_visibility="collapsed",
        )
    with c2:
        scope_sheet = None
        scope_column = None
        if selected in PRESET_REGISTRY and PRESET_REGISTRY[selected]["scoped"]:
            result = st.session_state.get("scan_result")
            if result:
                sheets = ["— Global —"] + result.sheet_names
                picked = st.selectbox("Scope to sheet (optional)", sheets, label_visibility="collapsed")
                if picked != "— Global —":
                    scope_sheet = picked
                    cols = result.columns_by_sheet().get(picked, [])
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
        add = st.button("Add preset", use_container_width=True, disabled=(selected not in PRESET_REGISTRY))

    if selected in PRESET_REGISTRY:
        caption(PRESET_REGISTRY[selected]["description"])

    if add and selected in PRESET_REGISTRY:
        factory = PRESET_REGISTRY[selected]["factory"]
        if PRESET_REGISTRY[selected]["scoped"]:
            new_rules = factory(scope_sheet=scope_sheet, scope_column=scope_column)
        else:
            new_rules = factory()

        existing_keys = {
            (r.source_value, r.scope_type, r.scope_sheet, r.scope_column) for r in _rules()
        }
        added = 0
        for r in new_rules:
            key = (r.source_value, r.scope_type, r.scope_sheet, r.scope_column)
            if key not in existing_keys:
                _rules().append(r)
                added += 1
        st.success(f"Added {added} rule{'s' if added != 1 else ''} from preset.")


# --------------------------------------------------------------------------- #

def _render_quick_add(sheet_options: List[str], columns_by_sheet: dict) -> None:
    """Quick-add form: one rule at a time, minimal clicks."""
    with st.expander("➕ Add a rule", expanded=False):
        q1, q2, q3 = st.columns(3)
        with q1:
            src = st.text_input("Source value", key="qa_src", placeholder="male")
        with q2:
            tgt = st.text_input("Target value", key="qa_tgt", placeholder="1")
        with q3:
            action = st.selectbox(
                "Action",
                ["Replace", "Map code", "Set blank"],
                key="qa_action",
            )

        s1, s2, s3 = st.columns(3)
        with s1:
            match_mode_label = st.selectbox(
                "Match mode",
                ["Normalized (recommended)", "Raw (exact bytes)"],
                key="qa_mode",
            )
        with s2:
            scope_type_label = st.selectbox(
                "Scope",
                ["Global", "Sheet", "Column"],
                key="qa_scope",
            )
        with s3:
            scope_sheet = None
            scope_column = None
            if scope_type_label in ("Sheet", "Column") and sheet_options:
                scope_sheet = st.selectbox("Sheet", sheet_options, key="qa_scope_sheet")
                if scope_type_label == "Column" and scope_sheet:
                    cols = columns_by_sheet.get(scope_sheet, [])
                    if cols:
                        scope_column = st.selectbox("Column", cols, key="qa_scope_col")

        add_btn = st.button("Add rule", type="primary", use_container_width=True)
        if add_btn:
            if not src:
                st.warning("Source value is required.")
                return

            action_map = {
                "Replace":   ActionType.REPLACE,
                "Map code":  ActionType.MAP_CODE,
                "Set blank": ActionType.SET_BLANK,
            }
            scope_map = {"Global": ScopeType.GLOBAL, "Sheet": ScopeType.SHEET, "Column": ScopeType.COLUMN}
            mode = MatchMode.EXACT_NORMALIZED if match_mode_label.startswith("Normalized") else MatchMode.EXACT_RAW

            new_rule = CleaningRule(
                source_value=src,
                target_value=tgt,
                action_type=action_map[action],
                match_mode=mode,
                scope_type=scope_map[scope_type_label],
                scope_sheet=scope_sheet if scope_type_label in ("Sheet", "Column") else None,
                scope_column=scope_column if scope_type_label == "Column" else None,
            )
            errors = new_rule.validate()
            if errors:
                st.warning(" ".join(errors))
                return
            _rules().append(new_rule)
            st.success("Rule added.")


# --------------------------------------------------------------------------- #

def _render_rule_grid() -> None:
    """Tabular editor for all active rules."""
    rules = _rules()
    if not rules:
        html_block('<div style="padding:22px; text-align:center; '
            'color:var(--tw-ink-3); font-size:13px; background:var(--tw-surface-2); '
            'border:1px dashed var(--tw-border-strong); border-radius:var(--tw-radius);">'
            'No rules yet. Add one above, seed from the value explorer, '
            'or start from a preset.</div>')
        return

    # Build a DataFrame with editable fields where appropriate.
    rows = []
    for r in rules:
        rows.append({
            "On": r.enabled,
            "Source": r.source_value,
            "→": "→",
            "Target": r.target_value,
            "Action": r.action_type.value,
            "Mode": r.match_mode.value,
            "Scope": r.scope_type.value,
            "Sheet": r.scope_sheet or "",
            "Column": r.scope_column or "",
            "Delete": False,
            "_id": r.rule_id,
        })
    df = pd.DataFrame(rows)

    edited = st.data_editor(
        df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "On":     st.column_config.CheckboxColumn("On", width="small"),
            "Source": st.column_config.TextColumn("Source value", width="large"),
            "→":      st.column_config.TextColumn("", disabled=True, width="small"),
            "Target": st.column_config.TextColumn("Target", width="medium"),
            "Action": st.column_config.SelectboxColumn(
                "Action",
                options=[a.value for a in ActionType],
                width="small",
            ),
            "Mode":   st.column_config.SelectboxColumn(
                "Mode",
                options=[m.value for m in MatchMode],
                width="small",
            ),
            "Scope":  st.column_config.SelectboxColumn(
                "Scope",
                options=[s.value for s in ScopeType],
                width="small",
            ),
            "Sheet":  st.column_config.TextColumn("Sheet", width="medium"),
            "Column": st.column_config.TextColumn("Column", width="medium"),
            "Delete": st.column_config.CheckboxColumn("🗑", width="small"),
            "_id": None,
        },
        num_rows="fixed",
        height=min(520, 56 + 35 * len(rules)),
        key="rules_editor",
    )

    # Merge edited values back into the rule list.
    # We build a new list rather than mutating in place because of the
    # delete flag — simpler semantics.
    id_to_row = {row["_id"]: row for _, row in edited.iterrows()}
    new_rules: list[CleaningRule] = []
    deleted = 0
    for r in rules:
        row = id_to_row.get(r.rule_id)
        if row is None or bool(row.get("Delete")):
            deleted += 1
            continue
        # Update fields from the grid.
        r.enabled = bool(row.get("On", True))
        r.source_value = str(row.get("Source") or "")
        r.target_value = str(row.get("Target") or "")
        try:
            r.action_type = ActionType(row.get("Action", r.action_type.value))
            r.match_mode  = MatchMode(row.get("Mode", r.match_mode.value))
            r.scope_type  = ScopeType(row.get("Scope", r.scope_type.value))
        except ValueError:
            pass
        sheet_val = row.get("Sheet") or ""
        col_val = row.get("Column") or ""
        r.scope_sheet = sheet_val if sheet_val else None
        r.scope_column = col_val if col_val else None
        # Recompute normalized source since source_value may have changed.
        from core.normalizer import normalize_value
        r.normalized_source_value = normalize_value(r.source_value)
        new_rules.append(r)

    st.session_state["rules"] = new_rules

    if deleted:
        st.toast(f"Removed {deleted} rule{'s' if deleted != 1 else ''}.", icon="🗑")


# --------------------------------------------------------------------------- #

def _render_validation_summary() -> None:
    rules = _rules()
    if not rules:
        return
    total = len(rules)
    enabled = sum(1 for r in rules if r.enabled)
    errors: list[tuple[CleaningRule, list[str]]] = []
    for r in rules:
        errs = r.validate()
        if errs:
            errors.append((r, errs))

    html_block(f'<div style="margin-top:10px; font-size:12.5px; color:var(--tw-ink-3);">'
        f'{chip(f"{enabled}/{total} enabled", "accent")}'
        + (f' &nbsp; {chip(f"{len(errors)} invalid", "warn")}' if errors else "")
        + '</div>')

    if errors:
        with st.expander(f"⚠ {len(errors)} rule(s) have validation issues", expanded=False):
            for r, errs in errors:
                html_block(f'<div style="font-family:var(--tw-font-mono); font-size:12.5px; '
                    f'margin:4px 0; color:var(--tw-ink);"><b>{r.source_value or "(empty)"}'
                    f' → {r.target_value}</b></div>')
                for e in errs:
                    html_block(f'<div style="font-size:12px; color:var(--tw-warn); margin-left:12px;">• {e}</div>')


# --------------------------------------------------------------------------- #

def render_rules_section() -> None:
    result = st.session_state.get("scan_result")

    with card(
        step=4,
        step_state=_step_state(),
        eyebrow="Rules",
        title="Cleaning rules",
        subtitle=(
            "Define how values should be replaced, coded, or blanked. Each "
            "rule has a scope (global, one sheet, or one column) and a match "
            "mode (raw or whitespace-and-case normalized). Substring matching "
            "is never used — only whole cells match."
        ),
    ):
        if result is None:
            caption("Scan a workbook first so the rule editor knows about your sheets and columns.")
            return

        columns_by_sheet = result.columns_by_sheet()

        # --- Preset chooser ---
        html_block('<div style="font-size:11px; letter-spacing:0.12em; text-transform:uppercase; '
            'color:var(--tw-ink-4); font-weight:600; margin-bottom:8px;">Preset templates</div>')
        _render_preset_chooser()

        divider()

        # --- Quick add ---
        _render_quick_add(result.sheet_names, columns_by_sheet)

        # --- Grid ---
        html_block('<div style="font-size:11px; letter-spacing:0.12em; text-transform:uppercase; '
            'color:var(--tw-ink-4); font-weight:600; margin:14px 0 8px;">Active rules</div>')
        _render_rule_grid()
        _render_validation_summary()
