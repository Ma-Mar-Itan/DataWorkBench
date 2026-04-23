"""Export view for exporting cleaned data and reports."""

import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional
import tempfile
import os
from datetime import datetime

from core.exporter import (
    export_cleaned_workbook,
    export_statistics_report,
    export_ruleset,
    create_export_summary,
)
from core.rules_engine import apply_rules
from core.stats_engine import generate_full_statistics_report


def render_export_view(sheets: Dict[str, pd.DataFrame],
                       rules: List[Any],
                       metadata: Dict[str, Any]) -> None:
    """
    Render the export view.
    
    Args:
        sheets: Original sheet data
        rules: List of cleaning rules
        metadata: Workbook metadata
    """
    st.markdown("### Export")
    st.markdown(
        "<p style='color: #5f6368; margin-bottom: 24px;'>Export your cleaned data and reports.</p>",
        unsafe_allow_html=True
    )
    
    if not rules:
        st.info("No cleaning rules have been created. The exported file will be identical to the original.")
    
    # Apply rules to get cleaned data
    with st.spinner("Applying cleaning rules..."):
        cleaned_sheets = apply_rules(sheets, rules)
    
    # Generate statistics
    stats = generate_full_statistics_report(cleaned_sheets)
    
    # Export summary
    summary = create_export_summary(cleaned_sheets, rules, stats)
    
    st.markdown("#### Export Summary")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Sheets", len(cleaned_sheets))
    
    with col2:
        total_rows = sum(len(df) for df in cleaned_sheets.values())
        st.metric("Total Rows", total_rows)
    
    with col3:
        st.metric("Rules Applied", summary["rules_applied"])
    
    st.divider()
    
    # Export options
    st.markdown("#### Export Options")
    
    # Get base filename
    original_name = metadata.get("file_name", "workbook")
    base_name = os.path.splitext(original_name)[0]
    
    # Create temp directory for exports
    temp_dir = tempfile.mkdtemp()
    
    # Cleaned workbook export
    st.markdown("##### 1. Cleaned Workbook")
    
    cleaned_path = os.path.join(temp_dir, f"{base_name}_cleaned.xlsx")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.text(f"File: {base_name}_cleaned.xlsx")
        st.caption("Excel workbook with all cleaning rules applied")
    
    with col2:
        if st.button("Download .xlsx", key="download_xlsx", use_container_width=True):
            export_cleaned_workbook(cleaned_sheets, cleaned_path)
            _provide_download_link(cleaned_path, f"{base_name}_cleaned.xlsx")
    
    st.divider()
    
    # Statistics report export
    st.markdown("##### 2. Statistics Report")
    
    stats_path_json = os.path.join(temp_dir, f"{base_name}_statistics.json")
    stats_path_csv = os.path.join(temp_dir, f"{base_name}_column_stats.csv")
    
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.text(f"Files: {base_name}_statistics.json, {base_name}_column_stats.csv")
        st.caption("Comprehensive statistics about your data")
    
    with col2:
        if st.button("Download JSON", key="download_stats_json", use_container_width=True):
            export_statistics_report(stats, stats_path_json, format="json")
            _provide_download_link(stats_path_json, f"{base_name}_statistics.json")
    
    with col3:
        if st.button("Download CSV", key="download_stats_csv", use_container_width=True):
            export_statistics_report(stats, stats_path_csv, format="csv")
            _provide_download_link(stats_path_csv, f"{base_name}_column_stats.csv")
    
    st.divider()
    
    # Ruleset export
    st.markdown("##### 3. Cleaning Ruleset")
    
    ruleset_path = os.path.join(temp_dir, f"{base_name}_rules.json")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.text(f"File: {base_name}_rules.json")
        st.caption(f"Save {len(rules)} rules for reuse on other workbooks")
    
    with col2:
        if st.button("Download Rules", key="download_rules", use_container_width=True):
            export_ruleset(rules, ruleset_path)
            _provide_download_link(ruleset_path, f"{base_name}_rules.json")
    
    st.divider()
    
    # Display preview of what will be exported
    st.markdown("#### Preview of Cleaned Data")
    
    sheet_names = list(metadata.get("sheet_names", []))
    
    if sheet_names:
        selected_sheet = st.selectbox(
            "Select sheet to preview",
            options=sheet_names,
            key="export_preview_sheet"
        )
        
        if selected_sheet in cleaned_sheets:
            st.dataframe(
                cleaned_sheets[selected_sheet].head(50),
                use_container_width=True,
                hide_index=True
            )


def _provide_download_link(filepath: str, filename: str) -> None:
    """Provide a download link for a file."""
    try:
        with open(filepath, "rb") as f:
            st.download_button(
                label=f"⬇️ Save {filename}",
                data=f.read(),
                file_name=filename,
                mime="application/octet-stream",
                key=f"download_{filename}",
            )
    except Exception as e:
        st.error(f"Error preparing download: {e}")


def render_quick_export(sheets: Dict[str, pd.DataFrame],
                        rules: List[Any],
                        metadata: Dict[str, Any]) -> Optional[str]:
    """
    Render a quick export button.
    
    Args:
        sheets: Original data
        rules: Cleaning rules
        metadata: Workbook metadata
        
    Returns:
        Path to exported file or None
    """
    if st.button("⚡ Quick Export Cleaned Workbook"):
        with st.spinner("Exporting..."):
            temp_dir = tempfile.mkdtemp()
            original_name = metadata.get("file_name", "workbook")
            base_name = os.path.splitext(original_name)[0]
            output_path = os.path.join(temp_dir, f"{base_name}_cleaned.xlsx")
            
            cleaned_sheets = apply_rules(sheets, rules)
            export_cleaned_workbook(cleaned_sheets, output_path)
            
            return output_path
    
    return None


def get_export_ready_data(sheets: Dict[str, pd.DataFrame],
                          rules: List[Any]) -> Dict[str, pd.DataFrame]:
    """
    Get cleaned data ready for export.
    
    Args:
        sheets: Original data
        rules: Cleaning rules
        
    Returns:
        Dict of cleaned sheets
    """
    return apply_rules(sheets, rules)
