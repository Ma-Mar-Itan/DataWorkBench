"""
Preview card.

Shows a sheet's first N rows in three tabs (Cleaned / Original / Side by
side). Changed cells are visually highlighted using a custom HTML render
driven by the ``changed_mask`` returned by ``build_preview``.
"""

from __future__ import annotations

from html import escape as html_escape

import pandas as pd
import streamlit as st

from core.preview import DEFAULT_PREVIEW_ROWS, build_preview, list_sheet_names
from ui.layout import card, caption


def _step_state() -> str:
    return "active" if st.session_state.get("scan_result") else "idle"


def _render_highlighted_table(
    clean_df: pd.DataFrame,
    orig_df: pd.DataFrame,
    mask: pd.DataFrame,
) -> None:
    """Render the cleaned DF as HTML with change highlighting.

    We use a custom HTML table because Streamlit's ``dataframe`` doesn't
    support per-cell background colouring without a full Styler pipeline
    that renders poorly on large data. Keep the rendering cap reasonable.
    """
    if clean_df.empty:
        return

    header_cells = "".join(
        f'<th style="padding:8px 12px; border-bottom:1px solid var(--tw-border); '
        f'font-size:11px; letter-spacing:0.08em; text-transform:uppercase; '
        f'color:var(--tw-ink-3); font-weight:600; text-align:left; background:var(--tw-surface-2);">'
        f'{html_escape(str(c))}</th>'
        for c in clean_df.columns
    )
    body_rows = []
    for r in range(len(clean_df)):
        cells = []
        for c in clean_df.columns:
            val = clean_df.iat[r, clean_df.columns.get_loc(c)]
            orig_val = orig_df.iat[r, orig_df.columns.get_loc(c)]
            is_changed = bool(mask.iat[r, mask.columns.get_loc(c)])
            display = "" if val is None else str(val)
            if is_changed and val is None:
                style = "background: var(--tw-warn-soft); color: var(--tw-warn); font-style: italic;"
                tooltip = f'was: {orig_val}'
                display = "(blank)"
            elif is_changed:
                style = "background: var(--tw-accent-soft); color: var(--tw-accent); font-weight:500;"
                tooltip = f'was: {orig_val}'
            else:
                style = "color: var(--tw-ink-2);"
                tooltip = ""
            tooltip_attr = f' title="{html_escape(str(tooltip))}"' if tooltip else ""
            cells.append(
                f'<td{tooltip_attr} style="padding:6px 12px; border-bottom:1px solid var(--tw-border); '
                f'font-size:12.5px; {style}">{html_escape(display)}</td>'
            )
        body_rows.append(f'<tr>{"".join(cells)}</tr>')

    st.markdown(
        f"""
        <div style="border:1px solid var(--tw-border); border-radius:var(--tw-radius);
                    overflow:auto; max-height:500px;">
          <table style="border-collapse:collapse; width:100%; font-family:var(--tw-font-sans);">
            <thead><tr>{header_cells}</tr></thead>
            <tbody>{"".join(body_rows)}</tbody>
          </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_preview_section() -> None:
    with card(
        step=5,
        step_state=_step_state(),
        eyebrow="Verification",
        title="Preview output",
        subtitle=(
            "Apply active rules to a chosen sheet and inspect the result before "
            "generating the final workbook. Changed cells are highlighted; "
            "hover to see the original value."
        ),
    ):
        if "uploaded_bytes" not in st.session_state or st.session_state.get("scan_result") is None:
            caption("Complete the workbook scan to enable preview.")
            return

        try:
            sheet_names = list_sheet_names(st.session_state["uploaded_bytes"])
        except Exception as e:  # noqa: BLE001
            st.error(f"Could not read workbook for preview: {e}")
            return

        c1, c2, c3 = st.columns([3, 2, 3])
        with c1:
            default_idx = 0
            stored = st.session_state.get("preview_sheet")
            if stored in sheet_names:
                default_idx = sheet_names.index(stored)
            sheet = st.selectbox("Sheet", sheet_names, index=default_idx)
            st.session_state["preview_sheet"] = sheet
        with c2:
            max_rows = st.number_input(
                "Rows to render",
                min_value=10,
                max_value=1000,
                value=DEFAULT_PREVIEW_ROWS,
                step=10,
            )
        with c3:
            pass

        rules = st.session_state.get("rules", [])

        try:
            orig_df, clean_df, mask = build_preview(
                st.session_state["uploaded_bytes"],
                sheet,
                rules,
                max_rows=int(max_rows),
            )
        except Exception as e:  # noqa: BLE001
            st.error(f"Could not build preview: {e}")
            return

        if orig_df.empty:
            caption(f"Sheet “{sheet}” has no data in the first {int(max_rows)} rows.")
            return

        # Change count summary.
        changed_count = int(mask.sum().sum())
        st.markdown(
            f'<div style="margin:4px 0 12px; font-size:12.5px; color:var(--tw-ink-3);">'
            f'<b>{changed_count:,}</b> cell{"s" if changed_count != 1 else ""} would change '
            f'in the first {len(orig_df):,} row{"s" if len(orig_df) != 1 else ""} of this sheet.</div>',
            unsafe_allow_html=True,
        )

        tab_clean, tab_orig, tab_side = st.tabs(["Cleaned", "Original", "Side by side"])
        with tab_clean:
            _render_highlighted_table(clean_df, orig_df, mask)
        with tab_orig:
            st.dataframe(orig_df, use_container_width=True, hide_index=True, height=420)
        with tab_side:
            co, cc = st.columns(2)
            with co:
                st.markdown(
                    '<div style="font-size:11px; letter-spacing:0.1em; text-transform:uppercase; '
                    'color:var(--tw-ink-4); font-weight:600; margin-bottom:6px;">Original</div>',
                    unsafe_allow_html=True,
                )
                st.dataframe(orig_df, use_container_width=True, hide_index=True, height=380)
            with cc:
                st.markdown(
                    '<div style="font-size:11px; letter-spacing:0.1em; text-transform:uppercase; '
                    'color:var(--tw-accent); font-weight:600; margin-bottom:6px;">Cleaned</div>',
                    unsafe_allow_html=True,
                )
                _render_highlighted_table(clean_df, orig_df, mask)
