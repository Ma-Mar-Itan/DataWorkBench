"""Rules engine for applying cleaning rules with proper scope and matching."""

import pandas as pd
from typing import Dict, List, Optional, Any
from copy import deepcopy

from models.schemas import Rule
from models.enums import MatchMode, ScopeType, ActionType, RulePrecedence
from core.normalizer import normalize_value


def apply_rules(sheets: Dict[str, pd.DataFrame], 
                rules: List[Rule]) -> Dict[str, pd.DataFrame]:
    """
    Apply cleaning rules to workbook data.
    
    Rule precedence:
    1. Column scope (highest priority)
    2. Sheet scope
    3. Workbook scope (lowest priority)
    
    Within same scope:
    1. exact_raw match mode
    2. exact_normalized match mode
    
    Args:
        sheets: Dict of sheet_name -> DataFrame
        rules: List of Rule objects to apply
        
    Returns:
        Dict of sheet_name -> cleaned DataFrame
    """
    # Create deep copy to avoid modifying original
    cleaned_sheets = {
        name: df.copy() for name, df in sheets.items()
    }
    
    # Sort rules by precedence
    sorted_rules = sort_rules_by_precedence(rules)
    
    # Track which cells have been modified (to avoid double-applying)
    # Key: (sheet, row_idx, col_idx)
    modified_cells = set()
    
    # Apply each rule in order
    for rule in sorted_rules:
        if not rule.enabled:
            continue
        
        cleaned_sheets = apply_single_rule(
            cleaned_sheets, rule, modified_cells
        )
    
    return cleaned_sheets


def sort_rules_by_precedence(rules: List[Rule]) -> List[Rule]:
    """
    Sort rules by precedence.
    
    Higher priority rules come first:
    - Column scope before sheet scope before workbook scope
    - exact_raw before exact_normalized within same scope
    """
    def get_priority(rule: Rule) -> tuple:
        # Scope priority (lower = higher priority)
        if rule.scope_type == ScopeType.COLUMN.value:
            scope_priority = RulePrecedence.COLUMN
        elif rule.scope_type == ScopeType.SHEET.value:
            scope_priority = RulePrecedence.SHEET
        else:
            scope_priority = RulePrecedence.WORKBOOK
        
        # Match mode priority
        if rule.match_mode == MatchMode.EXACT_RAW.value:
            match_priority = RulePrecedence.MATCH_EXACT_RAW
        else:
            match_priority = RulePrecedence.MATCH_EXACT_NORMALIZED
        
        # Created time as tiebreaker (earlier = higher priority)
        time_priority = rule.created_at
        
        return (scope_priority, match_priority, time_priority)
    
    return sorted(rules, key=get_priority)


def apply_single_rule(sheets: Dict[str, pd.DataFrame],
                      rule: Rule,
                      modified_cells: set) -> Dict[str, pd.DataFrame]:
    """
    Apply a single rule to the workbook.
    
    Args:
        sheets: Dict of sheet_name -> DataFrame
        rule: Rule to apply
        modified_cells: Set of already-modified cell coordinates
        
    Returns:
        Updated sheets dict
    """
    result = {name: df.copy() for name, df in sheets.items()}
    
    # Determine which sheets/columns to process
    if rule.scope_type == ScopeType.COLUMN.value:
        # Only process specific column in specific sheet
        if rule.scope_sheet and rule.scope_column:
            target_specs = [(rule.scope_sheet, rule.scope_column)]
        else:
            return result  # Invalid column scope
    elif rule.scope_type == ScopeType.SHEET.value:
        # Process all columns in specific sheet
        if rule.scope_sheet and rule.scope_sheet in result:
            target_specs = [
                (rule.scope_sheet, col) 
                for col in result[rule.scope_sheet].columns
            ]
        else:
            return result  # Invalid sheet scope
    else:  # WORKBOOK
        # Process all columns in all sheets
        target_specs = [
            (sheet_name, col)
            for sheet_name, df in result.items()
            for col in df.columns
        ]
    
    # Get replacement value
    if rule.action_type == ActionType.SET_BLANK.value:
        replacement = ""
    else:
        replacement = rule.target_value
    
    # Apply rule to each target
    for sheet_name, col_name in target_specs:
        df = result[sheet_name]
        
        for row_idx in range(len(df)):
            # Skip if already modified by higher-priority rule
            cell_key = (sheet_name, row_idx, col_name)
            if cell_key in modified_cells:
                continue
            
            # Get current value
            current_value = df.at[row_idx, col_name]
            
            # Skip NaN
            if pd.isna(current_value):
                continue
            
            str_value = str(current_value)
            
            # Check if rule matches
            if rule_matches(str_value, rule):
                # Apply replacement
                df.at[row_idx, col_name] = replacement
                modified_cells.add(cell_key)
    
    return result


