"""Tests for the rules engine - matching safety and scope correctness."""

import pytest
import pandas as pd
from typing import Dict

from models.schemas import Rule
from models.enums import MatchMode, ScopeType, ActionType
from core.rules_engine import apply_rules, rule_matches, sort_rules_by_precedence


class TestMatchingSafety:
    """Tests for safe whole-cell matching (no substring replacement)."""
    
    def test_no_substring_match_home_homework(self):
        """Test that replacing 'Home' does not affect 'Homework'."""
        sheets = {
            "Sheet1": pd.DataFrame({
                "Column1": ["Home", "Homework", "Home", "At Home"]
            })
        }
        
        rules = [Rule(
            rule_id="1",
            source_value="Home",
            target_value="Residence",
            action_type=ActionType.REPLACE.value,
            match_mode=MatchMode.EXACT_NORMALIZED.value,
            scope_type=ScopeType.WORKBOOK.value,
        )]
        
        result = apply_rules(sheets, rules)
        
        # Only exact "Home" should be replaced
        assert result["Sheet1"].at[0, "Column1"] == "Residence"  # Home -> Residence
        assert result["Sheet1"].at[1, "Column1"] == "Homework"   # Unchanged
        assert result["Sheet1"].at[2, "Column1"] == "Residence"  # Home -> Residence
        assert result["Sheet1"].at[3, "Column1"] == "At Home"    # Unchanged
    
    def test_no_substring_match_arabic(self):
        """Test that replacing Arabic short token doesn't affect longer phrase."""
        sheets = {
            "Sheet1": pd.DataFrame({
                "Column1": ["نعم", "نعم بالتأكيد", "لا", "لا شك"]
            })
        }
        
        rules = [Rule(
            rule_id="1",
            source_value="نعم",
            target_value="1",
            action_type=ActionType.REPLACE.value,
            match_mode=MatchMode.EXACT_NORMALIZED.value,
            scope_type=ScopeType.WORKBOOK.value,
        )]
        
        result = apply_rules(sheets, rules)
        
        # Only exact "نعم" should be replaced
        assert result["Sheet1"].at[0, "Column1"] == "1"           # نعم -> 1
        assert result["Sheet1"].at[1, "Column1"] == "نعم بالتأكيد"  # Unchanged
        assert result["Sheet1"].at[2, "Column1"] == "لا"          # Unchanged
        assert result["Sheet1"].at[3, "Column1"] == "لا شك"       # Unchanged
    
    def test_exact_match_male(self):
        """Test that replacing 'Male' only affects exact matches."""
        sheets = {
            "Sheet1": pd.DataFrame({
                "Gender": ["Male", "Female", "male", "MALE", "Males"]
            })
        }
        
        rules = [Rule(
            rule_id="1",
            source_value="Male",
            target_value="M",
            action_type=ActionType.REPLACE.value,
            match_mode=MatchMode.EXACT_NORMALIZED.value,
            scope_type=ScopeType.WORKBOOK.value,
        )]
        
        result = apply_rules(sheets, rules)
        
        # Normalized match should catch Male, male, MALE
        assert result["Sheet1"].at[0, "Gender"] == "M"   # Male
        assert result["Sheet1"].at[1, "Gender"] == "Female"  # Unchanged
        assert result["Sheet1"].at[2, "Gender"] == "M"   # male (normalized)
        assert result["Sheet1"].at[3, "Gender"] == "M"   # MALE (normalized)
        assert result["Sheet1"].at[4, "Gender"] == "Males"  # Unchanged


