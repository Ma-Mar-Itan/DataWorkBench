"""Column type inference for statistics generation."""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from .normalizer import normalize_value
from models.enums import ColumnType


def infer_column_type(series: pd.Series) -> str:
    """
    Infer the type of a column based on its values.
    
    Args:
        series: pandas Series to analyze
        
    Returns:
        ColumnType string
    """
    # Drop NaN values for analysis
    non_null = series.dropna()
    
    if len(non_null) == 0:
        return ColumnType.TEXT.value
    
    # Convert to strings for analysis
    str_values = non_null.astype(str)
    
    # Check for numeric
    numeric_count = 0
    for val in str_values:
        try:
            float(val.replace(",", "").replace("%", ""))
            numeric_count += 1
        except (ValueError, AttributeError):
            pass
    
    numeric_ratio = numeric_count / len(non_null)
    
    if numeric_ratio > 0.9:
        return ColumnType.NUMERIC.value
    
    # Check for date
    date_count = 0
    date_patterns = [
        r"^\d{1,2}/\d{1,2}/\d{2,4}$",
        r"^\d{4}-\d{2}-\d{2}$",
        r"^\d{1,2}-\d{1,2}-\d{2,4}$",
    ]
    import re
    
    for val in str_values:
        for pattern in date_patterns:
            if re.match(pattern, str(val)):
                date_count += 1
                break
    
    date_ratio = date_count / len(non_null)
    
    if date_ratio > 0.8:
        return ColumnType.DATE.value
    
    # Check for categorical (few unique values relative to total)
    unique_count = len(non_null.unique())
    unique_ratio = unique_count / len(non_null)
    
    if unique_ratio < 0.1 and unique_count < 50:
        return ColumnType.CATEGORICAL.value
    
    # Check for short text (likely categorical or codes)
    avg_length = str_values.str.len().mean()
    if avg_length < 15 and unique_ratio < 0.3:
        return ColumnType.CATEGORICAL.value
    
    # Default to text or mixed
    if unique_ratio > 0.8:
        return ColumnType.TEXT.value
    
    return ColumnType.MIXED.value


def compute_numeric_stats(series: pd.Series) -> Dict[str, float]:
    """
    Compute statistics for a numeric column.
    
    Args:
        series: pandas Series with numeric data
        
    Returns:
        Dict with count, missing, mean, median, std, min, q1, q3, max
    """
    # Convert to numeric, coercing errors
    numeric = pd.to_numeric(series, errors="coerce")
    
    count = numeric.notna().sum()
    missing = numeric.isna().sum()
    
    if count == 0:
        return {
            "count": 0,
            "missing": int(missing),
            "mean": None,
            "median": None,
            "std": None,
            "min": None,
            "q1": None,
            "q3": None,
            "max": None,
        }
    
    return {
        "count": int(count),
        "missing": int(missing),
        "mean": float(numeric.mean()),
        "median": float(numeric.median()),
        "std": float(numeric.std()) if count > 1 else 0.0,
        "min": float(numeric.min()),
        "q1": float(numeric.quantile(0.25)),
        "q3": float(numeric.quantile(0.75)),
        "max": float(numeric.max()),
    }


def compute_categorical_stats(series: pd.Series) -> Dict[str, Any]:
    """
    Compute statistics for a categorical/text column.
    
    Args:
        series: pandas Series with categorical/text data
        
    Returns:
        Dict with non_missing_count, missing_count, unique_count, mode, top_values
    """
    str_series = series.astype(str)
    
    # Count missing
    missing_mask = str_series.isin(["", "nan", "None", "NaN"]) | series.isna()
    missing_count = missing_mask.sum()
    non_missing_count = len(series) - missing_count
    
    # Get non-missing values
    non_missing = str_series[~missing_mask]
    
    unique_count = len(non_missing.unique())
    
    # Get mode (most common value)
    if len(non_missing) > 0:
        mode = non_missing.mode().iloc[0] if len(non_missing.mode()) > 0 else None
    else:
        mode = None
    
    # Get top values with frequencies
    value_counts = non_missing.value_counts().head(10)
    top_values = [
        {"value": str(val), "count": int(count), "percentage": round(100 * count / len(non_missing), 2)}
        for val, count in value_counts.items()
    ]
    
    return {
        "non_missing_count": int(non_missing_count),
        "missing_count": int(missing_count),
        "unique_count": int(unique_count),
        "mode": mode,
        "top_values": top_values,
    }


def compute_column_stats(sheet: str, column: str, series: pd.Series) -> Dict[str, Any]:
    """
    Compute comprehensive statistics for a column.
    
    Args:
        sheet: Sheet name
        column: Column name
        series: pandas Series with column data
        
    Returns:
        Dict with all statistics
    """
    inferred_type = infer_column_type(series)
    
    stats = {
        "sheet": sheet,
        "column": column,
        "inferred_type": inferred_type,
        "total_count": len(series),
    }
    
    if inferred_type == ColumnType.NUMERIC.value:
        numeric_stats = compute_numeric_stats(series)
        stats.update(numeric_stats)
        stats["categorical_stats"] = None
    else:
        categorical_stats = compute_categorical_stats(series)
        stats.update(categorical_stats)
        stats["numeric_stats"] = None
    
    return stats


def compute_all_column_stats(sheets: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, Any]]:
    """
    Compute statistics for all columns in all sheets.
    
    Args:
        sheets: Dict of sheet_name -> DataFrame
        
    Returns:
        Dict mapping "sheet|column" -> stats dict
    """
    all_stats = {}
    
    for sheet_name, df in sheets.items():
        for col_name in df.columns:
            key = f"{sheet_name}|{col_name}"
            stats = compute_column_stats(sheet_name, col_name, df[col_name])
            all_stats[key] = stats
    
    return all_stats
