"""
Value Explorer card.

Browses every unique value extracted from the workbook with filters (sheet,
column, classification, missing-only, frequency floor, search). Gives the
user the evidence they need to decide which values deserve a rule.

The "Add rule for selected" button pre-fills a rule in session state that
the Cleaning Rules card picks up on next render.
"""

from __future__ import annotations

from typing import List

import pandas as pd
import streamlit as st

from models.schemas import (
    ActionType,
    CleaningRule,
    ExtractedValue,
    MatchMode,
    ScopeType,
    ValueClass,
)
from ui.layout import caption, card, chip, html_block, value_class_badge


# --------------------------------------------------------------------------- #

_CLASS_FILTER_OPTIONS = [
    ("All classes", None),
    ("Category",      ValueClass.TEXT_CATEGORY),
    ("Numeric-like",  ValueClass.NUMERIC_LIKE),
    ("Mixed alnum",   ValueClass.MIXED_ALNUM),
    ("Missing token", ValueClass.MISSING_TOKEN),
    ("Header label",  ValueClass.HEADER_LABEL),
    ("Date-like",     ValueClass.DATE_LIKE),
    ("Free text",     ValueClass.FREE_TEXT),
    ("Low frequency", ValueClass.LOW_FREQUENCY),
]


def _step_state() -> str:
    return "active" if st.session_state.get("scan_result") else "idle"


def _filter_values(
    values: List[ExtractedValue],
    *,
    search: str,
    sheet: str,
    column: str,
    klass: ValueClass | None,
    missing_only: bool,
    min_frequency: int,
) -> List[ExtractedValue]:
    out = values
    if search:
        needle = search.strip().casefold()
        if needle:
            out = [v for v in out if needle in v.raw_value.casefold() or needle in v.normalized_value]
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
    return out


# --------------------------------------------------------------------------- #

