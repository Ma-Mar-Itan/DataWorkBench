"""Statistics engine for generating descriptive statistics."""

import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime

from core.type_inference import compute_all_column_stats, infer_column_type
from core.normalizer import normalize_value, is_likely_missing


def generate_workbook_stats(sheets: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """
    Generate workbook-level statistics.
    
    Args:
        sheets: Dict of sheet_name -> DataFrame
        
    Returns:
        Dict with workbook-level statistics
    """
    total_rows = 0
    total_columns = 0
    total_cells = 0
    total_missing = 0
    all_values = []
    
    for sheet_name, df in sheets.items():
        total_rows += len(df)
        total_columns += len(df.columns)
        total_cells += len(df) * len(df.columns)
        
        # Count missing values
        for col in df.columns:
            missing_count = df[col].isna().sum()
            missing_count += (df[col].astype(str).isin(["", "nan", "None", "NaN"])).sum()
            total_missing += missing_count
            
            # Collect all values for unique count
            all_values.extend(df[col].dropna().astype(str).tolist())
    
    unique_values = set(normalize_value(v) for v in all_values if v)
    
    return {
        "num_sheets": len(sheets),
        "sheet_names": list(sheets.keys()),
        "total_rows": total_rows,
        "total_columns": total_columns,
        "total_cells": total_cells,
        "total_missing": total_missing,
        "unique_values": len(unique_values),
        "missing_percentage": round(100 * total_missing / max(total_cells, 1), 2),
    }


def generate_column_stats(sheets: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
    """
    Generate per-column statistics.
    
    Args:
        sheets: Dict of sheet_name -> DataFrame
        
    Returns:
        List of column statistics dicts
    """
    stats_list = []
    
    for sheet_name, df in sheets.items():
        for col_name in df.columns:
            series = df[col_name]
            
            # Infer type
            inferred_type = infer_column_type(series)
            
            # Basic counts
            total_count = len(series)
            missing_count = series.isna().sum()
            missing_count += (series.astype(str).isin(["", "nan", "None", "NaN"])).sum()
            non_missing = series.dropna()
            non_missing = non_missing[~non_missing.astype(str).isin(["", "nan", "None", "NaN"])]
            unique_count = len(non_missing.unique()) if len(non_missing) > 0 else 0
            
            col_stats = {
                "sheet": sheet_name,
                "column": col_name,
                "inferred_type": inferred_type,
                "total_count": int(total_count),
                "missing_count": int(missing_count),
                "non_missing_count": int(total_count - missing_count),
                "unique_count": int(unique_count),
            }
            
            # Type-specific stats
            if inferred_type == "numeric":
                numeric = pd.to_numeric(series, errors="coerce")
                non_null_numeric = numeric.dropna()
                
                if len(non_null_numeric) > 0:
                    col_stats["numeric_stats"] = {
                        "mean": round(float(non_null_numeric.mean()), 4),
                        "median": round(float(non_null_numeric.median()), 4),
                        "std": round(float(non_null_numeric.std()), 4) if len(non_null_numeric) > 1 else 0,
                        "min": float(non_null_numeric.min()),
                        "max": float(non_null_numeric.max()),
                        "q1": round(float(non_null_numeric.quantile(0.25)), 4),
                        "q3": round(float(non_null_numeric.quantile(0.75)), 4),
                    }
            
            # Categorical stats for non-numeric columns
            if inferred_type != "numeric" and len(non_missing) > 0:
                value_counts = non_missing.astype(str).value_counts().head(10)
                top_values = [
                    {
                        "value": str(val),
                        "count": int(count),
                        "percentage": round(100 * count / len(non_missing), 2)
                    }
                    for val, count in value_counts.items()
                ]
                col_stats["categorical_stats"] = {
                    "mode": str(value_counts.index[0]) if len(value_counts) > 0 else None,
                    "top_values": top_values,
                }
            
            stats_list.append(col_stats)
    
    return stats_list


def generate_before_after_stats(
    original_sheets: Dict[str, pd.DataFrame],
    cleaned_sheets: Dict[str, pd.DataFrame]
) -> Dict[str, Any]:
    """
    Generate before/after comparison statistics.
    
    Args:
        original_sheets: Original data
        cleaned_sheets: Cleaned data
        
    Returns:
        Dict with before/after comparison
    """
    # Count total changes
    total_changes = 0
    
    for sheet_name in original_sheets:
        if sheet_name not in cleaned_sheets:
            continue
        
        orig_df = original_sheets[sheet_name]
        clean_df = cleaned_sheets[sheet_name]
        
        for col_name in orig_df.columns:
            for row_idx in range(len(orig_df)):
                orig_val = orig_df.at[row_idx, col_name]
                clean_val = clean_df.at[row_idx, col_name]
                
                orig_str = "" if pd.isna(orig_val) else str(orig_val)
                clean_str = "" if pd.isna(clean_val) else str(clean_val)
                
                if orig_str != clean_str:
                    total_changes += 1
    
    # Get category distribution changes for categorical columns
    category_changes = {}
    
    for sheet_name in original_sheets:
        if sheet_name not in cleaned_sheets:
            continue
        
        orig_df = original_sheets[sheet_name]
        clean_df = cleaned_sheets[sheet_name]
        
        for col_name in orig_df.columns:
            orig_type = infer_column_type(orig_df[col_name])
            
            if orig_type in ["categorical", "text"]:
                orig_counts = orig_df[col_name].dropna().astype(str).value_counts().head(5)
                clean_counts = clean_df[col_name].dropna().astype(str).value_counts().head(5)
                
                orig_unique = len(orig_df[col_name].dropna().unique())
                clean_unique = len(clean_df[col_name].dropna().unique())
                
                if orig_unique != clean_unique:
                    key = f"{sheet_name}.{col_name}"
                    category_changes[key] = {
                        "before_unique": orig_unique,
                        "after_unique": clean_unique,
                        "reduction": orig_unique - clean_unique,
                        "before_top": {str(k): int(v) for k, v in orig_counts.items()},
                        "after_top": {str(k): int(v) for k, v in clean_counts.items()},
                    }
    
    return {
        "total_changes": total_changes,
        "affected_columns": len(category_changes),
        "category_changes": category_changes,
        "generated_at": datetime.now().isoformat(),
    }


def generate_full_statistics_report(
    sheets: Dict[str, pd.DataFrame],
    cleaned_sheets: Optional[Dict[str, pd.DataFrame]] = None
) -> Dict[str, Any]:
    """
    Generate a complete statistics report.
    
    Args:
        sheets: Original data
        cleaned_sheets: Optional cleaned data for before/after comparison
        
    Returns:
        Complete statistics report dict
    """
    report = {
        "workbook": generate_workbook_stats(sheets),
        "columns": generate_column_stats(sheets),
        "generated_at": datetime.now().isoformat(),
    }
    
    if cleaned_sheets is not None:
        report["before_after"] = generate_before_after_stats(sheets, cleaned_sheets)
    
    return report


def get_missing_token_summary(sheets: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """
    Get summary of likely missing tokens in the data.
    
    Args:
        sheets: Original data
        
    Returns:
        Dict with missing token analysis
    """
    missing_tokens = {}
    
    for sheet_name, df in sheets.items():
        for col_name in df.columns:
            for val in df[col_name].dropna().unique():
                str_val = str(val)
                if is_likely_missing(str_val):
                    normalized = normalize_value(str_val)
                    
                    if normalized not in missing_tokens:
                        missing_tokens[normalized] = {
                            "variants": [],
                            "locations": [],
                            "total_count": 0,
                        }
                    
                    # Count occurrences
                    count = (df[col_name].astype(str) == str_val).sum()
                    
                    if str_val not in missing_tokens[normalized]["variants"]:
                        missing_tokens[normalized]["variants"].append(str_val)
                    
                    missing_tokens[normalized]["total_count"] += count
                    
                    if len(missing_tokens[normalized]["locations"]) < 5:
                        missing_tokens[normalized]["locations"].append({
                            "sheet": sheet_name,
                            "column": col_name,
                            "example": str_val,
                        })
    
    return {
        "total_missing_variants": len(missing_tokens),
        "tokens": missing_tokens,
    }
