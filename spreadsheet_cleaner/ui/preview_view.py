"""Preview view for before/after data comparison."""

import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional

from core.preview_engine import generate_preview, create_highlighted_preview
from core.rules_engine import apply_rules


def render_preview_view(sheets: Dict[str, pd.DataFrame],
                        rules: List[Any],
                        metadata: Dict[str, Any]) -> None:
    """
    Render the preview view.
    
    Args:
        sheets: Original sheet data
        rules: List of cleaning rules
        metadata: Workbook metadata
    """
    st.markdown("### Preview Changes")
    st.markdown(
        "<p style='color: #5f6368; margin-bottom: 24px;'>Review changes before exporting.</p>",
        unsafe_allow_html=True
    )
    
    if not rules:
        st.info("No cleaning rules have been created. Add rules in the 'Cleaning Rules' section.")
        return
    
    # Sheet selector
    sheet_names = list(metadata.get("sheet_names", []))
    
    if not sheet_names:
        st.error("No sheets found in workbook.")
        return
    
    selected_sheet = st.selectbox(
        "Select sheet to preview",
        options=sheet_names,
        key="preview_sheet"
    )
    
    # Generate preview
    try:
        preview_data = generate_preview(sheets, rules, selected_sheet, max_rows=100)
    except Exception as e:
        st.error(f"Error generating preview: {e}")
        return
    
    # Summary stats
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Changed Cells", len(preview_data.changed_cells))
    
    with col2:
        st.metric("Total Rows", len(preview_data.original_df))
    
    with col3:
        st.metric("Applied Rules", len([r for r in rules if r.enabled]))
    
    st.divider()
    
    # Applied rules summary
    st.markdown("#### Applied Rules")
    if preview_data.applied_rules:
        for rule_desc in preview_data.applied_rules:
            st.text(f"• {rule_desc}")
    else:
        st.info("No enabled rules to apply.")
    
    st.divider()
    
    # Before/After tabs
    tab1, tab2 = st.tabs(["📄 Original Data", "✨ Cleaned Data"])
    
    with tab1:
        st.markdown("##### Original Data (First 100 rows)")
        st.dataframe(
            preview_data.original_df,
            use_container_width=True,
            hide_index=True
        )
    
    with tab2:
        st.markdown("##### Cleaned Data (First 100 rows)")
        st.dataframe(
            preview_data.cleaned_df,
            use_container_width=True,
            hide_index=True
        )
    
    st.divider()
    
    # Side-by-side comparison for changed cells only
    if preview_data.changed_cells:
        st.markdown("#### Changed Cells Highlight")
        
        # Create comparison dataframe
        comparison_data = []
        
        for row_idx, col_idx in preview_data.changed_cells[:50]:  # Limit to 50 changes
            orig_val = preview_data.original_df.iat[row_idx, col_idx]
            clean_val = preview_data.cleaned_df.iat[row_idx, col_idx]
            col_name = preview_data.original_df.columns[col_idx]
            
            comparison_data.append({
                "Row": row_idx + 1,
                "Column": col_name,
                "Before": str(orig_val) if pd.notna(orig_val) else "(empty)",
                "After": str(clean_val) if pd.notna(clean_val) else "(empty)",
            })
        
        if comparison_data:
            comparison_df = pd.DataFrame(comparison_data)
            st.dataframe(comparison_df, use_container_width=True, hide_index=True)
            st.caption(f"Showing first {len(comparison_data)} changes")
    else:
        st.info("No changes will be made with current rules.")


def render_quick_preview(sheets: Dict[str, pd.DataFrame],
                         rules: List[Any],
                         sheet_name: str) -> Optional[Dict[str, Any]]:
    """
    Render a quick inline preview.
    
    Args:
        sheets: Original data
        rules: Cleaning rules
        sheet_name: Sheet to preview
        
    Returns:
        Preview data dict or None
    """
    if not rules or sheet_name not in sheets:
        return None
    
    try:
        preview_data = generate_preview(sheets, rules, sheet_name, max_rows=20)
        highlighted = create_highlighted_preview(preview_data)
        
        return highlighted
    except Exception:
        return None


def get_preview_summary(sheets: Dict[str, pd.DataFrame],
                        rules: List[Any]) -> Dict[str, Any]:
    """
    Get a summary of preview changes across all sheets.
    
    Args:
        sheets: Original data
        rules: Cleaning rules
        
    Returns:
        Summary dict
    """
    summary = {
        "total_changes": 0,
        "by_sheet": {},
        "rules_applied": len([r for r in rules if r.enabled]),
    }
    
    # Apply rules once
    cleaned_sheets = apply_rules(sheets, rules)
    
    for sheet_name in sheets:
        if sheet_name not in cleaned_sheets:
            continue
        
        orig_df = sheets[sheet_name]
        clean_df = cleaned_sheets[sheet_name]
        
        changes = 0
        for col in orig_df.columns:
            for idx in range(len(orig_df)):
                orig_val = orig_df.at[idx, col]
                clean_val = clean_df.at[idx, col]
                
                orig_str = "" if pd.isna(orig_val) else str(orig_val)
                clean_str = "" if pd.isna(clean_val) else str(clean_val)
                
                if orig_str != clean_str:
                    changes += 1
        
        summary["by_sheet"][sheet_name] = changes
        summary["total_changes"] += changes
    
    return summary
