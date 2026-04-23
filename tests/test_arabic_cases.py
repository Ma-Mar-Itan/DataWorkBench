"""Tests for Arabic language handling."""

import pytest
import pandas as pd

from core.normalizer import normalize_value, is_likely_missing
from core.rules_engine import apply_rules
from models.schemas import Rule
from models.enums import MatchMode, ScopeType, ActionType


class TestArabicNormalization:
    """Tests for Arabic text normalization."""
    
    def test_arabic_preservation(self):
        """Test that Arabic text is preserved through normalization."""
        arabic_texts = [
            "مرحبا",
            "العالم",
            "نعم",
            "لا",
            "كيف حالك",
        ]
        
        for text in arabic_texts:
            result = normalize_value(text)
            assert result == text, f"Arabic text '{text}' was modified to '{result}'"
    
    def test_arabic_with_whitespace(self):
        """Test Arabic text with whitespace trimming."""
        assert normalize_value("  مرحبا  ") == "مرحبا"
        assert normalize_value("\tنعم\n") == "نعم"
    
    def test_arabic_tatweel_removal(self):
        """Test removal of tatweel from Arabic text."""
        # Tatweel (U+0640) is used for elongation
        with_tatweel = "سلامـ"
        result = normalize_value(with_tatweel)
        assert "ـ" not in result
        assert result == "سلام"
    
    def test_arabic_numbers_preserved(self):
        """Test that Arabic-Indic numbers are preserved."""
        # Eastern Arabic numerals
        assert normalize_value("١٢٣") == "١٢٣"
        # Western Arabic numerals (standard)
        assert normalize_value("123") == "123"


class TestArabicMissingTokens:
    """Tests for Arabic missing value detection."""
    
    def test_arabic_missing_detection(self):
        """Test detection of Arabic missing tokens."""
        arabic_missing = [
            "لا شيء",
            "فارغ",
            "غير متوفر",
            "مجهول",
        ]
        
        for token in arabic_missing:
            assert is_likely_missing(token) is True, f"'{token}' should be detected as missing"
    
    def test_arabic_not_missing(self):
        """Test that normal Arabic words are not flagged as missing."""
        normal_words = [
            "نعم",
            "لا",
            "ربما",
            "صحيح",
            "خطأ",
        ]
        
        for word in normal_words:
            assert is_likely_missing(word) is False, f"'{word}' should NOT be detected as missing"


class TestArabicRuleMatching:
    """Tests for Arabic rule matching."""
    
    def test_arabic_exact_match(self):
        """Test exact matching for Arabic values."""
        sheets = {
            "Sheet1": pd.DataFrame({
                "Column1": ["نعم", "لا", "نعم", "ربما"]
            })
        }
        
        rules = [Rule(
            rule_id="1",
            source_value="نعم",
            target_value="1",
            action_type=ActionType.REPLACE.value,
            match_mode=MatchMode.EXACT_RAW.value,
            scope_type=ScopeType.WORKBOOK.value,
        )]
        
        result = apply_rules(sheets, rules)
        
        assert result["Sheet1"].at[0, "Column1"] == "1"
        assert result["Sheet1"].at[1, "Column1"] == "لا"
        assert result["Sheet1"].at[2, "Column1"] == "1"
        assert result["Sheet1"].at[3, "Column1"] == "ربما"
    
    def test_arabic_no_substring_match(self):
        """Test that Arabic short tokens don't match longer phrases."""
        sheets = {
            "Sheet1": pd.DataFrame({
                "Column1": [
                    "نعم",
                    "نعم بالتأكيد",
                    "نعم، شكرا",
                    "لا",
                    "لا شك"
                ]
            })
        }
        
        rules = [Rule(
            rule_id="1",
            source_value="نعم",
            target_value="YES",
            action_type=ActionType.REPLACE.value,
            match_mode=MatchMode.EXACT_NORMALIZED.value,
            scope_type=ScopeType.WORKBOOK.value,
        )]
        
        result = apply_rules(sheets, rules)
        
        # Only exact matches should change
        assert result["Sheet1"].at[0, "Column1"] == "YES"
        assert result["Sheet1"].at[1, "Column1"] == "نعم بالتأكيد"
        assert result["Sheet1"].at[2, "Column1"] == "نعم، شكرا"
        assert result["Sheet1"].at[3, "Column1"] == "لا"
        assert result["Sheet1"].at[4, "Column1"] == "لا شك"
    
    def test_arabic_case_insensitive_not_applicable(self):
        """Test that case folding doesn't affect Arabic."""
        # Arabic doesn't have case, so normalization should preserve it
        arabic = "مرحبا"
        result = normalize_value(arabic)
        assert result == arabic


class TestArabicExport:
    """Tests for Arabic data export integrity."""
    
    def test_arabic_dataframe_integrity(self):
        """Test that Arabic text survives DataFrame operations."""
        df = pd.DataFrame({
            "Name": ["أحمد", "محمد", "فاطمة"],
            "City": ["الرياض", "جدة", "مكة"],
            "Status": ["نعم", "لا", "نعم"]
        })
        
        # Verify all Arabic text is preserved
        assert df.at[0, "Name"] == "أحمد"
        assert df.at[1, "City"] == "جدة"
        assert df.at[2, "Status"] == "نعم"
    
    def test_arabic_string_conversion(self):
        """Test Arabic string conversion in DataFrames."""
        df = pd.DataFrame({
            "Col": ["مرحبا", None, "العالم"]
        })
        
        # Convert to string and check
        str_val = str(df.at[0, "Col"])
        assert str_val == "مرحبا"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
