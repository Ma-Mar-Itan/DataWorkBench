"""Scan results view for displaying scanned workbook data."""

import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional

from core.scanner import (
    search_values,
    get_repeated_values,
    get_missing_candidates,
    filter_values_by_sheet,
)


def render_scan_view(value_index: Dict[str, Any], 
                     metadata: Dict[str, Any],
                     sheets: Dict[str, pd.DataFrame]) -> None:
    """
    Render the scan results view.
    
    Args:
        value_index: Dict of normalized_value -> ValueFrequency
        metadata: Workbook metadata
        sheets: Original sheet data
    """
    st.markdown("### Scan Results")
    st.markdown(
        "<p style='color: #5f6368; margin-bottom: 24px;'>Review unique values found in your workbook.</p>",
        unsafe_allow_html=True
    )
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Sheets", metadata.get("num_sheets", 0))
    
    with col2:
        total_rows = sum(metadata.get("rows_per_sheet", {}).values())
        st.metric("Total Rows", total_rows)
    
    with col3:
        total_cols = sum(metadata.get("columns_per_sheet", {}).values())
        st.metric("Total Columns", total_cols)
    
    with col4:
        st.metric("Unique Values", len(value_index))
    
    st.divider()
    
    # Filters and search
    st.markdown("#### Filter & Search")
    
    col1, col2, col3 = st.columns([3, 2, 2])
    
    with col1:
        search_query = st.text_input(
            "Search values",
            placeholder="Type to search...",
            key="search_query"
        )
    
    with col2:
        sheet_filter = st.selectbox(
            "Filter by sheet",
            options=["All Sheets"] + list(metadata.get("sheet_names", [])),
            key="sheet_filter"
        )
    
    with col3:
        show_only_repeated = st.checkbox("Show repeated only (count ≥ 2)", value=False)
    
    # Apply filters
    filtered_index = value_index.copy()
    
    if search_query:
        filtered_index = search_values(filtered_index, search_query)
    
    if sheet_filter != "All Sheets":
        filtered_index = filter_values_by_sheet(filtered_index, sheet_filter)
    
    if show_only_repeated:
        filtered_index = {
            k: v for k, v in filtered_index.items() 
            if v.total_count >= 2
        }
    
    # Show missing token candidates
    missing_candidates = {
        k: v for k, v in filtered_index.items() 
        if v.is_likely_missing
    }
    
    if missing_candidates:
        st.warning(f"⚠️ Found {len(missing_candidates)} likely missing token variants")
        with st.expander("View missing tokens"):
            _render_missing_tokens_table(missing_candidates)
    
    st.divider()
    
    # Main values table
    st.markdown(f"#### Values ({len(filtered_index)} found)")
    
    if not filtered_index:
        st.info("No values match your filters.")
        return
    
    _render_values_table(filtered_index)


def _render_values_table(value_index: Dict[str, Any]) -> None:
    """Render the main values table."""
    # Prepare data for display
    rows = []
    for norm_val, freq in sorted(value_index.items(), key=lambda x: -x[1].total_count):
        rows.append({
            "Value": freq.raw_value,
            "Normalized": freq.normalized_value,
            "Count": freq.total_count,
            "Sheets": ", ".join(sorted(freq.sheets)),
            "Columns": ", ".join(sorted(freq.columns)),
            "Type": freq.inferred_type,
            "Missing?": "Yes" if freq.is_likely_missing else "No",
        })
    
    df = pd.DataFrame(rows)
    
    # Limit display to first 500 rows for performance
    if len(df) > 500:
        st.caption(f"Showing first 500 of {len(df)} values")
        df = df.head(500)
    
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_missing_tokens_table(missing_candidates: Dict[str, Any]) -> None:
    """Render missing tokens table."""
    rows = []
    for norm_val, freq in sorted(missing_candidates.items(), key=lambda x: -x[1].total_count):
        rows.append({
            "Variant": freq.raw_value,
            "Normalized": freq.normalized_value,
            "Count": freq.total_count,
            "Locations": ", ".join([f"{loc.sheet}.{loc.column}" for loc in freq.locations[:5]]),
        })
    
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_scan_summary(value_index: Dict[str, Any]) -> Dict[str, int]:
    """
    Render scan summary and return stats.
    
    Args:
        value_index: The value index
        
    Returns:
        Dict with summary statistics
    """
    total_values = len(value_index)
    repeated_values = len([v for v in value_index.values() if v.total_count >= 2])
    missing_variants = len([v for v in value_index.values() if v.is_likely_missing])
    
    # Count by type
    type_counts = {}
    for freq in value_index.values():
        t = freq.inferred_type
        type_counts[t] = type_counts.get(t, 0) + 1
    
    return {
        "total_unique": total_values,
        "repeated": repeated_values,
        "missing_variants": missing_variants,
        "by_type": type_counts,
    }
