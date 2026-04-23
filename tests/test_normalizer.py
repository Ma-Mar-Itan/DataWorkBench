"""Tests for the normalizer module."""

import pytest
from core.normalizer import normalize_value, is_likely_missing, infer_value_type


class TestNormalizeValue:
    """Tests for normalize_value function."""
    
    def test_basic_latin(self):
        """Test basic Latin text normalization."""
        assert normalize_value("Hello") == "hello"
        assert normalize_value("HELLO") == "hello"
        assert normalize_value("  hello  ") == "hello"
    
    def test_arabic_preservation(self):
        """Test that Arabic text is preserved correctly."""
        arabic = "مرحبا"
        result = normalize_value(arabic)
        assert result == arabic  # Arabic should be preserved
    
    def test_arabic_tatweel_removal(self):
        """Test removal of Arabic tatweel (elongation)."""
        # Tatweel character: ـ
        with_tatweel = "سلامـ"
        result = normalize_value(with_tatweel)
        assert "ـ" not in result
    
    def test_whitespace_normalization(self):
        """Test whitespace handling."""
        assert normalize_value("  hello   world  ") == "hello world"
        assert normalize_value("\t\nhello\n\t") == "hello"
    
    def test_empty_and_none(self):
        """Test empty and None values."""
        assert normalize_value(None) == ""
        assert normalize_value("") == ""
        assert normalize_value("   ") == ""
    
    def test_numeric_strings(self):
        """Test numeric strings are preserved."""
        assert normalize_value("123") == "123"
        assert normalize_value("12.5") == "12.5"
    
    def test_mixed_content(self):
        """Test mixed Latin and Arabic content."""
        mixed = "Hello مرحبا"
        result = normalize_value(mixed)
        # Latin should be casefolded, Arabic preserved
        assert "مرحبا" in result


class TestIsLikelyMissing:
    """Tests for is_likely_missing function."""
    
    def test_common_missing_tokens(self):
        """Test common missing value tokens."""
        assert is_likely_missing("N/A") is True
        assert is_likely_missing("n/a") is True
        assert is_likely_missing("NA") is True
        assert is_likely_missing("-") is True
        assert is_likely_missing(".") is True
        assert is_likely_missing("missing") is True
        assert is_likely_missing("null") is True
        assert is_likely_missing("None") is True
    
    def test_arabic_missing_tokens(self):
        """Test Arabic missing value tokens."""
        assert is_likely_missing("لا شيء") is True
        assert is_likely_missing("فارغ") is True
        assert is_likely_missing("غير متوفر") is True
    
    def test_not_missing(self):
        """Test non-missing values."""
        assert is_likely_missing("Male") is False
        assert is_likely_missing("Female") is False
        assert is_likely_missing("Yes") is False
        assert is_likely_missing("No") is False


class TestInferValueType:
    """Tests for infer_value_type function."""
    
    def test_numeric_detection(self):
        """Test numeric value detection."""
        assert infer_value_type("123") == "numeric"
        assert infer_value_type("12.5") == "numeric"
        assert infer_value_type("1,000") == "numeric"
    
    def test_date_detection(self):
        """Test date value detection."""
        assert infer_value_type("2024-01-15") == "date"
        assert infer_value_type("01/15/2024") == "date"
        assert infer_value_type("15-01-2024") == "date"
    
    def test_categorical_detection(self):
        """Test categorical value detection."""
        assert infer_value_type("Male") == "categorical"
        assert infer_value_type("Yes") == "categorical"
        assert infer_value_type("A") == "categorical"
    
    def test_text_detection(self):
        """Test free text detection."""
        long_text = "This is a longer piece of text that should be classified as free text"
        assert infer_value_type(long_text) == "text"
    
    def test_empty_detection(self):
        """Test empty value detection."""
        assert infer_value_type("") == "empty"
        assert infer_value_type("   ") == "empty"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
