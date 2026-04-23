"""Upload card — unchanged in concept from v1 but re-themed."""

from __future__ import annotations

import streamlit as st

from ui.layout import card, caption, chip


_DOWNSTREAM_KEYS = (
    "scan_result",
    "rules",
    "generated_bytes",
    "generated_filename",
    "export_summary",
    "preview_sheet",
)


def _reset_downstream_state() -> None:
    for key in _DOWNSTREAM_KEYS:
        st.session_state.pop(key, None)


def _step_state() -> str:
    return "done" if "uploaded_bytes" in st.session_state else "active"


def render_upload_section() -> None:
    with card(
        step=1,
        step_state=_step_state(),
        eyebrow="Intake",
        title="Upload workbook",
        subtitle=(
            "Select an .xlsx file to scan. The file is read locally; no workbook "
            "data is transmitted. When run on Streamlit Community Cloud the file "
            "lives only in the container's session memory."
        ),
    ):
        uploaded = st.file_uploader(
            "Drop an .xlsx file or click to browse",
            type=["xlsx"],
            accept_multiple_files=False,
            label_visibility="collapsed",
        )

        if uploaded is None:
            if "uploaded_bytes" in st.session_state:
                st.session_state.pop("uploaded_bytes", None)
                st.session_state.pop("uploaded_name", None)
                _reset_downstream_state()
            caption(
                "Supported format: .xlsx (Excel 2007+). "
                "Legacy .xls files must be resaved as .xlsx before upload."
            )
            return

        file_bytes = uploaded.getvalue()
        file_name = uploaded.name
        file_size = len(file_bytes)

        previous_name = st.session_state.get("uploaded_name")
        previous_size = len(st.session_state.get("uploaded_bytes", b""))
        is_new = (file_name != previous_name) or (file_size != previous_size)
        if is_new:
            st.session_state["uploaded_bytes"] = file_bytes
            st.session_state["uploaded_name"] = file_name
            _reset_downstream_state()

        kb = file_size / 1024
        size_label = f"{kb:,.1f} KB" if kb < 1024 else f"{kb / 1024:,.2f} MB"
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; justify-content:space-between;
                        background: var(--tw-ok-soft); border: 1px solid var(--tw-ok-border);
                        border-radius: var(--tw-radius); padding: 12px 16px; margin-top: 14px;">
              <div>
                <div style="font-weight:600; color:var(--tw-ink); font-size:14px;">{file_name}</div>
                <div style="font-size:12px; color:var(--tw-ink-3); margin-top:2px;">
                  {size_label} · ready for scan
                </div>
              </div>
              <div>{chip("Loaded", "ok")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
