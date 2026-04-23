"""
Data Cleaning Workbench — Streamlit entry point.

Shell layout:

    ┌──────────────── Top application bar ────────────────┐
    │                                                      │
    │  ┌────────────┐  ┌────────────────────────────────┐ │
    │  │ Left panel │  │ — Saved rule sets (load)        │ │
    │  │  Stages    │  │ 1. Upload workbook              │ │
    │  │  Session   │  │ 2. Scan workbook                │ │
    │  │  Notes     │  │ 3. Terminology workbench        │ │
    │  │            │  │ 4. Preview output               │ │
    │  │            │  │ 5. Generate cleaned workbook    │ │
    │  └────────────┘  └────────────────────────────────┘ │
    │                                                      │
    └──────────────────── Footer ──────────────────────────┘

Changes from the previous version
---------------------------------
- Dark workspace band removed. The left panel is the single source of
  session-status. Less color competition with the red app bar, ~60px
  of vertical space freed on every page view.
- Explorer + rules cards merged into one ``Terminology workbench`` card
  (see ``ui/workbench_section.py``). Inline "Replace with" column;
  advanced editor lives behind an expander below.
- Saved rule sets moved to the top of the main column, right after
  Upload. Users who want to load an existing recipe no longer have to
  scroll past everything first.
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

from core.ruleset_store import DEFAULT_RULESET_DIR, RuleSetStore
from ui.export_section import render_export_section
from ui.layout import (
    inject_global_chrome,
    render_appbar,
    render_control_panel,
    render_footer,
    scroll_anchor,
)
from ui.preview_section import render_preview_section
from ui.rulesets_section import render_rulesets_section
from ui.scan_section import render_scan_section
from ui.upload_section import render_upload_section
from ui.workbench_section import render_workbench_section


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
# Shell helpers
# --------------------------------------------------------------------------- #

def _derive_stages() -> list[tuple[str, str]]:
    """Return (label, state) pairs for the left panel workflow list."""
    has_upload = "uploaded_bytes" in st.session_state
    has_scan = st.session_state.get("scan_result") is not None
    rules = st.session_state.get("rules", []) or []
    has_rules = any(r.enabled and not r.validate() for r in rules)
    has_output = bool(st.session_state.get("generated_bytes"))

    return [
        ("Upload workbook",       "done" if has_upload else "active"),
        ("Scan workbook",         "done" if has_scan else ("active" if has_upload else "idle")),
        ("Terminology workbench", "done" if has_rules and has_output else
                                  ("active" if has_scan else "idle")),
        ("Preview output",        "active" if has_scan else "idle"),
        ("Generate output",       "done" if has_output else
                                  ("active" if has_rules else "idle")),
    ]


def _session_metrics() -> list[tuple[str, str]]:
    """Single source of session status, surfaced in the left panel."""
    metrics: list[tuple[str, str]] = []

    file_name = st.session_state.get("uploaded_name")
    metrics.append(("File", file_name if file_name else "—"))

    scan = st.session_state.get("scan_result")
    if scan is not None:
        metrics.append(("Sheets",         f"{scan.sheet_count}"))
        metrics.append(("Unique values",  f"{scan.unique_value_count:,}"))
        metrics.append(("Missing tokens", f"{scan.missing_token_count:,}"))
    else:
        metrics.append(("Sheets",         "—"))
        metrics.append(("Unique values",  "—"))
        metrics.append(("Missing tokens", "—"))

    rules = st.session_state.get("rules", []) or []
    active = sum(1 for r in rules if r.enabled and not r.validate())
    metrics.append(("Active rules", f"{active:,}"))

    # Output status closes the loop so the panel reflects the full
    # workflow, not just the first half.
    output = "Ready" if st.session_state.get("generated_bytes") else "—"
    metrics.append(("Output", output))

    return metrics


def _appbar_status() -> tuple[str, str]:
    """Return (label, kind) for the app bar status indicator.

    kind ∈ {"ok", "warn", "idle"}:
      - idle: no file uploaded yet
      - warn: rules exist but some are invalid (user has work to fix)
      - ok:   everything's healthy for the current stage
    """
    if "uploaded_bytes" not in st.session_state:
        return ("Ready · no file loaded", "idle")

    rules = st.session_state.get("rules", []) or []
    invalid = [r for r in rules if not r.validate() == []]
    if invalid:
        return (f"{len(invalid)} rule{'s' if len(invalid) != 1 else ''} need fixes", "warn")

    if st.session_state.get("generated_bytes"):
        return ("Cleaned workbook ready", "ok")
    if rules:
        active = sum(1 for r in rules if r.enabled)
        return (f"{active} active rule{'s' if active != 1 else ''}", "ok")
    if st.session_state.get("scan_result") is not None:
        return ("Scan complete", "ok")
    return ("Workbook loaded", "ok")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> None:
    inject_global_chrome()
    store = _get_store()

    label, kind = _appbar_status()
    render_appbar(active="Workbench", status_label=label, status_kind=kind)

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
        # Rule sets surface first so users who want to apply an existing
        # recipe don't have to upload → scan → build → scroll to find it.
        scroll_anchor("section-library")
        render_rulesets_section(store)

        render_upload_section()
        render_scan_section()

        scroll_anchor("section-workbench")
        render_workbench_section()

        scroll_anchor("section-preview")
        render_preview_section()

        scroll_anchor("section-export")
        render_export_section(store)

    render_footer()


if __name__ == "__main__":
    main()
