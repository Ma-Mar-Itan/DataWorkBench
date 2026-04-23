"""
Export card.

Final action panel. Applies the active rules through ``core.exporter`` and
exposes a download button. Also offers an opt-in Save-as-rule-set control
that writes the current (enabled & valid) rules to a named JSON file under
``rulesets/``.
"""

from __future__ import annotations

import streamlit as st

from core.exporter import apply_rules, suggest_output_filename
from core.ruleset_store import RuleSetStore
from models.schemas import CleaningRule, RuleSet
from ui.layout import card, caption, chip, render_metrics, rule as divider


def _step_state() -> str:
    if st.session_state.get("generated_bytes"):
        return "done"
    if st.session_state.get("scan_result") is not None and st.session_state.get("rules"):
        return "active"
    return "idle"


def _valid_enabled_rules() -> list[CleaningRule]:
    """Return the subset of rules that will actually do something on export."""
    return [
        r for r in st.session_state.get("rules", [])
        if r.enabled and not r.validate()
    ]


def render_export_section(store: RuleSetStore) -> None:
    """Render the export card. Requires a scan and at least one valid rule."""
    with card(
        step=6,
        step_state=_step_state(),
        eyebrow="Output",
        title="Generate cleaned workbook",
        subtitle=(
            "Apply active rules workbook-wide using whole-cell matching. "
            "Formulas are preserved, workbook structure is kept intact, and "
            "the output is produced entirely in memory — nothing is written "
            "to disk unless you save a rule set."
        ),
    ):
        if "uploaded_bytes" not in st.session_state or st.session_state.get("scan_result") is None:
            caption("Complete the workbook scan and define at least one rule to enable export.")
            return

        all_rules = st.session_state.get("rules", [])
        applicable = _valid_enabled_rules()

        # Readiness strip.
        render_metrics(
            [
                ("Rules total",       f"{len(all_rules):,}",       "in workspace"),
                ("Rules applicable",  f"{len(applicable):,}",      "enabled & valid"),
                ("Rules disabled",    f"{sum(1 for r in all_rules if not r.enabled):,}", "won't apply"),
                ("Formulas",          "preserved",                 "never replaced"),
            ],
            accent_index=1,
        )

        divider()

        # Action row.
        c1, c2 = st.columns([3, 2])
        with c1:
            generate = st.button(
                "Generate cleaned workbook",
                type="primary",
                use_container_width=True,
                disabled=len(applicable) == 0,
            )
            if not applicable:
                caption("No applicable rules. Add at least one enabled and valid rule to export.")
        with c2:
            save_set = st.checkbox(
                "Also save as rule set",
                value=False,
                help="Persist the current applicable rules to rulesets/<name>.json "
                     "for reuse on future workbooks.",
            )
            set_name = ""
            set_desc = ""
            if save_set:
                set_name = st.text_input(
                    "Rule-set name",
                    placeholder="e.g. Survey 2024 standard recoding",
                )
                set_desc = st.text_input(
                    "Description (optional)",
                    placeholder="e.g. Gender, yes/no, and missing-value recoding.",
                )

        if generate:
            with st.spinner("Applying rules…"):
                try:
                    result = apply_rules(st.session_state["uploaded_bytes"], applicable)
                except Exception as e:  # noqa: BLE001
                    st.error(f"Export failed: {e}")
                    return

            st.session_state["generated_bytes"] = result.output_bytes
            st.session_state["generated_filename"] = suggest_output_filename(
                st.session_state.get("uploaded_name")
            )
            st.session_state["export_summary"] = {
                "cells_visited": result.cells_visited,
                "cells_replaced": result.cells_replaced,
                "cells_blanked": result.cells_blanked,
                "cells_skipped_formula": result.cells_skipped_formula,
                "sheet_count": result.sheet_count,
                "per_rule_counts": dict(result.per_rule_counts),
            }

            # Optional rule-set save.
            if save_set:
                name = (set_name or "").strip()
                if not name:
                    st.warning("A rule-set name is required to save.")
                else:
                    try:
                        ruleset = RuleSet(
                            name=name,
                            description=(set_desc or "").strip(),
                            rules=applicable,
                        )
                        path = store.save(ruleset)
                        st.success(f"Saved rule set to {path}.")
                    except Exception as e:  # noqa: BLE001
                        st.error(f"Could not save rule set: {e}")

        # Replacement summary + download.
        summary = st.session_state.get("export_summary")
        output_bytes = st.session_state.get("generated_bytes")
        filename = st.session_state.get("generated_filename")

        if summary and output_bytes:
            divider()
            total_changed = summary["cells_replaced"] + summary["cells_blanked"]
            st.markdown(
                f'<div style="margin-bottom:14px;">'
                f'{chip("Workbook generated", "ok")} '
                f'<span style="margin-left:10px; font-size:12.5px; color:var(--tw-ink-3);">'
                f'{total_changed:,} cell{"s" if total_changed != 1 else ""} changed '
                f'across {summary["sheet_count"]} sheet{"s" if summary["sheet_count"] != 1 else ""}.'
                f'</span></div>',
                unsafe_allow_html=True,
            )

            render_metrics(
                [
                    ("Cells replaced",   f"{summary['cells_replaced']:,}", "source → target"),
                    ("Cells blanked",    f"{summary['cells_blanked']:,}",  "set empty"),
                    ("Formulas skipped", f"{summary['cells_skipped_formula']:,}", "preserved"),
                    ("Sheets written",   f"{summary['sheet_count']:,}", "full workbook"),
                ],
            )

            # Per-rule breakdown (only when rules actually did something).
            per_rule = summary.get("per_rule_counts", {})
            if per_rule:
                with st.expander(f"Per-rule breakdown ({len(per_rule)} rules used)", expanded=False):
                    # Map rule_id back to source_value for readability.
                    rules_by_id = {r.rule_id: r for r in _valid_enabled_rules()}
                    rows = []
                    for rid, count in sorted(per_rule.items(), key=lambda kv: -kv[1]):
                        r = rules_by_id.get(rid)
                        if r is None:
                            continue
                        rows.append(
                            f'<tr>'
                            f'<td style="padding:3px 10px 3px 0; font-family:var(--tw-font-mono); '
                            f'font-size:12.5px; color:var(--tw-ink);">{r.source_value}</td>'
                            f'<td style="padding:3px 10px; font-family:var(--tw-font-mono); '
                            f'font-size:12.5px; color:var(--tw-ink-3);">→</td>'
                            f'<td style="padding:3px 10px 3px 0; font-family:var(--tw-font-mono); '
                            f'font-size:12.5px; color:var(--tw-accent); font-weight:600;">'
                            f'{"(blank)" if r.action_type.value == "set_blank" else r.target_value}</td>'
                            f'<td style="padding:3px 0; text-align:right; font-family:var(--tw-font-mono); '
                            f'font-size:12.5px; color:var(--tw-ink-3);">{count:,}</td>'
                            f'</tr>'
                        )
                    st.markdown(
                        f'<table style="width:100%; border-collapse:collapse;">{"".join(rows)}</table>',
                        unsafe_allow_html=True,
                    )

            st.markdown('<div style="height:14px;"></div>', unsafe_allow_html=True)
            st.download_button(
                label=f"Download {filename}",
                data=output_bytes,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True,
            )
