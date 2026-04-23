"""
View renderers — one function per section in the left nav.

Keeping each view in its own function (rather than separate files) makes
the flow easy to follow and keeps reloads fast. If any view grows past
~200 lines, split it out.
"""
from __future__ import annotations

import html
from io import BytesIO

import pandas as pd
import streamlit as st

from ui import demo_data as dd
from ui.components import (
    chip, count_badge, kv_list, page_header, panel_close, panel_open,
    progress_bar, stat_cards,
)


# ===================================================================== #
# 1. Upload
# ===================================================================== #
def render_upload() -> None:
    page_header(
        "Step 1",
        "Upload workbook",
        "Drop an .xlsx file to begin scanning. Your file stays local to this session.",
    )

    left, right = st.columns([1.3, 1], gap="large")

    # --- Upload panel -------------------------------------------------
    with left:
        panel_open(
            "Workbook source",
            "Supported formats: .xlsx (Excel 2007+). Files up to 200 MB.",
        )
        uploaded = st.file_uploader(
            "Drop your file",
            type=["xlsx"],
            label_visibility="collapsed",
            key="uploader",
        )
        if uploaded is not None:
            st.session_state.uploaded_file_bytes = uploaded.getvalue()
            st.session_state.uploaded_file_name  = uploaded.name
            # NOTE: real backend would read + scan here. For the UI
            # phase we populate demo metadata so the rest of the app is
            # realistically populated.
            if st.session_state.get("workbook_meta") is None:
                meta = dd.demo_workbook_meta()
                meta["filename"] = uploaded.name
                meta["size_bytes"] = len(st.session_state.uploaded_file_bytes)
                st.session_state.workbook_meta = meta

        c1, c2, _ = st.columns([1, 1, 2])
        with c1:
            scan_clicked = st.button("Scan workbook", type="primary", use_container_width=True)
        with c2:
            st.button("Load sample", use_container_width=True)
        if scan_clicked:
            st.session_state.scan_state = "done"
            st.session_state.scan_rows  = st.session_state.workbook_meta["row_count"] if st.session_state.get("workbook_meta") else 0
            st.session_state.view       = "scan"
            st.rerun()
        panel_close()

    # --- Summary panel -----------------------------------------------
    with right:
        panel_open("File summary")
        wb = st.session_state.get("workbook_meta")
        if not wb:
            st.markdown(
                '<div style="color:var(--text-faint);font-size:13px;padding:6px 0;">'
                "Upload a workbook to see its summary."
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            kv_list([
                ("File",        wb["filename"]),
                ("Size",        _fmt_bytes(wb["size_bytes"])),
                ("Sheets",      wb["sheet_count"]),
                ("Rows",        f"{wb['row_count']:,}"),
                ("Columns",     wb["column_count"]),
                ("Uploaded",    wb["uploaded_at"]),
            ])
            st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
            rows = "".join(
                f"<tr>"
                f"<td style='padding:6px 0;font-size:13px;'>{html.escape(s['name'])}</td>"
                f"<td style='padding:6px 0;font-size:13px;color:var(--text-muted);text-align:right;'>{s['rows']:,} rows</td>"
                f"<td style='padding:6px 0;font-size:13px;color:var(--text-faint);text-align:right;'>{s['cols']} cols</td>"
                f"</tr>"
                for s in wb["sheets"]
            )
            st.markdown(
                "<table style='width:100%;border-collapse:collapse;'>"
                "<thead><tr>"
                "<th style='text-align:left;font-size:11px;color:var(--text-faint);text-transform:uppercase;letter-spacing:0.06em;padding-bottom:6px;border-bottom:1px solid var(--divider);'>Sheet</th>"
                "<th style='text-align:right;font-size:11px;color:var(--text-faint);text-transform:uppercase;letter-spacing:0.06em;padding-bottom:6px;border-bottom:1px solid var(--divider);'>Rows</th>"
                "<th style='text-align:right;font-size:11px;color:var(--text-faint);text-transform:uppercase;letter-spacing:0.06em;padding-bottom:6px;border-bottom:1px solid var(--divider);'>Cols</th>"
                f"</tr></thead><tbody>{rows}</tbody></table>",
                unsafe_allow_html=True,
            )
        panel_close()


# ===================================================================== #
# 2. Scan results
# ===================================================================== #
def render_scan(query: str) -> None:
    page_header(
        "Step 2",
        "Scan results",
        "Repeated values across the workbook, with counts and locations.",
    )

    s = dd.demo_scan_summary()
    stat_cards([
        {"label": "Sheets",           "value": s["sheets"]},
        {"label": "Rows",             "value": f"{s['rows']:,}"},
        {"label": "Columns",          "value": s["columns"]},
        {"label": "Unique values",    "value": f"{s['unique_string_values']:,}"},
        {"label": "Likely missing",   "value": s["missing_tokens"], "delta": "5 distinct tokens", "delta_kind": ""},
    ])

    # --- Filters row --------------------------------------------------
    panel_open()
    f1, f2, f3, f4, f5 = st.columns([2, 1.4, 1.4, 1.4, 1])
    with f1:
        local_q = st.text_input(
            "Filter values",
            value=query,
            placeholder="Filter within results",
            key="scan_filter",
        )
    with f2:
        st.selectbox("Sheet", ["All sheets", "Responses", "Demographics", "Free text", "Lookup"], key="scan_sheet")
    with f3:
        st.selectbox("Column", ["All columns", "gender", "country", "consent", "region", "income"], key="scan_column")
    with f4:
        st.selectbox("Value class", ["Any", "categorical", "missing", "numeric-like", "date-like", "free text"], key="scan_class")
    with f5:
        st.selectbox("Min count", ["1", "10", "50", "100", "500"], index=1, key="scan_mincount")
    panel_close()

    # --- Results table ------------------------------------------------
    rows = dd.demo_repeated_values()
    if local_q:
        lq = local_q.lower()
        rows = [r for r in rows if lq in r["value"].lower() or lq in r["normalized"].lower()]

    df = pd.DataFrame(rows)
    df = df.rename(columns={
        "value": "Value",
        "normalized": "Normalized",
        "count": "Count",
        "sheets": "Sheets",
        "columns": "Columns",
        "class": "Class",
    })

    panel_open("Repeated values", f"{len(df)} values match the current filters")
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=min(560, 56 + 36 * len(df)),
        column_config={
            "Count":      st.column_config.NumberColumn(format="%d"),
            "Value":      st.column_config.TextColumn(width="medium"),
            "Normalized": st.column_config.TextColumn(width="small"),
            "Sheets":     st.column_config.TextColumn(width="medium"),
            "Columns":    st.column_config.TextColumn(width="medium"),
            "Class":      st.column_config.TextColumn(width="small"),
        },
    )
    c1, c2, _ = st.columns([1.2, 1.2, 4])
    with c1:
        if st.button("Create rule from selection", type="primary"):
            st.session_state.view = "rules"
            st.rerun()
    with c2:
        st.button("Export scan report")
    panel_close()


