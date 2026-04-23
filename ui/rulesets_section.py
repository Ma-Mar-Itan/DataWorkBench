"""
Saved rule sets card.

Lists the JSON files under ``rulesets/`` and lets the user load one into
the current workspace or delete it. Loading replaces the current rules;
the user is warned when non-empty state would be overwritten.
"""

from __future__ import annotations

import streamlit as st

from core.ruleset_store import RuleSetStore
from ui.layout import caption, card, chip, html_block


def render_rulesets_section(store: RuleSetStore) -> None:
    """Small utility card for loading/saving/deleting named rule sets.

    We only render the card when there is at least one saved rule set —
    otherwise it's a self-referential empty state sitting at the top of
    the page, taking up ~180px to tell the user something they can already
    see (they have nothing to load).
    """
    names = store.list_names()
    if not names:
        return

    with card(
        step=None,
        eyebrow="Library",
        title="Saved rule sets",
        subtitle=(
            "Reusable cleaning recipes. Loading a set replaces the current "
            "rules in the workspace."
        ),
    ):

        # Summary line.
        html_block(f'<div style="margin-bottom:10px; font-size:12.5px; color:var(--tw-ink-3);">'
            f'{chip(f"{len(names)} saved", "info")} &nbsp;'
            f'<span style="margin-left:8px;">Ready to apply to any workbook.</span></div>')

        # Pick one.
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            picked = st.selectbox("Rule set", names, label_visibility="collapsed")
        with c2:
            load_click = st.button("Load", use_container_width=True)
        with c3:
            delete_click = st.button("Delete", use_container_width=True)

        if load_click and picked:
            existing = st.session_state.get("rules", [])
            try:
                rs = store.load(picked)
            except Exception as e:  # noqa: BLE001
                st.error(f"Could not load rule set: {e}")
                return
            st.session_state["rules"] = list(rs.rules)
            msg = (
                f"Loaded {len(rs.rules)} rule{'s' if len(rs.rules) != 1 else ''} from “{picked}”."
            )
            if existing:
                msg += f" Replaced {len(existing)} existing rule{'s' if len(existing) != 1 else ''}."
            st.success(msg)

        if delete_click and picked:
            try:
                if store.delete(picked):
                    st.success(f"Deleted “{picked}”.")
                    # Streamlit's rerun model will refresh the selectbox next cycle.
                else:
                    st.warning(f"“{picked}” was not found on disk.")
            except Exception as e:  # noqa: BLE001
                st.error(f"Could not delete: {e}")

        # Show a brief description of each rule set on hover/expansion.
        with st.expander("Browse saved sets", expanded=False):
            for name in names:
                try:
                    rs = store.load(name)
                except Exception:  # noqa: BLE001
                    continue
                html_block(f'<div style="padding:8px 10px; border-bottom:1px solid var(--tw-border); '
                    f'display:flex; justify-content:space-between; align-items:baseline;">'
                    f'<div><b style="font-size:13.5px; color:var(--tw-ink);">{name}</b>'
                    f' &nbsp; <span style="font-size:12px; color:var(--tw-ink-3);">{rs.description or "—"}</span>'
                    f'</div>'
                    f'<div style="font-family:var(--tw-font-mono); font-size:12px; color:var(--tw-ink-3);">'
                    f'{len(rs.rules)} rule{"s" if len(rs.rules) != 1 else ""}</div>'
                    f'</div>')
