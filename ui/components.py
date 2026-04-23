"""
Reusable UI building blocks.

Every function here renders a self-contained, stylistically coherent
piece of the interface. The real layout responsibility lives in app.py;
this module is just well-labeled Lego bricks.
"""
from __future__ import annotations

import html
from typing import Iterable

import streamlit as st


# --------------------------------------------------------------------- #
# Top bar
# --------------------------------------------------------------------- #
def render_topbar(
    product_name: str,
    tag: str,
    scan_state: str,
    rows_scanned: int | None,
) -> str:
    """
    Render the horizontal app bar. Returns the current search query.

    scan_state: "idle" | "running" | "done"
    """
    state_label = {
        "idle":    "No scan yet",
        "running": "Scanning workbook…",
        "done":    f"Last scan · {rows_scanned:,} rows" if rows_scanned else "Scan complete",
    }[scan_state]
    state_cls = {"idle": "", "running": "run", "done": "ok"}[scan_state]

    # Left brand / middle search / right status + actions
    st.markdown(
        f"""
        <div class="topbar">
          <div class="topbar-brand">
            <div class="logo">Sc</div>
            <div style="display:flex;flex-direction:column;line-height:1.15">
              <span class="name">{html.escape(product_name)}</span>
              <span class="tag">{html.escape(tag)}</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # The brand is full-width because Streamlit columns can't sit inside
    # a raw-HTML flex container. Render search + actions in a column row
    # that *visually* sits just under the brand row but reads as one bar.
    c_search, c_status, c_actions = st.columns([7, 2.2, 2.2])

    with c_search:
        st.markdown('<div class="searchbar-wrap visually-hidden-label">', unsafe_allow_html=True)
        query = st.text_input(
            "search",
            value=st.session_state.get("global_search", ""),
            placeholder="Search values, columns, or sheets",
            label_visibility="collapsed",
            key="global_search_input",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with c_status:
        st.markdown(
            f'<div style="display:flex;justify-content:center;">'
            f'<span class="scan-indicator {state_cls}"><span class="dot"></span>{html.escape(state_label)}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )

    with c_actions:
        a1, a2 = st.columns(2)
        with a1:
            st.button("Rescan", use_container_width=True, key="tb_rescan")
        with a2:
            st.button("Help", use_container_width=True, key="tb_help")

    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    return query


# --------------------------------------------------------------------- #
# Nav rail
# --------------------------------------------------------------------- #
NAV_ITEMS = [
    ("upload",  "Upload"),
    ("scan",    "Scan Results"),
    ("rules",   "Cleaning Rules"),
    ("preview", "Preview"),
    ("stats",   "Statistics"),
    ("export",  "Export"),
]


def render_navrail() -> str:
    """Render the left rail and return the selected view id."""
    current = st.session_state.get("view", "upload")
    labels = [label for _, label in NAV_ITEMS]
    ids    = [vid   for vid, _   in NAV_ITEMS]

    st.markdown('<div class="navrail">', unsafe_allow_html=True)
    st.markdown('<div class="navrail-heading">Workspace</div>', unsafe_allow_html=True)

    idx = ids.index(current) if current in ids else 0
    chosen_label = st.radio(
        "navigation",
        labels,
        index=idx,
        label_visibility="collapsed",
        key="nav_radio",
    )
    chosen_id = ids[labels.index(chosen_label)]

    st.markdown(
        '<div style="height:12px"></div>'
        '<div class="navrail-heading">Workbook</div>',
        unsafe_allow_html=True,
    )

    wb = st.session_state.get("workbook_meta")
    if wb:
        st.markdown(
            f"""
            <div style="padding: 4px 10px; font-size:12.5px; color:var(--text-muted);">
              <div style="font-weight:600;color:var(--text);margin-bottom:2px;">{html.escape(wb['filename'])}</div>
              <div>{wb['sheet_count']} sheets · {wb['row_count']:,} rows</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="padding: 4px 10px; font-size:12.5px; color:var(--text-faint);">'
            "No workbook loaded</div>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)
    st.session_state.view = chosen_id
    return chosen_id


# --------------------------------------------------------------------- #
# Page header
# --------------------------------------------------------------------- #
def page_header(eyebrow: str, title: str, subtitle: str, actions_html: str = "") -> None:
    st.markdown(
        f"""
        <div class="toolbar-row">
          <div class="title-block">
            <div class="section-eyebrow">{html.escape(eyebrow)}</div>
            <div class="page-title">{html.escape(title)}</div>
            <div class="page-sub">{html.escape(subtitle)}</div>
          </div>
          <div class="actions">{actions_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------- #
# Panels
# --------------------------------------------------------------------- #
def panel_open(title: str | None = None, subtitle: str | None = None, soft: bool = False) -> None:
    cls = "panel-soft" if soft else "panel"
    st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
    if title:
        st.markdown(f'<div class="panel-title">{html.escape(title)}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="panel-subtitle">{html.escape(subtitle)}</div>', unsafe_allow_html=True)


def panel_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


# --------------------------------------------------------------------- #
# Stat cards
# --------------------------------------------------------------------- #
def stat_cards(cards: list[dict]) -> None:
    """
    Render a responsive grid of stat cards.

    Each card dict: { "label": str, "value": str|int, "delta": str?, "delta_kind": "pos"|"neg"|"" }
    """
    items = []
    for c in cards:
        delta_html = ""
        if c.get("delta"):
            kind = c.get("delta_kind", "")
            delta_html = f'<div class="delta {kind}">{html.escape(c["delta"])}</div>'
        items.append(
            f"""
            <div class="stat-card">
              <div class="label">{html.escape(c["label"])}</div>
              <div class="value">{html.escape(str(c["value"]))}</div>
              {delta_html}
            </div>
            """
        )
    st.markdown('<div class="stat-grid">' + "".join(items) + "</div>", unsafe_allow_html=True)


# --------------------------------------------------------------------- #
# Badges
# --------------------------------------------------------------------- #
def chip(text: str, kind: str = "") -> str:
    return f'<span class="chip {kind}">{html.escape(text)}</span>'


def count_badge(n: int) -> str:
    return f'<span class="count-badge">{n}</span>'


# --------------------------------------------------------------------- #
# Key/value list
# --------------------------------------------------------------------- #
def kv_list(pairs: Iterable[tuple[str, str]]) -> None:
    rows = "".join(
        f"<dt>{html.escape(str(k))}</dt><dd>{html.escape(str(v))}</dd>" for k, v in pairs
    )
    st.markdown(f'<dl class="kv">{rows}</dl>', unsafe_allow_html=True)


# --------------------------------------------------------------------- #
# Inline progress bar
# --------------------------------------------------------------------- #
def progress_bar(pct: float, kind: str = "") -> str:
    pct = max(0.0, min(100.0, pct))
    return f'<div class="bar {kind}"><span style="width:{pct:.1f}%"></span></div>'
