"""Cleaning rules view for creating and managing cleaning rules."""

import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from models.schemas import Rule
from models.enums import MatchMode, ScopeType, ActionType


def render_rules_view(value_index: Dict[str, Any],
                      metadata: Dict[str, Any],
                      rules: List[Rule]) -> List[Rule]:
    """
    Render the cleaning rules view.
    
    Args:
        value_index: Dict of normalized_value -> ValueFrequency
        metadata: Workbook metadata
        rules: Current list of rules
        
    Returns:
        Updated list of rules
    """
    st.markdown("### Cleaning Rules")
    st.markdown(
        "<p style='color: #5f6368; margin-bottom: 24px;'>Create rules to clean and standardize your data.</p>",
        unsafe_allow_html=True
    )
    
    # Two-column layout: rule creator on left, rules list on right
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### Create New Rule")
        new_rule = _render_rule_creator(value_index, metadata)
        
        if new_rule:
            rules.append(new_rule)
            st.success("✓ Rule added!")
    
    with col2:
        st.markdown(f"#### Active Rules ({len(rules)})")
        
        if not rules:
            st.info("No rules created yet.")
        else:
            rules = _render_rules_list(rules, metadata)
    
    st.divider()
    
    # Ruleset management
    st.markdown("#### Ruleset Management")
    _render_ruleset_management(rules)
    
    return rules


def _render_rule_creator(value_index: Dict[str, Any],
                         metadata: Dict[str, Any]) -> Optional[Rule]:
    """Render the rule creation form."""
    with st.form("rule_creator", clear_on_submit=True):
        # Source value selection
        source_options = [""] + [freq.raw_value for freq in sorted(value_index.values(), key=lambda x: -x.total_count)[:100]]
        source_value = st.selectbox(
            "Value to replace",
            options=source_options,
            help="Select a value from your data to replace"
        )
        
        # Target value
        target_value = st.text_input(
            "Replacement value",
            help="Enter the value to replace with (leave blank to set empty)"
        )
        
        # Action type
        action_type = st.radio(
            "Action",
            options=[ActionType.REPLACE.value, ActionType.SET_BLANK.value],
            format_func=lambda x: "Replace with..." if x == ActionType.REPLACE.value else "Set to blank"
        )
        
        # Scope type
        scope_type = st.selectbox(
            "Apply to",
            options=[ScopeType.WORKBOOK.value, ScopeType.SHEET.value, ScopeType.COLUMN.value],
            format_func=lambda x: {
                ScopeType.WORKBOOK.value: "Entire Workbook",
                ScopeType.SHEET.value: "Specific Sheet",
                ScopeType.COLUMN.value: "Specific Column",
            }.get(x, x)
        )
        
        # Scope details based on type
        scope_sheet = None
        scope_column = None
        
        if scope_type == ScopeType.SHEET.value:
            scope_sheet = st.selectbox(
                "Select sheet",
                options=metadata.get("sheet_names", [])
            )
        elif scope_type == ScopeType.COLUMN.value:
            scope_sheet = st.selectbox(
                "Select sheet",
                options=metadata.get("sheet_names", []),
                key="col_scope_sheet"
            )
            if scope_sheet:
                # Get columns for selected sheet - would need sheets data
                scope_column = st.text_input(
                    "Enter column name",
                    help="Enter the exact column name"
                )
        
        # Match mode
        match_mode = st.radio(
            "Match mode",
            options=[MatchMode.EXACT_NORMALIZED.value, MatchMode.EXACT_RAW.value],
            format_func=lambda x: {
                MatchMode.EXACT_NORMALIZED.value: "Exact (normalized) - case-insensitive for Latin",
                MatchMode.EXACT_RAW.value: "Exact (raw) - case-sensitive",
            }.get(x, x),
            help="Normalized matching is recommended for most cases"
        )
        
        submitted = st.form_submit_button("Add Rule", use_container_width=True)
        
        if submitted and source_value:
            return Rule(
                rule_id=str(uuid.uuid4())[:8],
                source_value=source_value,
                target_value=target_value if action_type == ActionType.REPLACE.value else "",
                action_type=action_type,
                match_mode=match_mode,
                scope_type=scope_type,
                scope_sheet=scope_sheet,
                scope_column=scope_column,
                enabled=True,
            )
        elif submitted and not source_value:
            st.error("Please select a value to replace")
    
    return None