# ===================================================================== #
# 3. Cleaning rules
# ===================================================================== #
def render_rules() -> None:
    page_header(
        "Step 3",
        "Cleaning rules",
        "Whole-cell matching only. Replace, blank, and scope each rule precisely.",
    )

    # Bootstrap rules into state
    if "rules" not in st.session_state:
        st.session_state.rules = dd.demo_rules()

    # --- Quick add ---------------------------------------------------
    panel_open("Quick add rule", "A shortcut. For bulk editing use the rules grid below.")
    q1, q2, q3, q4, q5 = st.columns([2, 2, 1.4, 1.4, 1])
    with q1:
        src = st.text_input("Source value", placeholder="e.g. yes", key="qa_src")
    with q2:
        tgt = st.text_input("Replacement", placeholder="e.g. Yes", key="qa_tgt")
    with q3:
        scope = st.selectbox("Scope", ["workbook", "sheet", "column"], key="qa_scope")
    with q4:
        match = st.selectbox("Match mode", ["exact_normalized", "exact_raw"], key="qa_match")
    with q5:
        st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
        if st.button("Add rule", type="primary", use_container_width=True):
            if src:
                r = dd.new_rule()
                r.update({
                    "source_value": src,
                    "target_value": tgt,
                    "scope_type": scope,
                    "match_mode": match,
                    "action_type": "set_blank" if tgt == "" else "replace",
                })
                st.session_state.rules.insert(0, r)
                st.rerun()
    panel_close()

    # --- Rules grid ---------------------------------------------------
    panel_open("Rules", f"{sum(1 for r in st.session_state.rules if r['enabled'])} of {len(st.session_state.rules)} enabled")
    df = pd.DataFrame(st.session_state.rules)
    edited = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        height=min(480, 56 + 40 * len(df)),
        key="rules_editor",
        column_config={
            "rule_id":      st.column_config.TextColumn("ID", width="small", disabled=True),
            "source_value": st.column_config.TextColumn("Source value", width="medium"),
            "target_value": st.column_config.TextColumn("Replacement", width="medium"),
            "action_type":  st.column_config.SelectboxColumn("Action", options=["replace", "set_blank"], width="small"),
            "match_mode":   st.column_config.SelectboxColumn("Match mode", options=["exact_raw", "exact_normalized"], width="small"),
            "scope_type":   st.column_config.SelectboxColumn("Scope", options=["workbook", "sheet", "column"], width="small"),
            "scope_sheet":  st.column_config.TextColumn("Sheet", width="small"),
            "scope_column": st.column_config.TextColumn("Column", width="small"),
            "enabled":      st.column_config.CheckboxColumn("On", width="small"),
        },
    )
    st.session_state.rules = edited.to_dict(orient="records")

    c1, c2, c3, _ = st.columns([1.2, 1.2, 1.2, 3])
    with c1:
        if st.button("Run preview", type="primary"):
            st.session_state.view = "preview"
            st.rerun()
    with c2:
        st.button("Save ruleset")
    with c3:
        st.button("Load ruleset")
    panel_close()


