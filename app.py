"""
Main entry for the data-cleaning Streamlit app.

Layout mirrors a desktop productivity tool:
    +----------------------------------------------------------+
    |  topbar (brand, search, status, actions)                 |
    +--------+-------------------------------------------------+
    |  nav   |   workspace (stats + table + panels)            |
    |  rail  |                                                 |
    +--------+-------------------------------------------------+
"""
from __future__ import annotations

import streamlit as st

from ui.components import render_navrail, render_topbar
from ui.styles import CSS
from ui.views import (
    render_export, render_preview, render_rules,
    render_scan, render_stats, render_upload,
)


# --------------------------------------------------------------------- #
# Page config  -- must be the very first streamlit call
# --------------------------------------------------------------------- #
st.set_page_config(
    page_title="Scrubline — Spreadsheet data cleaning",
    page_icon="🧼",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Inject global CSS
st.markdown(CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------- #
# Session defaults
# --------------------------------------------------------------------- #
def _init_state() -> None:
    defaults = {
        "view":          "upload",
        "scan_state":    "idle",    # "idle" | "running" | "done"
        "scan_rows":     None,
        "global_search": "",
        "workbook_meta": None,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


_init_state()


# --------------------------------------------------------------------- #
# Top bar
# --------------------------------------------------------------------- #
query = render_topbar(
    product_name="Scrubline",
    tag="Spreadsheet data cleaner",
    scan_state=st.session_state.scan_state,
    rows_scanned=st.session_state.scan_rows,
)
st.session_state.global_search = query


# --------------------------------------------------------------------- #
# Body layout: nav rail + workspace
# --------------------------------------------------------------------- #
nav_col, work_col = st.columns([1, 5], gap="small")

with nav_col:
    view = render_navrail()

with work_col:
    if   view == "upload":  render_upload()
    elif view == "scan":    render_scan(query)
    elif view == "rules":   render_rules()
    elif view == "preview": render_preview()
    elif view == "stats":   render_stats()
    elif view == "export":  render_export()
