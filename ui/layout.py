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
import streamlit.components.v1 as components

from models.schemas import ValueClass


_CSS_PATH = Path(__file__).parent / "theme" / "styles.css"


# --------------------------------------------------------------------------- #
# Bootstrap
# --------------------------------------------------------------------------- #

def inject_global_chrome() -> None:
    """Inject fonts + design-system stylesheet into the Streamlit page.

    Implementation note: Streamlit's ``st.markdown(..., unsafe_allow_html=True)``
    runs through an HTML sanitizer that can silently strip or partially render
    ``<style>`` blocks containing comment blocks, non-ASCII characters, or
    certain CSS patterns. That sanitizer is what caused the stylesheet to
    appear as literal page text in earlier builds.

    Two-layer fix:
      1. Write the ``<link>`` + ``<style>`` via ``st.html``, which escapes the
         markdown pipeline entirely and hands raw HTML to the Streamlit frame.
      2. Defensively strip the leading banner comment from the CSS before
         injection — a belt-and-braces measure against any future sanitizer
         heuristic that trips on ``/* ... */`` at the very start of a block.
    """
    css = _CSS_PATH.read_text(encoding="utf-8")

    # Strip the top banner comment if present. The regex is anchored to the
    # start of file to avoid touching anything else.
    import re as _re
    css = _re.sub(r"^\s*/\*.*?\*/\s*", "", css, count=1, flags=_re.DOTALL)

    html_payload = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?'
        'family=Inter:wght@400;500;600;700&'
        'family=Source+Serif+4:wght@500;600;700&'
        'family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">'
        f'<style>{css}</style>'
    )

    # Prefer st.html (Streamlit ≥1.33) which bypasses the markdown sanitizer.
    # Fall back to st.markdown for older versions.
    if hasattr(st, "html"):
        st.html(html_payload)
    else:
        st.markdown(html_payload, unsafe_allow_html=True)


def html_block(markup: str) -> None:
    """Central HTML emitter for UI chrome.

    Streamlit's ``st.markdown(..., unsafe_allow_html=True)`` pipes the payload
    through a markdown renderer plus an HTML sanitizer. Certain shapes of
    input — multiline HTML with indentation, specific tag nesting, or
    ``<style>``/``<link>`` elements — can make the sanitizer escape the whole
    block as text. That was the cause of the "CSS showing as page text" bug.

    ``st.html`` (Streamlit ≥1.33) renders raw HTML through DOMPurify — more
    permissive than the markdown sanitizer and *not* iframed, so global
    styles inject into the main document. This helper prefers it and falls
    back to ``st.markdown`` on older versions so the module still imports.
    """
    if hasattr(st, "html"):
        st.html(markup)
    else:
        st.markdown(markup, unsafe_allow_html=True)


# Internal alias — lots of code in this module uses the short name.
_html = html_block


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
    _html(f'<div class="tw-band">{cell_html}</div>')


# --------------------------------------------------------------------------- #
# Card
#
# IMPORTANT: Streamlit cannot reliably wrap widgets inside a single <div>
# spanning multiple st.markdown calls — the framework splits each markdown
# into its own DOM container and sanitizes any unclosed tags, which ends up
# rendering `<div class="tw-card">` as literal text on the page. We
# therefore build each card as a COMPLETE, self-closed HTML block (header,
# eyebrow, title, subtitle, body border) in one markdown call, and let
# widgets flow on the page background immediately beneath it. Visually the
# result is a header-with-rule-under-it followed by its controls — the
# header's border-bottom plus the spacing below serves as the card's
# "frame" without needing an HTML wrapper around the widgets.
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
    """Open a card: emits a self-contained header block; widgets follow below.

    Usage is unchanged for callers::

        with card(step=1, title="Upload", subtitle="…"):
            st.file_uploader(...)

    On enter we emit one st.markdown with the complete header HTML. On
    exit we emit a small trailing spacer + horizontal rule so consecutive
    cards read as distinct modules. No opened HTML tags cross markdown
    boundaries, so nothing gets escaped to text.
    """
    step_class = {"active": "tw-card__step--active", "done": "tw-card__step--done"}.get(step_state, "")
    step_html = (
        f'<span class="tw-card__step {step_class}">{step}</span>'
        if step is not None
        else ""
    )
    eyebrow_html = f'<div class="tw-card__eyebrow">{escape(eyebrow)}</div>' if eyebrow else ""
    sub_html = f'<div class="tw-card__sub">{escape(subtitle)}</div>' if subtitle else ""

    # Self-contained header with an explicit bottom rule. The surrounding
    # `.tw-card-shell` class gives this card the outer frame styling
    # (white background, border, shadow, padding). Because we cannot wrap
    # the widgets with HTML, we simulate the card body by giving the next
    # Streamlit column a matching background via the `.tw-card-body`
    # spacer div emitted on exit.
    header_html = (
        '<div class="tw-card-head-block">'
        f'  <div class="tw-card__title-group">'
        f'    {step_html}'
        f'    <div style="min-width:0;">'
        f'      {eyebrow_html}'
        f'      <h2 class="tw-card__title">{escape(title)}</h2>'
        f'      {sub_html}'
        f'    </div>'
        f'  </div>'
        '</div>'
    )
    _html(header_html)
    try:
        yield
    finally:
        # Trailing spacer separates cards. Self-contained; never unclosed.
        _html('<div class="tw-card-foot"></div>')


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
    _html(f'<div class="tw-metrics">{"".join(tiles)}</div>')


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
    _html(f'<div class="tw-caption">{escape(text)}</div>')


def rule() -> None:
    _html('<hr class="tw-rule"/>')


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
