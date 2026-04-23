"""Preview engine for before/after comparison."""

import pandas as pd
from typing import Dict, List, Tuple, Any

from models.schemas import PreviewData, Rule
from core.rules_engine import apply_rules


def generate_preview(original_sheets: Dict[str, pd.DataFrame],
                     rules: List[Rule],
                     sheet_name: str,
                     max_rows: int = 100) -> PreviewData:
    """
    Generate preview data for before/after comparison.
    
    Args:
        original_sheets: Original workbook data
        rules: List of cleaning rules
        sheet_name: Sheet to preview
        max_rows: Maximum rows to include in preview
        
    Returns:
        PreviewData with original, cleaned, and change information
    """
    if sheet_name not in original_sheets:
        raise ValueError(f"Sheet '{sheet_name}' not found")
    
    # Get original data (limited to max_rows)
    original_df = original_sheets[sheet_name].head(max_rows).copy()
    
    # Apply rules to get cleaned data
    cleaned_sheets = apply_rules(original_sheets, rules)
    cleaned_df = cleaned_sheets[sheet_name].head(max_rows).copy()
    
    # Find changed cells
    changed_cells = find_changed_cells(original_df, cleaned_df)
    
    # Get applied rule descriptions
    applied_rules = [
        f"{rule.source_value} → {rule.target_value}" 
        for rule in rules 
        if rule.enabled
    ]
    
    return PreviewData(
        sheet=sheet_name,
        original_df=original_df,
        cleaned_df=cleaned_df,
        changed_cells=changed_cells,
        applied_rules=applied_rules,
    )


def find_changed_cells(original_df: pd.DataFrame,
                       cleaned_df: pd.DataFrame) -> List[Tuple[int, int]]:
    """
    Find cells that changed between original and cleaned data.
    
    Args:
        original_df: Original DataFrame
        cleaned_df: Cleaned DataFrame
        
    Returns:
        List of (row_idx, col_idx) tuples for changed cells
    """
    changed = []
    
    # Ensure same shape
    if original_df.shape != cleaned_df.shape:
        return changed
    
    for row_idx in range(len(original_df)):
        for col_idx, col_name in enumerate(original_df.columns):
            orig_val = original_df.at[row_idx, col_name]
            clean_val = cleaned_df.at[row_idx, col_name]
            
            # Handle NaN comparison
            orig_str = "" if pd.isna(orig_val) else str(orig_val)
            clean_str = "" if pd.isna(clean_val) else str(clean_val)
            
            if orig_str != clean_str:
                changed.append((row_idx, col_idx))
    
    return changed


def create_highlighted_preview(preview_data: PreviewData) -> Dict[str, Any]:
    """
    Create a preview with change highlighting information.
    
    Args:
        preview_data: PreviewData object
        
    Returns:
        Dict with display-ready preview information
    """
    # Convert DataFrames to dict for JSON serialization
    original_records = preview_data.original_df.to_dict("records")
    cleaned_records = preview_data.cleaned_df.to_dict("records")
    
    # Create set of changed cell keys for quick lookup
    changed_set = set(preview_data.changed_cells)
    
    # Add highlight information
    highlighted_original = []
    highlighted_cleaned = []
    
    for row_idx, (orig_row, clean_row) in enumerate(zip(original_records, cleaned_records)):
        highlighted_orig_row = {}
        highlighted_clean_row = {}
        
        for col_idx, col_name in enumerate(preview_data.original_df.columns):
            is_changed = (row_idx, col_idx) in changed_set
            
            highlighted_orig_row[col_name] = {
                "value": orig_row.get(col_name, ""),
                "is_changed": is_changed,
            }
            highlighted_clean_row[col_name] = {
                "value": clean_row.get(col_name, ""),
                "is_changed": is_changed,
            }
        
        highlighted_original.append(highlighted_orig_row)
        highlighted_cleaned.append(highlighted_clean_row)
    
    return {
        "sheet": preview_data.sheet,
        "original": highlighted_original,
        "cleaned": highlighted_cleaned,
        "changed_count": len(preview_data.changed_cells),
        "applied_rules": preview_data.applied_rules,
        "columns": list(preview_data.original_df.columns),
    }


def get_change_summary(original_sheets: Dict[str, pd.DataFrame],
                       cleaned_sheets: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """
    Get a summary of changes across the workbook.
    
    Args:
        original_sheets: Original data
        cleaned_sheets: Cleaned data
        
    Returns:
        Summary dict with per-sheet change counts
    """
    summary = {
        "total_changes": 0,
        "by_sheet": {},
        "by_column": {},
    }
    
    for sheet_name in original_sheets:
        if sheet_name not in cleaned_sheets:
            continue
        
        original_df = original_sheets[sheet_name]
        cleaned_df = cleaned_sheets[sheet_name]
        
        sheet_changes = 0
        column_changes = {}
        
        for col_name in original_df.columns:
            col_change_count = 0
            
            for row_idx in range(len(original_df)):
                orig_val = original_df.at[row_idx, col_name]
                clean_val = cleaned_df.at[row_idx, col_name]
                
                orig_str = "" if pd.isna(orig_val) else str(orig_val)
                clean_str = "" if pd.isna(clean_val) else str(clean_val)
                
                if orig_str != clean_str:
                    sheet_changes += 1
                    col_change_count += 1
            
            if col_change_count > 0:
                column_changes[f"{sheet_name}.{col_name}"] = col_change_count
        
        summary["by_sheet"][sheet_name] = sheet_changes
        summary["total_changes"] += sheet_changes
        summary["by_column"].update(column_changes)
    
    return summary