class TestScopeCorrectness:
    """Tests for rule scope application."""
    
    def test_workbook_scope(self):
        """Test workbook-wide rule application."""
        sheets = {
            "Sheet1": pd.DataFrame({"Col": ["A", "B"]}),
            "Sheet2": pd.DataFrame({"Col": ["A", "C"]}),
        }
        
        rules = [Rule(
            rule_id="1",
            source_value="A",
            target_value="X",
            action_type=ActionType.REPLACE.value,
            match_mode=MatchMode.EXACT_RAW.value,
            scope_type=ScopeType.WORKBOOK.value,
        )]
        
        result = apply_rules(sheets, rules)
        
        assert result["Sheet1"].at[0, "Col"] == "X"
        assert result["Sheet2"].at[0, "Col"] == "X"
    
    def test_sheet_scope(self):
        """Test sheet-specific rule application."""
        sheets = {
            "Sheet1": pd.DataFrame({"Col": ["A", "B"]}),
            "Sheet2": pd.DataFrame({"Col": ["A", "C"]}),
        }
        
        rules = [Rule(
            rule_id="1",
            source_value="A",
            target_value="X",
            action_type=ActionType.REPLACE.value,
            match_mode=MatchMode.EXACT_RAW.value,
            scope_type=ScopeType.SHEET.value,
            scope_sheet="Sheet1",
        )]
        
        result = apply_rules(sheets, rules)
        
        assert result["Sheet1"].at[0, "Col"] == "X"  # Changed in Sheet1
        assert result["Sheet2"].at[0, "Col"] == "A"  # Unchanged in Sheet2
    
    def test_column_scope(self):
        """Test column-specific rule application."""
        sheets = {
            "Sheet1": pd.DataFrame({
                "Col1": ["A", "B"],
                "Col2": ["A", "C"],
            })
        }
        
        rules = [Rule(
            rule_id="1",
            source_value="A",
            target_value="X",
            action_type=ActionType.REPLACE.value,
            match_mode=MatchMode.EXACT_RAW.value,
            scope_type=ScopeType.COLUMN.value,
            scope_sheet="Sheet1",
            scope_column="Col1",
        )]
        
        result = apply_rules(sheets, rules)
        
        assert result["Sheet1"].at[0, "Col1"] == "X"  # Changed in Col1
        assert result["Sheet1"].at[0, "Col2"] == "A"  # Unchanged in Col2


class TestRulePrecedence:
    """Tests for rule precedence ordering."""
    
    def test_column_before_sheet_before_workbook(self):
        """Test that column scope takes precedence over sheet/workbook."""
        sheets = {
            "Sheet1": pd.DataFrame({"Col1": ["A"]})
        }
        
        rules = [
            Rule(
                rule_id="1",
                source_value="A",
                target_value="Workbook",
                action_type=ActionType.REPLACE.value,
                match_mode=MatchMode.EXACT_RAW.value,
                scope_type=ScopeType.WORKBOOK.value,
            ),
            Rule(
                rule_id="2",
                source_value="A",
                target_value="Column",
                action_type=ActionType.REPLACE.value,
                match_mode=MatchMode.EXACT_RAW.value,
                scope_type=ScopeType.COLUMN.value,
                scope_sheet="Sheet1",
                scope_column="Col1",
            ),
        ]
        
        sorted_rules = sort_rules_by_precedence(rules)
        
        # Column rule should come first
        assert sorted_rules[0].rule_id == "2"
        assert sorted_rules[1].rule_id == "1"
    
    def test_exact_raw_before_normalized(self):
        """Test that exact_raw takes precedence over exact_normalized."""
        rules = [
            Rule(
                rule_id="1",
                source_value="a",
                target_value="Normalized",
                action_type=ActionType.REPLACE.value,
                match_mode=MatchMode.EXACT_NORMALIZED.value,
                scope_type=ScopeType.WORKBOOK.value,
            ),
            Rule(
                rule_id="2",
                source_value="a",
                target_value="Raw",
                action_type=ActionType.REPLACE.value,
                match_mode=MatchMode.EXACT_RAW.value,
                scope_type=ScopeType.WORKBOOK.value,
            ),
        ]
        
        sorted_rules = sort_rules_by_precedence(rules)
        
        # Raw rule should come first
        assert sorted_rules[0].rule_id == "2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