def render_explorer_section() -> None:
    result = st.session_state.get("scan_result")

    with card(
        step=3,
        step_state=_step_state(),
        eyebrow="Inspection",
        title="Value explorer",
        subtitle=(
            "Browse every unique string value in the workbook. Filter by "
            "sheet, column, classification, or frequency. Select values and "
            "seed cleaning rules from your selection."
        ),
    ):
        if result is None:
            caption("Scan the workbook above to populate the explorer.")
            return
        if result.unique_value_count == 0:
            caption("No string values were extracted.")
            return

        # -------- Filter bar --------
        f1, f2, f3, f4 = st.columns([3, 2, 2, 2])
        with f1:
            search = st.text_input(
                "Search", placeholder="Filter by raw or normalized text…",
                label_visibility="collapsed",
            )
        with f2:
            sheet_options = ["All sheets"] + result.sheet_names
            sheet_filter = st.selectbox("Sheet", sheet_options, label_visibility="collapsed")
        with f3:
            cols_by_sheet = result.columns_by_sheet()
            if sheet_filter == "All sheets":
                all_cols: list[str] = []
                seen = set()
                for s in result.sheet_names:
                    for c in cols_by_sheet.get(s, []):
                        if c not in seen:
                            seen.add(c)
                            all_cols.append(c)
                column_options = ["All columns"] + all_cols
            else:
                column_options = ["All columns"] + cols_by_sheet.get(sheet_filter, [])
            column_filter = st.selectbox("Column", column_options, label_visibility="collapsed")
        with f4:
            class_filter_label = st.selectbox(
                "Class",
                [label for label, _ in _CLASS_FILTER_OPTIONS],
                label_visibility="collapsed",
            )
        class_filter = dict(_CLASS_FILTER_OPTIONS)[class_filter_label]

        g1, g2, g3 = st.columns([1, 1, 4])
        with g1:
            missing_only = st.checkbox("Missing only", value=False)
        with g2:
            min_freq = st.number_input("Min. freq", min_value=1, max_value=10000, value=1, step=1)
        with g3:
            html_block("")

        filtered = _filter_values(
            result.values,
            search=search,
            sheet=sheet_filter,
            column=column_filter,
            klass=class_filter,
            missing_only=missing_only,
            min_frequency=int(min_freq),
        )

        # -------- Summary line --------
        html_block(f'<div style="margin:4px 0 10px; font-size:12.5px; color:var(--tw-ink-3);">'
            f'<b>{len(filtered):,}</b> of <b>{result.unique_value_count:,}</b> unique values match filters.'
            f'</div>')

        if not filtered:
            html_block('<div style="margin-top:6px; padding:18px; text-align:center; '
                'color:var(--tw-ink-3); font-size:13px; background:var(--tw-surface-2); '
                'border:1px dashed var(--tw-border-strong); border-radius:var(--tw-radius);">'
                'No values match the current filters.</div>')
            return

        # -------- Table --------
        # Cap to 500 rows to keep the DOM sane. Users can narrow filters for more.
        display = filtered[:500]
        rows = []
        for v in display:
            rows.append({
                "Select": False,
                "Value": v.raw_value,
                "Class": v.value_class.value,
                "Count": v.frequency,
                "Sheets": ", ".join(v.sheets) if len(v.sheets) <= 3
                          else f"{', '.join(v.sheets[:3])} +{len(v.sheets)-3}",
                "Columns": ", ".join(v.columns) if len(v.columns) <= 3
                           else f"{', '.join(v.columns[:3])} +{len(v.columns)-3}",
                "Sample": v.sample_locations[0] if v.sample_locations else "",
                "_normalized": v.normalized_value,
            })
        df = pd.DataFrame(rows)

        edited = st.data_editor(
            df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Select": st.column_config.CheckboxColumn("✓", width="small", help="Select for rule seeding."),
                "Value":  st.column_config.TextColumn("Value", disabled=True, width="large"),
                "Class":  st.column_config.TextColumn("Class", disabled=True, width="small"),
                "Count":  st.column_config.NumberColumn("Count", disabled=True, width="small"),
                "Sheets": st.column_config.TextColumn("Sheets", disabled=True, width="medium"),
                "Columns":st.column_config.TextColumn("Columns", disabled=True, width="medium"),
                "Sample": st.column_config.TextColumn("Sample cell", disabled=True, width="small"),
                "_normalized": None,
            },
            num_rows="fixed",
            height=min(560, 56 + 35 * len(display)),
            key="explorer_editor",
        )

        if len(filtered) > 500:
            caption(f"Showing first 500 values. Narrow filters to see more.")

        # -------- Seed rules from selection --------
        selected = edited[edited["Select"] == True]  # noqa: E712 — pandas comparison
        sel_count = len(selected)

        s1, s2 = st.columns([2, 3])
        with s1:
            html_block(f'<div style="padding-top:6px; font-size:12.5px; color:var(--tw-ink-3);">'
                f'<b>{sel_count}</b> value{"s" if sel_count != 1 else ""} selected.</div>')
        with s2:
            act_c1, act_c2 = st.columns(2)
            with act_c1:
                seed_map = st.button(
                    "Seed replace rules",
                    use_container_width=True,
                    disabled=sel_count == 0,
                    help="Create draft rules (source → target blank) for each selected value. Scope starts as Global.",
                )
            with act_c2:
                seed_blank = st.button(
                    "Seed blank-out rules",
                    use_container_width=True,
                    disabled=sel_count == 0,
                    help="Create rules that blank each selected value. Useful for missing tokens.",
                )

        if seed_map or seed_blank:
            rules: list[CleaningRule] = st.session_state.setdefault("rules", [])
            existing_sources = {(r.source_value, r.scope_type, r.scope_sheet, r.scope_column) for r in rules}
            action = ActionType.SET_BLANK if seed_blank else ActionType.REPLACE
            match_mode = MatchMode.EXACT_NORMALIZED
            added = 0
            for _, row in selected.iterrows():
                src = str(row["Value"])
                key = (src, ScopeType.GLOBAL, None, None)
                if key in existing_sources:
                    continue
                rules.append(CleaningRule(
                    source_value=src,
                    target_value="",
                    action_type=action,
                    match_mode=match_mode,
                    scope_type=ScopeType.GLOBAL,
                    notes="Seeded from value explorer",
                ))
                added += 1
            st.success(f"Added {added} draft rule{'s' if added != 1 else ''} to the workspace.")

        # -------- Column profiles --------
        html_block('<div style="margin-top:22px; padding-top:18px; border-top:1px solid var(--tw-border);"></div>')
        html_block('<div style="font-size:11px; letter-spacing:0.12em; text-transform:uppercase; '
            'color:var(--tw-ink-4); font-weight:600; margin-bottom:10px;">Column profiles</div>')

        # Filter profiles to currently-selected sheet (if any).
        profiles_to_show = result.column_profiles
        if sheet_filter != "All sheets":
            profiles_to_show = [p for p in profiles_to_show if p.sheet == sheet_filter]
        if not profiles_to_show:
            caption("No columns to profile for the current filter.")
            return

        # Display top-k columns by unique-value count — most interesting first.
        profiles_to_show = sorted(profiles_to_show, key=lambda p: -p.unique_count)[:12]

        for p in profiles_to_show:
            with st.expander(
                f"{p.sheet} · {p.column}  ·  {p.unique_count:,} unique · "
                f"{p.non_empty_count:,} non-empty"
                + (f"  ·  {p.missing_like_count:,} missing-like" if p.missing_like_count else ""),
                expanded=False,
            ):
                if not p.top_values:
                    caption("No string values in this column.")
                    continue
                rows = "".join(
                    f'<tr><td style="padding:3px 10px 3px 0; font-family:var(--tw-font-mono); '
                    f'font-size:12.5px; color:var(--tw-ink);">{raw}</td>'
                    f'<td style="padding:3px 0; font-family:var(--tw-font-mono); font-size:12.5px; '
                    f'color:var(--tw-ink-3); text-align:right;">{count:,}</td></tr>'
                    for raw, count in p.top_values
                )
                html_block(f'<table style="width:100%; border-collapse:collapse;">{rows}</table>')