# ===================================================================== #
# 4. Preview
# ===================================================================== #
def render_preview() -> None:
    page_header(
        "Step 4",
        "Preview changes",
        "Before and after, per sheet. Review every change the ruleset would produce.",
    )

    # top summary
    stat_cards([
        {"label": "Changed cells",     "value": 413},
        {"label": "Sheets affected",   "value": 3},
        {"label": "Columns affected",  "value": 7},
        {"label": "Rules fired",       "value": 3},
    ])

    # sheet picker
    panel_open()
    c1, c2, _ = st.columns([2, 2, 4])
    with c1:
        sheet = st.selectbox("Sheet", ["Responses", "Demographics", "Free text", "Lookup"], key="prv_sheet")
    with c2:
        st.selectbox("Show", ["All changes", "Only flagged", "By rule"], key="prv_show")
    panel_close()

    # before/after tabs
    tab_changes, tab_rules = st.tabs(["Changed cells", "Rules fired"])
    with tab_changes:
        rows = dd.demo_preview_rows(sheet)
        df = pd.DataFrame(rows).rename(columns={
            "row": "Row", "column": "Column", "before": "Before", "after": "After", "rule": "Rule"
        })
        st.dataframe(df, use_container_width=True, hide_index=True, height=280)
    with tab_rules:
        summary = dd.demo_rules_summary()
        for item in summary:
            st.markdown(
                f"""
                <div style="display:flex;justify-content:space-between;align-items:center;
                            padding:10px 14px;border:1px solid var(--border);border-radius:10px;
                            background:var(--panel-soft);margin-bottom:8px;">
                  <div>
                    <div style="font-size:11px;color:var(--text-faint);text-transform:uppercase;letter-spacing:0.06em;font-weight:600;">Rule {html.escape(item['rule_id'])}</div>
                    <div style="font-size:13.5px;font-weight:500;color:var(--text);">{html.escape(item['label'])}</div>
                  </div>
                  <div><span class="chip accent">{item['fires']} cells</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    col_a, col_b, _ = st.columns([1.2, 1.2, 4])
    with col_a:
        st.button("Apply and export", type="primary", on_click=lambda: st.session_state.update({"view": "export"}))
    with col_b:
        st.button("Back to rules", on_click=lambda: st.session_state.update({"view": "rules"}))


# ===================================================================== #
# 5. Statistics
# ===================================================================== #
def render_stats() -> None:
    page_header(
        "Insights",
        "Descriptive statistics",
        "Automatic summaries per column, with before/after cleaning comparisons.",
    )

    # Workbook cards
    s = dd.demo_scan_summary()
    stat_cards([
        {"label": "Sheets",            "value": s["sheets"]},
        {"label": "Rows",              "value": f"{s['rows']:,}"},
        {"label": "Columns",           "value": s["columns"]},
        {"label": "Total missing",     "value": "4,193"},
        {"label": "Unique string vals","value": f"{s['unique_string_values']:,}"},
    ])

    # Numeric + categorical
    left, right = st.columns(2, gap="medium")
    with left:
        panel_open("Numeric columns", "Mean, median, quartiles, spread.")
        st.dataframe(
            pd.DataFrame(dd.demo_numeric_stats()),
            use_container_width=True, hide_index=True, height=230,
        )
        panel_close()
    with right:
        panel_open("Categorical columns", "Mode, cardinality, dominant values.")
        st.dataframe(
            pd.DataFrame(dd.demo_categorical_stats()),
            use_container_width=True, hide_index=True, height=230,
        )
        panel_close()

    # Missingness
    panel_open("Missingness", "Columns with the highest missing rate.")
    miss = dd.demo_missingness()
    for m in miss:
        st.markdown(
            f"""
            <div style="padding:10px 0;border-bottom:1px solid var(--divider);">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                <div style="font-size:13.5px;font-weight:500;">{html.escape(m['sheet'])} · {html.escape(m['column'])}</div>
                <div style="font-size:12.5px;color:var(--text-muted);">{m['missing']:,} / {m['total']:,} ({m['pct']:.1f}%)</div>
              </div>
              {progress_bar(m['pct'], 'warn' if m['pct'] > 20 else '')}
            </div>
            """,
            unsafe_allow_html=True,
        )
    panel_close()

    # Before vs after
    ba = dd.demo_before_after()
    panel_open("Before vs after cleaning", "Impact of the active ruleset.")
    stat_cards([
        {"label": "Cells changed",      "value": ba["changed_cells"],    "delta": "from 0", "delta_kind": "pos"},
        {"label": "Sheets affected",    "value": ba["affected_sheets"]},
        {"label": "Columns affected",   "value": ba["affected_columns"]},
        {"label": "Category reduction", "value": ba["category_reduction"]},
        {"label": "Cells blanked",      "value": ba["missing_added"],    "delta": "N/A tokens removed", "delta_kind": ""},
    ])
    panel_close()


# ===================================================================== #
# 6. Export
# ===================================================================== #
def render_export() -> None:
    page_header(
        "Step 6",
        "Export",
        "Produce the cleaned workbook, a statistics report, and a reusable ruleset.",
    )

    ba = dd.demo_before_after()
    panel_open("Final summary", "What this export will produce.")
    kv_list([
        ("Changed cells",    f"{ba['changed_cells']:,}"),
        ("Sheets affected",  ba["affected_sheets"]),
        ("Columns affected", ba["affected_columns"]),
        ("Rules applied",    "3 of 4 enabled"),
        ("Workbook",         (st.session_state.get("workbook_meta") or {}).get("filename", "—")),
    ])
    panel_close()

    # Three export cards
    c1, c2, c3 = st.columns(3, gap="medium")
    demo_bytes = _tiny_xlsx_bytes()

    with c1:
        panel_open("Cleaned workbook", "All rules applied, formulas preserved.")
        st.download_button(
            "Download .xlsx",
            data=demo_bytes,
            file_name="cleaned.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        panel_close()

    with c2:
        panel_open("Statistics report", "Full descriptive stats, before and after.")
        st.download_button(
            "Download .xlsx",
            data=demo_bytes,
            file_name="statistics_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        panel_close()

    with c3:
        panel_open("Ruleset", "Save as JSON to reapply on future files.")
        st.download_button(
            "Download .json",
            data=b'{"rules": []}',
            file_name="ruleset.json",
            mime="application/json",
            use_container_width=True,
        )
        panel_close()


# --------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------- #
def _fmt_bytes(n: int) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {u}" if u != "B" else f"{n} {u}"
        n /= 1024
    return f"{n:.1f} TB"


def _tiny_xlsx_bytes() -> bytes:
    """A tiny valid .xlsx placeholder so the download button actually works in the UI demo."""
    buf = BytesIO()
    pd.DataFrame({"placeholder": ["backend will produce the real file"]}).to_excel(buf, index=False)
    return buf.getvalue()
