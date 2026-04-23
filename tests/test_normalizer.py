"""Tests for the Arabic-safe normalizer."""
from __future__ import annotations

import pytest

from core.normalizer import (
    MISSING_TOKENS, is_arabic, is_missing_token, normalize, to_text,
)


class TestNormalizeBasics:
    def test_empty(self):
        assert normalize("") == ""
        assert normalize(None) == ""

    def test_none_becomes_empty(self):
        assert normalize(None) == ""

    def test_latin_casefold(self):
        assert normalize("Yes") == "yes"
        assert normalize("YES") == "yes"
        assert normalize("yes") == "yes"

    def test_whitespace_collapsed(self):
        assert normalize("  hello   world  ") == "hello world"
        assert normalize("foo\tbar") == "foo bar"
        assert normalize("foo\n\nbar") == "foo bar"

    def test_integer_stringified(self):
        assert normalize(42) == "42"

    def test_casefold_handles_eszett(self):
        # German ß -> ss under casefold (more correct than .lower())
        assert normalize("STRAẞE") == "strasse"


class TestNormalizeArabic:
    def test_arabic_preserved(self):
        assert normalize("ذكر") == "ذكر"
        assert normalize("أنثى") == "أنثى"

    def test_tatweel_removed(self):
        # tatweel is purely decorative; "أســعد" -> "أسعد"
        assert normalize("أســـــعد") == "أسعد"

    def test_arabic_whitespace_collapsed(self):
        assert normalize("  مرحبا   بك  ") == "مرحبا بك"

    def test_arabic_not_folded(self):
        # We do NOT merge ا/أ/إ. These remain distinct under normalize.
        assert normalize("احمد") != normalize("أحمد")
        assert normalize("ى") != normalize("ي")

    def test_arabic_presentation_forms_nfkc(self):
        # NFKC folds presentation forms to base forms (this is safe,
        # since presentation forms are display-only variants)
        # U+FE8E is "ARABIC LETTER ALEF FINAL FORM" → folds to U+0627
        assert "\u0627" in normalize("\ufe8e")


class TestIsArabic:
    def test_english_not_arabic(self):
        assert not is_arabic("hello")

    def test_arabic_detected(self):
        assert is_arabic("ذكر")

    def test_mixed_counts_as_arabic(self):
        assert is_arabic("User: أحمد")


class TestMissingTokens:
    @pytest.mark.parametrize("token", ["N/A", "n/a", "  N/A  ", "NA", "-", ".", "MISSING", "unknown", "null", ""])
    def test_common_missing(self, token):
        assert is_missing_token(token), f"expected {token!r} to be detected as missing"

    def test_arabic_missing(self):
        assert is_missing_token("لا يوجد")
        assert is_missing_token("غير معروف")

    def test_real_value_not_missing(self):
        assert not is_missing_token("Yes")
        assert not is_missing_token("0")          # zero is real data
        assert not is_missing_token("أحمد")


class TestToText:
    def test_none(self):
        assert to_text(None) == ""

    def test_number(self):
        assert to_text(42) == "42"
        assert to_text(3.14) == "3.14"

    def test_string_passthrough(self):
        assert to_text("  spaces  ") == "  spaces  "     # untouched