def _render_rules_list(rules: List[Rule], 
                       metadata: Dict[str, Any]) -> List[Rule]:
    """Render the list of existing rules."""
    updated_rules = []
    
    for idx, rule in enumerate(rules):
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1, 1])
            
            with col1:
                st.markdown(f"**{rule.source_value}** → **{rule.target_value or '(blank)'}**")
            
            with col2:
                scope_display = {
                    ScopeType.WORKBOOK.value: "📚 Workbook",
                    ScopeType.SHEET.value: f"📄 {rule.scope_sheet or 'All'}",
                    ScopeType.COLUMN.value: f"📑 {rule.scope_sheet}.{rule.scope_column or 'All'}",
                }
                st.text(scope_display.get(rule.scope_type, rule.scope_type))
            
            with col3:
                match_display = {
                    MatchMode.EXACT_RAW.value: "exact",
                    MatchMode.EXACT_NORMALIZED.value: "normalized",
                }
                st.text(match_display.get(rule.match_mode, rule.match_mode))
            
            with col4:
                enabled = st.checkbox(
                    "Enabled",
                    value=rule.enabled,
                    key=f"rule_enabled_{idx}"
                )
                rule.enabled = enabled
            
            with col5:
                if st.button("✕", key=f"rule_delete_{idx}"):
                    pass  # Will be filtered out
                else:
                    updated_rules.append(rule)
            
            st.divider()
    
    return updated_rules


def _render_ruleset_management(rules: List[Rule]) -> None:
    """Render ruleset save/load controls."""
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        ruleset_name = st.text_input("Ruleset name", placeholder="My cleaning rules")
    
    with col2:
        if st.button("💾 Save Ruleset", use_container_width=True):
            if ruleset_name:
                _save_ruleset(rules, ruleset_name)
            else:
                st.error("Please enter a ruleset name")
    
    with col3:
        if st.button("📂 Load Ruleset", use_container_width=True):
            st.session_state.show_load_dialog = True
    
    # Load dialog
    if st.session_state.get("show_load_dialog", False):
        _render_load_dialog()


def _save_ruleset(rules: List[Rule], name: str) -> None:
    """Save ruleset to file."""
    from core.ruleset_store import save_ruleset
    
    try:
        filepath = save_ruleset(rules, name)
        st.success(f"Ruleset saved to {filepath}")
    except Exception as e:
        st.error(f"Failed to save ruleset: {e}")


def _render_load_dialog() -> None:
    """Render the ruleset load dialog."""
    from core.ruleset_store import list_rulesets, load_ruleset_from_store
    
    st.markdown("#### Load Existing Ruleset")
    
    rulesets = list_rulesets()
    
    if not rulesets:
        st.info("No saved rulesets found.")
        if st.button("Close"):
            st.session_state.show_load_dialog = False
            st.rerun()
        return
    
    ruleset_options = {
        f"{r['name']} ({r['rules_count']} rules)": r['filepath']
        for r in rulesets
    }
    
    selected = st.selectbox("Select ruleset", options=list(ruleset_options.keys()))
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Load", use_container_width=True):
            filepath = ruleset_options[selected]
            loaded_rules = load_ruleset_from_store(filepath)
            st.session_state.rules = loaded_rules
            st.session_state.show_load_dialog = False
            st.success(f"Loaded {len(loaded_rules)} rules!")
            st.rerun()
    
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.session_state.show_load_dialog = False
            st.rerun()


def render_quick_add_buttons(value_index: Dict[str, Any]) -> Optional[Rule]:
    """
    Render quick-add buttons for common cleaning tasks.
    
    Args:
        value_index: The value index
        
    Returns:
        New rule if created
    """
    st.markdown("#### Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    missing_values = [v for v in value_index.values() if v.is_likely_missing]
    
    with col1:
        if st.button("Standardize Missing Values", use_container_width=True):
            # Create rules to standardize all missing variants to empty
            rules = []
            for freq in missing_values[:10]:  # Limit to 10
                rules.append(Rule(
                    rule_id=str(uuid.uuid4())[:8],
                    source_value=freq.raw_value,
                    target_value="",
                    action_type=ActionType.SET_BLANK.value,
                    match_mode=MatchMode.EXACT_NORMALIZED.value,
                    scope_type=ScopeType.WORKBOOK.value,
                    enabled=True,
                ))
            st.session_state.quick_add_rules = rules
            return rules
    
    with col2:
        if st.button("Show High-Frequency Values", use_container_width=True):
            st.session_state.show_high_freq = True
    
    with col3:
        if st.button("Clear All Rules", use_container_width=True):
            st.session_state.rules = []
            st.rerun()
    
    return None
