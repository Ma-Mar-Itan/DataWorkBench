"""Scanner for building value-frequency index from workbook data."""

import pandas as pd
from typing import Dict, List, Any
from collections import defaultdict

from .normalizer import normalize_value, is_likely_missing, infer_value_type
from models.schemas import ValueFrequency, ValueLocation


def scan_workbook(sheets: Dict[str, pd.DataFrame]) -> Dict[str, ValueFrequency]:
    """
    Scan all sheets and build a value-frequency index.
    
    For each unique value, tracks:
    - Raw value
    - Normalized value
    - Total count
    - Which sheets it appears in
    - Which columns it appears in
    - Sample locations
    
    Args:
        sheets: Dict of sheet_name -> DataFrame
        
    Returns:
        Dict mapping normalized_value -> ValueFrequency
    """
    # Use normalized values as keys to group variants together
    value_index: Dict[str, ValueFrequency] = {}
    
    for sheet_name, df in sheets.items():
        for col_idx, col_name in enumerate(df.columns):
            for row_idx, cell_value in enumerate(df[col_name]):
                # Skip NaN values
                if pd.isna(cell_value):
                    continue
                
                # Convert to string and get raw/normalized forms
                raw_value = str(cell_value)
                normalized = normalize_value(raw_value)
                
                # Skip empty normalized values
                if not normalized:
                    continue
                
                # Create location record
                location = ValueLocation(
                    sheet=sheet_name,
                    column=col_name,
                    row_index=row_idx,
                    cell_value=raw_value,
                )
                
                # Get or create frequency record
                if normalized not in value_index:
                    # Infer type from first occurrence
                    inferred_type = infer_value_type(raw_value)
                    value_index[normalized] = ValueFrequency(
                        raw_value=raw_value,
                        normalized_value=normalized,
                        total_count=0,
                        locations=[],
                        sheets=set(),
                        columns=set(),
                        is_likely_missing=is_likely_missing(raw_value),
                        inferred_type=inferred_type,
                    )
                
                # Update frequency record
                freq = value_index[normalized]
                freq.total_count += 1
                freq.locations.append(location)
                freq.sheets.add(sheet_name)
                freq.columns.add(col_name)
                
                # Keep the most common raw representation
                # (first one encountered is fine for now)
    
    return value_index


def get_value_locations(value_freq: ValueFrequency, 
                        max_locations: int = 100) -> List[ValueLocation]:
    """
    Get sample locations for a value.
    
    Args:
        value_freq: ValueFrequency record
        max_locations: Maximum number of locations to return
        
    Returns:
        List of ValueLocation records
    """
    return value_freq.locations[:max_locations]


def filter_values_by_sheet(value_index: Dict[str, ValueFrequency],
                           sheet_name: str) -> Dict[str, ValueFrequency]:
    """Filter value index to only values appearing in a specific sheet."""
    return {
        k: v for k, v in value_index.items()
        if sheet_name in v.sheets
    }


def filter_values_by_column(value_index: Dict[str, ValueFrequency],
                            sheet_name: str,
                            column_name: str) -> Dict[str, ValueFrequency]:
    """Filter value index to only values appearing in a specific column."""
    return {
        k: v for k, v in value_index.items()
        if sheet_name in v.sheets and column_name in v.columns
    }


def search_values(value_index: Dict[str, ValueFrequency],
                  query: str) -> Dict[str, ValueFrequency]:
    """
    Search values by raw or normalized form.
    
    Uses whole-value matching only (no substring matching).
    
    Args:
        value_index: The full value index
        query: Search query string
        
    Returns:
        Filtered value index matching the query
    """
    if not query:
        return value_index
    
    query_normalized = normalize_value(query)
    
    results = {}
    for norm_key, value_freq in value_index.items():
        # Match against raw value (exact)
        if value_freq.raw_value == query:
            results[norm_key] = value_freq
            continue
        
        # Match against normalized value (exact)
        if norm_key == query_normalized:
            results[norm_key] = value_freq
            continue
        
        # Also check if query appears as exact match in any raw variant
        # This handles case where user searches for "male" but data has "Male"
        if query.lower() == value_freq.raw_value.lower():
            results[norm_key] = value_freq
    
    return results


def get_repeated_values(value_index: Dict[str, ValueFrequency],
                        min_count: int = 2) -> Dict[str, ValueFrequency]:
    """Get values that appear more than once."""
    return {
        k: v for k, v in value_index.items()
        if v.total_count >= min_count
    }


def get_missing_candidates(value_index: Dict[str, ValueFrequency]) -> Dict[str, ValueFrequency]:
    """Get values that are likely missing tokens."""
    return {
        k: v for k, v in value_index.items()
        if v.is_likely_missing
    }


def get_categorical_values(value_index: Dict[str, ValueFrequency]) -> Dict[str, ValueFrequency]:
    """Get values inferred as categorical."""
    return {
        k: v for k, v in value_index.items()
        if v.inferred_type == "categorical"
    }
