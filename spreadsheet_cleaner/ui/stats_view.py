"""Statistics view for displaying descriptive statistics."""

import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional

from core.stats_engine import (
    generate_workbook_stats,
    generate_column_stats,
    generate_before_after_stats,
    get_missing_token_summary,
)
from core.rules_engine import apply_rules


def render_stats_view(sheets: Dict[str, pd.DataFrame],
                      rules: List[Any] = None,
                      metadata: Dict[str, Any] = None) -> None:
    """
    Render the statistics view.
    
    Args:
        sheets: Original sheet data
        rules: Optional list of cleaning rules
        metadata: Optional workbook metadata
    """
    st.markdown("### Statistics")
    st.markdown(
        "<p style='color: #5f6368; margin-bottom: 24px;'>View descriptive statistics for your data.</p>",
        unsafe_allow_html=True
    )
    
    # Generate stats
    workbook_stats = generate_workbook_stats(sheets)
    column_stats = generate_column_stats(sheets)
    
    # Workbook-level summary
    st.markdown("#### Workbook Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Sheets", workbook_stats["num_sheets"])
    
    with col2:
        st.metric("Total Rows", workbook_stats["total_rows"])
    
    with col3:
        st.metric("Total Columns", workbook_stats["total_columns"])
    
    with col4:
        st.metric("Unique Values", workbook_stats["unique_values"])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Missing Values", workbook_stats["total_missing"])
    
    with col2:
        st.metric("Missing %", f"{workbook_stats['missing_percentage']}%")
    
    st.divider()
    
    # Missing token analysis
    st.markdown("#### Missing Token Analysis")
    missing_summary = get_missing_token_summary(sheets)
    
    if missing_summary["total_missing_variants"] > 0:
        st.warning(f"Found {missing_summary['total_missing_variants']} different missing token variants")
        
        # Show missing tokens table
        missing_rows = []
        for norm_val, info in missing_summary["tokens"].items():
            missing_rows.append({
                "Normalized": norm_val or "(empty)",
                "Variants": ", ".join(info["variants"]),
                "Count": info["total_count"],
                "Example Locations": ", ".join([f"{loc['sheet']}.{loc['column']}" for loc in info["locations"][:3]]),
            })
        
        missing_df = pd.DataFrame(missing_rows)
        st.dataframe(missing_df, use_container_width=True, hide_index=True)
    else:
        st.success("No obvious missing token variants detected.")
    
    st.divider()
    
    # Column statistics
    st.markdown("#### Column Statistics")
    
    # Filter options
    col1, col2 = st.columns(2)
    
    with col1:
        type_filter = st.multiselect(
            "Filter by type",
            options=["numeric", "categorical", "text", "date", "mixed"],
            default=[]
        )
    
    with col2:
        sheet_filter = st.selectbox(
            "Filter by sheet",
            options=["All"] + list(set(s["sheet"] for s in column_stats))
        )
    
    # Apply filters
    filtered_stats = column_stats
    
    if type_filter:
        filtered_stats = [s for s in filtered_stats if s["inferred_type"] in type_filter]
    
    if sheet_filter != "All":
        filtered_stats = [s for s in filtered_stats if s["sheet"] == sheet_filter]
    
    # Display column stats
    for col_stat in filtered_stats[:50]:  # Limit to 50 columns
        _render_column_stat_card(col_stat)
    
    if len(filtered_stats) > 50:
        st.caption(f"Showing 50 of {len(filtered_stats)} columns")
    
    # Before/After comparison if rules exist
    if rules and len(rules) > 0:
        st.divider()
        st.markdown("#### Before/After Cleaning Comparison")
        _render_before_after_comparison(sheets, rules)


def _render_column_stat_card(stat: Dict[str, Any]) -> None:
    """Render a single column statistics card."""
    with st.expander(f"**{stat['sheet']}.{stat['column']}** ({stat['inferred_type']})"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total", stat["total_count"])
        
        with col2:
            st.metric("Missing", stat["missing_count"])
        
        with col3:
            st.metric("Unique", stat["unique_count"])
        
        # Type-specific stats
        if stat.get("numeric_stats"):
            ns = stat["numeric_stats"]
            st.markdown("**Numeric Statistics:**")
            ns_col1, ns_col2 = st.columns(2)
            
            with ns_col1:
                st.write(f"- Mean: {ns.get('mean', 'N/A')}")
                st.write(f"- Median: {ns.get('median', 'N/A')}")
                st.write(f"- Std: {ns.get('std', 'N/A')}")
            
            with ns_col2:
                st.write(f"- Min: {ns.get('min', 'N/A')}")
                st.write(f"- Max: {ns.get('max', 'N/A')}")
                st.write(f"- Q1/Q3: {ns.get('q1', 'N/A')} / {ns.get('q3', 'N/A')}")
        
        if stat.get("categorical_stats"):
            cs = stat["categorical_stats"]
            st.markdown("**Top Values:**")
            
            if cs.get("top_values"):
                top_df = pd.DataFrame(cs["top_values"][:5])
                if not top_df.empty:
                    st.dataframe(top_df, use_container_width=True, hide_index=True)


def _render_before_after_comparison(sheets: Dict[str, pd.DataFrame],
                                     rules: List[Any]) -> None:
    """Render before/after comparison."""
    try:
        # Apply rules
        cleaned_sheets = apply_rules(sheets, rules)
        
        # Generate comparison stats
        before_after = generate_before_after_stats(sheets, cleaned_sheets)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total Changes", before_after["total_changes"])
        
        with col2:
            st.metric("Affected Columns", before_after["affected_columns"])
        
        # Category distribution changes
        if before_after.get("category_changes"):
            st.markdown("##### Category Distribution Changes")
            
            for col_key, changes in list(before_after["category_changes"].items())[:5]:
                with st.expander(f"{col_key}"):
                    st.write(f"**Unique values:** {changes['before_unique']} → {changes['after_unique']} (reduction: {changes['reduction']})")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Before:**")
                        for val, count in list(changes["before_top"].items())[:3]:
                            st.write(f"• {val}: {count}")
                    
                    with col2:
                        st.markdown("**After:**")
                        for val, count in list(changes["after_top"].items())[:3]:
                            st.write(f"• {val}: {count}")
    
    except Exception as e:
        st.error(f"Error generating comparison: {e}")


def get_stats_summary(sheets: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """
    Get a quick statistics summary.
    
    Args:
        sheets: Original data
        
    Returns:
        Summary dict
    """
    workbook_stats = generate_workbook_stats(sheets)
    
    return {
        "sheets": workbook_stats["num_sheets"],
        "rows": workbook_stats["total_rows"],
        "columns": workbook_stats["total_columns"],
        "unique_values": workbook_stats["unique_values"],
        "missing": workbook_stats["total_missing"],
        "missing_pct": workbook_stats["missing_percentage"],
    }
