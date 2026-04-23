"""
Layout primitives: appbar, dark band, cards, metrics, left panel, chips.

Markup-only helpers. No business logic.
"""

from __future__ import annotations

from contextlib import contextmanager
from html import escape
from pathlib import Path
from typing import Iterable, Optional

import streamlit as st

from models.schemas import ValueClass


_CSS_PATH = Path(__file__).parent / "theme" / "styles.css"


# --------------------------------------------------------------------------- #
# Bootstrap
# --------------------------------------------------------------------------- #

def inject_global_chrome() -> None:
    """Inject fonts + design-system stylesheet."""
    css = _CSS_PATH.read_text(encoding="utf-8")
    st.markdown(
        f"""
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Source+Serif+4:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
        <style>{css}</style>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# App bar
# --------------------------------------------------------------------------- #

def render_appbar(*, active: str = "Workbench", status_label: str = "Local session") -> None:
    nav_items = ["Workbench", "Rule Sets", "Preview", "Export"]
    nav_html = "".join(
        f'<a class="{"is-active" if item == active else ""}">{item}</a>'
        for item in nav_items
    )
    st.markdown(
        f"""
        <div class="tw-appbar">
          <div class="tw-appbar__brand">
            <span class="tw-appbar__mark">DC</span>
            <div>
              <div class="tw-appbar__title">Data Cleaning Workbench</div>
              <div class="tw-appbar__subtitle">Value standardization · Recoding · Excel</div>
            </div>
          </div>
          <nav class="tw-appbar__nav">{nav_html}</nav>
          <div class="tw-appbar__status">
            <span><span class="tw-dot"></span>{escape(status_label)}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Dark band
# --------------------------------------------------------------------------- #

def render_workspace_band(cells: Iterable[tuple[str, str, bool]]) -> None:
    cell_html = "".join(
        f'''
        <div class="tw-band__cell">
          <div class="tw-band__label">{escape(label)}</div>
          <div class="tw-band__value {"tw-band__value--muted" if muted else ""}">{escape(value)}</div>
        </div>
        '''
        for label, value, muted in cells
    )
    st.markdown(f'<div class="tw-band">{cell_html}</div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Card
# --------------------------------------------------------------------------- #

@contextmanager
def card(
    *,
    step: Optional[int] = None,
    step_state: str = "idle",
    eyebrow: Optional[str] = None,
    title: str = "",
    subtitle: Optional[str] = None,
):
    step_class = {"active": "tw-card__step--active", "done": "tw-card__step--done"}.get(step_state, "")
    step_html = f'<span class="tw-card__step {step_class}">{step}</span>' if step is not None else ""
    eyebrow_html = f'<div class="tw-card__eyebrow">{escape(eyebrow)}</div>' if eyebrow else ""
    sub_html = f'<div class="tw-card__sub">{escape(subtitle)}</div>' if subtitle else ""

    st.markdown(
        f"""
        <div class="tw-card">
          <div class="tw-card__head">
            <div class="tw-card__title-group">
              {step_html}
              <div style="min-width:0;">
                {eyebrow_html}
                <h2 class="tw-card__title">{escape(title)}</h2>
                {sub_html}
              </div>
            </div>
          </div>
        """,
        unsafe_allow_html=True,
    )
    try:
        yield
    finally:
        st.markdown("</div>", unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #

def render_metrics(
    metrics: list[tuple[str, str, Optional[str]]],
    *,
    accent_index: Optional[int] = None,
) -> None:
    tiles: list[str] = []
    for i, (label, value, hint) in enumerate(metrics):
        cls = "tw-metric"
        if accent_index is not None and i == accent_index:
            cls += " tw-metric--accent"
        hint_html = f'<div class="tw-metric__hint">{escape(hint)}</div>' if hint else ""
        tiles.append(
            f'''
            <div class="{cls}">
              <div class="tw-metric__label">{escape(label)}</div>
              <div class="tw-metric__value">{escape(value)}</div>
              {hint_html}
            </div>
            '''
        )
    st.markdown(f'<div class="tw-metrics">{"".join(tiles)}</div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Left panel
# --------------------------------------------------------------------------- #

def render_control_panel(
    *,
    stages: list[tuple[str, str]],
    metrics: list[tuple[str, str]],
    info_lines: Optional[list[str]] = None,
) -> None:
    stage_html = "".join(
        f'''
        <div class="tw-panel__stage {
            {"active":"tw-panel__stage--active","done":"tw-panel__stage--done","idle":""}.get(state,"")
        }">
          <span class="tw-panel__stage-dot"></span>
          <span>{escape(label)}</span>
        </div>
        '''
        for label, state in stages
    )
    stat_rows = "".join(
        f'<div class="tw-panel__stat"><span class="tw-panel__stat-label">{escape(l)}</span>'
        f'<span class="tw-panel__stat-value">{escape(v)}</span></div>'
        for l, v in metrics
    )
    info_html = ""
    if info_lines:
        info_html = (
            '<div class="tw-panel__section">'
            '<div class="tw-panel__heading">Notes</div>'
            + "".join(f'<div class="tw-caption">{escape(s)}</div>' for s in info_lines)
            + "</div>"
        )
    st.markdown(
        f"""
        <aside class="tw-panel">
          <div class="tw-panel__section">
            <div class="tw-panel__heading">Workflow</div>
            {stage_html}
          </div>
          <div class="tw-panel__section">
            <div class="tw-panel__heading">Session</div>
            {stat_rows}
          </div>
          {info_html}
        </aside>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Small utilities
# --------------------------------------------------------------------------- #

def chip(text: str, kind: str = "default") -> str:
    kind_cls = {
        "ok": "tw-chip--ok",
        "warn": "tw-chip--warn",
        "accent": "tw-chip--accent",
        "info": "tw-chip--info",
    }.get(kind, "")
    return f'<span class="tw-chip {kind_cls}">{escape(text)}</span>'


_VALUE_CLASS_LABELS = {
    ValueClass.TEXT_CATEGORY: ("category",   "tw-class--cat"),
    ValueClass.NUMERIC_LIKE:  ("numeric",    "tw-class--num"),
    ValueClass.MIXED_ALNUM:   ("alnum code", "tw-class--mixed"),
    ValueClass.MISSING_TOKEN: ("missing",    "tw-class--missing"),
    ValueClass.HEADER_LABEL:  ("header",     "tw-class--header"),
    ValueClass.DATE_LIKE:     ("date",       "tw-class--date"),
    ValueClass.FREE_TEXT:     ("free text",  "tw-class--free"),
    ValueClass.LOW_FREQUENCY: ("low freq",   "tw-class--low"),
    ValueClass.OTHER:         ("other",      "tw-class--free"),
}


def value_class_badge(vc: ValueClass) -> str:
    """Return a colored inline badge for a value class."""
    label, cls = _VALUE_CLASS_LABELS.get(vc, ("other", "tw-class--free"))
    return f'<span class="tw-class {cls}">{escape(label)}</span>'


def caption(text: str) -> None:
    st.markdown(f'<div class="tw-caption">{escape(text)}</div>', unsafe_allow_html=True)


def rule() -> None:
    st.markdown('<hr class="tw-rule"/>', unsafe_allow_html=True)


def render_footer() -> None:
    st.markdown(
        '''
        <div class="tw-footer">
          <span>Local processing · no data leaves this machine.</span>
          <span>Data Cleaning Workbench · v1</span>
        </div>
        ''',
        unsafe_allow_html=True,
    )