def rule_matches(cell_value: str, rule: Rule) -> bool:
    """
    Check if a rule matches a cell value.
    
    Uses WHOLE-CELL matching only - no substring matching.
    
    Args:
        cell_value: The cell value as string
        rule: The rule to check
        
    Returns:
        True if the rule matches
    """
    source = rule.source_value
    
    if rule.match_mode == MatchMode.EXACT_RAW.value:
        # Exact raw match (case-sensitive for Arabic, case-insensitive for Latin)
        # For safety, we do exact string comparison
        return cell_value == source
    else:  # EXACT_NORMALIZED
        # Exact normalized match (whole-cell only)
        cell_normalized = normalize_value(cell_value)
        source_normalized = normalize_value(source)
        return cell_normalized == source_normalized


def count_changes(original_sheets: Dict[str, pd.DataFrame],
                  cleaned_sheets: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """
    Count the number of changes made by cleaning.
    
    Args:
        original_sheets: Original workbook data
        cleaned_sheets: Cleaned workbook data
        
    Returns:
        Dict with total_changes, affected_sheets, affected_columns
    """
    total_changes = 0
    affected_sheets = set()
    affected_columns = set()
    
    for sheet_name in original_sheets:
        if sheet_name not in cleaned_sheets:
            continue
        
        original_df = original_sheets[sheet_name]
        cleaned_df = cleaned_sheets[sheet_name]
        
        # Ensure same shape
        if original_df.shape != cleaned_df.shape:
            continue
        
        # Compare cell by cell
        for col_name in original_df.columns:
            for row_idx in range(len(original_df)):
                orig_val = original_df.at[row_idx, col_name]
                clean_val = cleaned_df.at[row_idx, col_name]
                
                # Handle NaN comparison
                orig_str = "" if pd.isna(orig_val) else str(orig_val)
                clean_str = "" if pd.isna(clean_val) else str(clean_val)
                
                if orig_str != clean_str:
                    total_changes += 1
                    affected_sheets.add(sheet_name)
                    affected_columns.add(f"{sheet_name}|{col_name}")
    
    return {
        "total_changes": total_changes,
        "affected_sheets": list(affected_sheets),
        "affected_columns": list(affected_columns),
    }


def get_changes_by_rule(original_sheets: Dict[str, pd.DataFrame],
                        cleaned_sheets: Dict[str, pd.DataFrame],
                        rules: List[Rule]) -> Dict[str, int]:
    """
    Estimate changes attributed to each rule.
    
    This is an approximation since multiple rules could affect the same cell.
    
    Args:
        original_sheets: Original data
        cleaned_sheets: Cleaned data
        rules: List of rules
        
    Returns:
        Dict mapping rule_id to change count
    """
    changes_by_rule = {}
    
    for rule in rules:
        if not rule.enabled:
            changes_by_rule[rule.rule_id] = 0
            continue
        
        # Count cells that would match this rule
        count = 0
        
        if rule.scope_type == ScopeType.COLUMN.value:
            if rule.scope_sheet and rule.scope_column:
                sheets_to_check = {rule.scope_sheet: cleaned_sheets.get(rule.scope_sheet)}
                columns_to_check = [rule.scope_column]
            else:
                changes_by_rule[rule.rule_id] = 0
                continue
        elif rule.scope_type == ScopeType.SHEET.value:
            if rule.scope_sheet:
                sheets_to_check = {rule.scope_sheet: cleaned_sheets.get(rule.scope_sheet)}
                columns_to_check = list(cleaned_sheets.get(rule.scope_sheet, pd.DataFrame()).columns)
            else:
                changes_by_rule[rule.rule_id] = 0
                continue
        else:  # WORKBOOK
            sheets_to_check = cleaned_sheets
            columns_to_check = None
        
        for sheet_name, df in sheets_to_check.items():
            if df is None:
                continue
            
            cols = columns_to_check if columns_to_check else df.columns
            
            for col_name in cols:
                if col_name not in df.columns:
                    continue
                    
                for row_idx in range(len(df)):
                    val = df.at[row_idx, col_name]
                    if pd.isna(val):
                        continue
                    
                    if rule_matches(str(val), rule):
                        count += 1
        
        changes_by_rule[rule.rule_id] = count
    
    return changes_by_rule
