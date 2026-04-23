"""
Data Cleaning Workbench — Streamlit entry point.

Shell layout:

    ┌──────────────── Top application bar ────────────────┐
    ├──────── Secondary dark workspace band ──────────────┤
    │                                                      │
    │  ┌────────────┐  ┌────────────────────────────────┐ │
    │  │ Left panel │  │ 1. Upload workbook             │ │
    │  │  Stages    │  │ 2. Scan workbook               │ │
    │  │  Session   │  │ 3. Value explorer              │ │
    │  │  Notes     │  │ 4. Cleaning rules              │ │
    │  │            │  │ 5. Preview output              │ │
    │  │            │  │ 6. Generate cleaned workbook   │ │
    │  │            │  │ (library) Saved rule sets       │ │
    │  └────────────┘  └────────────────────────────────┘ │
    │                                                      │
    └──────────────────── Footer ──────────────────────────┘
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

from core.ruleset_store import DEFAULT_RULESET_DIR, RuleSetStore
from ui.export_section import render_export_section
from ui.explorer_section import render_explorer_section
from ui.layout import (
    inject_global_chrome,
    render_appbar,
    render_control_panel,
    render_footer,
    render_workspace_band,
)
from ui.preview_section import render_preview_section
from ui.rules_section import render_rules_section
from ui.rulesets_section import render_rulesets_section
from ui.scan_section import render_scan_section
from ui.upload_section import render_upload_section


# --------------------------------------------------------------------------- #
# Page config — must be first.
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="Data Cleaning Workbench",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_resource
def _get_store() -> RuleSetStore:
    return RuleSetStore(DEFAULT_RULESET_DIR)


# --------------------------------------------------------------------------- #
# Shell helpers — derive stage/session state from session_state alone.
# --------------------------------------------------------------------------- #

def _derive_stages() -> list[tuple[str, str]]:
    has_upload = "uploaded_bytes" in st.session_state
    has_scan = st.session_state.get("scan_result") is not None
    rules = st.session_state.get("rules", []) or []
    has_rules = any(r.enabled and not r.validate() for r in rules)
    has_output = bool(st.session_state.get("generated_bytes"))

    return [
        ("Upload workbook",   "done" if has_upload else "active"),
        ("Scan workbook",     "done" if has_scan else ("active" if has_upload else "idle")),
        ("Explore values",    "active" if has_scan else "idle"),
        ("Build rules",       "done" if has_rules and has_output else
                              ("active" if has_scan else "idle")),
        ("Preview output",    "active" if has_scan else "idle"),
        ("Generate output",   "done" if has_output else
                              ("active" if has_rules else "idle")),
    ]


def _session_metrics() -> list[tuple[str, str]]:
    metrics: list[tuple[str, str]] = []

    file_name = st.session_state.get("uploaded_name")
    metrics.append(("File", file_name if file_name else "—"))

    scan = st.session_state.get("scan_result")
    if scan is not None:
        metrics.append(("Sheets", f"{scan.sheet_count}"))
        metrics.append(("Unique values", f"{scan.unique_value_count:,}"))
        metrics.append(("Missing tokens", f"{scan.missing_token_count:,}"))
    else:
        metrics.append(("Sheets", "—"))
        metrics.append(("Unique values", "—"))
        metrics.append(("Missing tokens", "—"))

    rules = st.session_state.get("rules", []) or []
    enabled_valid = sum(1 for r in rules if r.enabled and not r.validate())
    metrics.append(("Active rules", f"{enabled_valid:,}"))

    return metrics


def _band_cells() -> list[tuple[str, str, bool]]:
    file_name: Optional[str] = st.session_state.get("uploaded_name")
    scan = st.session_state.get("scan_result")
    rules = st.session_state.get("rules", []) or []
    active = sum(1 for r in rules if r.enabled and not r.validate())
    output = bool(st.session_state.get("generated_bytes"))

    # Current stage label — first non-done stage.
    stages = _derive_stages()
    current = next((name for name, state in stages if state == "active"), "Ready")

    return [
        ("Workbook",       file_name if file_name else "No file loaded",       file_name is None),
        ("Current stage",  current,                                             False),
        ("Unique values",  f"{scan.unique_value_count:,}" if scan else "—",     scan is None),
        ("Active rules",   f"{active:,}" if rules else "—",                     not rules),
        ("Output",         "Ready" if output else "Not generated",              not output),
    ]


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> None:
    inject_global_chrome()
    store = _get_store()

    render_appbar(active="Workbench")
    render_workspace_band(_band_cells())

    left, main_col = st.columns([1, 3.4], gap="large")

    with left:
        render_control_panel(
            stages=_derive_stages(),
            metrics=_session_metrics(),
            info_lines=[
                "Processing happens entirely on this machine.",
                "Rules match whole cells only. Shorter values never "
                "leak into longer phrases.",
                "Formulas are preserved automatically.",
            ],
        )

    with main_col:
        render_upload_section()
        render_scan_section()
        render_explorer_section()
        render_rules_section()
        render_preview_section()
        render_export_section(store)
        render_rulesets_section(store)

    render_footer()


if __name__ == "__main__":
    main()
