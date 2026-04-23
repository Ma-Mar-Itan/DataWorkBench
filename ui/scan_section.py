"""
Scan summary card.

Runs the extractor and reports sheet count, text-cell count, unique
values, likely missing tokens, and likely categorical candidates.
"""

from __future__ import annotations

import streamlit as st

from core.extractor import scan_workbook
from ui.layout import card, caption, chip, render_metrics


def _step_state() -> str:
    if "scan_result" in st.session_state:
        return "done"
    if "uploaded_bytes" in st.session_state:
        return "active"
    return "idle"


def render_scan_section() -> None:
    """Render the scan card. Requires an uploaded file."""
    uploaded = "uploaded_bytes" in st.session_state

    with card(
        step=2,
        step_state=_step_state(),
        eyebrow="Discovery",
        title="Scan workbook",
        subtitle=(
            "Walk every sheet, collect unique string values with their "
            "column and frequency context, and classify each value as a "
            "likely category, missing token, numeric-looking string, or "
            "free text."
        ),
    ):
        if not uploaded:
            caption("Upload a workbook to enable scanning.")
            return

        # Action row.
        a, _, info = st.columns([2, 1, 4])
        with a:
            rescan = st.button("Scan workbook", type="primary", use_container_width=True)
        with info:
            if "scan_result" in st.session_state:
                st.markdown(
                    f'<div style="padding-top:6px; font-size:12.5px; color:var(--tw-ink-3);">'
                    f'Last scan complete. {chip("Ready to build rules", "accent")}</div>',
                    unsafe_allow_html=True,
                )
            else:
                caption("Formula cells are detected and skipped. Nothing is written to disk.")

        if rescan:
            with st.spinner("Scanning workbook…"):
                try:
                    result = scan_workbook(st.session_state["uploaded_bytes"])
                except Exception as e:  # noqa: BLE001
                    st.error(f"Could not read workbook: {e}")
                    return
            st.session_state["scan_result"] = result

        result = st.session_state.get("scan_result")
        if result is None:
            return

        render_metrics(
            [
                ("Sheets", f"{result.sheet_count}", "in workbook"),
                ("String cells", f"{result.string_cells_scanned:,}", "scanned"),
                ("Unique values", f"{result.unique_value_count:,}", "after normalize"),
                ("Missing tokens", f"{result.missing_token_count:,}", "detected"),
            ],
            accent_index=2,
        )

        st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)

        render_metrics(
            [
                ("Categorical candidates", f"{result.likely_categorical_count:,}", "freq ≥ 2, short text"),
                ("Header labels", f"{result.header_label_count:,}", "first-row values"),
                ("Columns profiled", f"{len(result.column_profiles):,}", "across all sheets"),
                ("Formulas skipped", f"{result.formula_cells_skipped:,}", "preserved"),
            ],
        )

        if result.unique_value_count == 0:
            st.markdown(
                '<div style="margin-top:16px; padding:12px 14px; border-radius:var(--tw-radius); '
                'background: var(--tw-warn-soft); border:1px solid var(--tw-warn-border); '
                'font-size:13px; color:var(--tw-warn);">'
                'No string values were detected. There is nothing to clean in this workbook.'
                '</div>',
                unsafe_allow_html=True,
            )
