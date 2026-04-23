"""Tests for value normalization."""

from __future__ import annotations

from core.normalizer import is_blank, normalize_value, trim_and_collapse


def test_normalize_lowercases() -> None:
    assert normalize_value("MALE") == "male"


def test_normalize_collapses_whitespace() -> None:
    assert normalize_value("  Very   good  ") == "very good"


def test_normalize_casefolds() -> None:
    # casefold handles German eszett; "ß" → "ss".
    assert normalize_value("Straße") == "strasse"


def test_normalize_strips_tatweel() -> None:
    assert normalize_value("ن\u0640\u0640سبة") == normalize_value("نسبة")


def test_whitespace_variants_match() -> None:
    a = normalize_value(" Male ")
    b = normalize_value("male")
    c = normalize_value("MALE")
    d = normalize_value("male\t")
    assert a == b == c == d == "male"


def test_normalize_non_string_returns_empty() -> None:
    assert normalize_value(None) == ""
    assert normalize_value(123) == ""
    assert normalize_value(True) == ""


def test_normalize_empty_returns_empty() -> None:
    assert normalize_value("") == ""


def test_normalize_preserves_arabic_letter_variants() -> None:
    # Different alef letters must not fold together.
    a = normalize_value("أحمد")
    b = normalize_value("احمد")
    assert a != b


def test_normalize_preserves_punctuation_boundary() -> None:
    # "N/A" and "N.A." must stay distinct — the user can write rules
    # against both if needed.
    assert normalize_value("N/A") != normalize_value("N.A.")


def test_normalize_preserves_leading_zeros() -> None:
    # ID codes often look like "01", "001" — we must not strip the zeros.
    assert normalize_value("01") == "01"
    assert normalize_value("01") != normalize_value("1")


def test_trim_and_collapse_preserves_case() -> None:
    assert trim_and_collapse("  Hello  World  ") == "Hello World"


def test_is_blank_recognises_whitespace() -> None:
    assert is_blank("") is True
    assert is_blank("   ") is True
    assert is_blank(None) is True
    assert is_blank("x") is False
    assert is_blank(0) is False  # numbers aren't "blank text"
