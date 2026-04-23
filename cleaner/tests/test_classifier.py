"""Tests for value classification."""

from __future__ import annotations

from core.classifier import classify_value, is_likely_missing
from core.normalizer import normalize_value
from models.schemas import ValueClass


def _classify(raw: str, *, frequency: int = 2, in_headers: bool = False) -> ValueClass:
    return classify_value(
        raw, normalize_value(raw), frequency=frequency, appears_in_headers=in_headers,
    )


# --------------------------------------------------------------------------- #

def test_missing_token_detected() -> None:
    assert _classify("N/A") == ValueClass.MISSING_TOKEN
    assert _classify("missing") == ValueClass.MISSING_TOKEN
    assert _classify("--") == ValueClass.MISSING_TOKEN
    assert _classify("?") == ValueClass.MISSING_TOKEN
    assert _classify(".") == ValueClass.MISSING_TOKEN


def test_missing_token_survives_whitespace_and_case() -> None:
    # Normalization handles the messy input; classifier uses the normalized form.
    assert _classify("  N/A  ") == ValueClass.MISSING_TOKEN
    assert _classify("NA") == ValueClass.MISSING_TOKEN
    assert _classify("missing") == ValueClass.MISSING_TOKEN


def test_numeric_strings_classified() -> None:
    assert _classify("42") == ValueClass.NUMERIC_LIKE
    assert _classify("-3.14") == ValueClass.NUMERIC_LIKE
    assert _classify("1,234,567") == ValueClass.NUMERIC_LIKE


def test_numeric_like_does_not_match_alphanumeric() -> None:
    assert _classify("A1") != ValueClass.NUMERIC_LIKE


def test_date_like_patterns() -> None:
    assert _classify("2024-01-15") == ValueClass.DATE_LIKE
    assert _classify("01/15/2024") == ValueClass.DATE_LIKE
    assert _classify("2024/01/15") == ValueClass.DATE_LIKE


def test_mixed_alnum_code() -> None:
    assert _classify("Q3-2024") == ValueClass.MIXED_ALNUM
    assert _classify("SKU-001") == ValueClass.MIXED_ALNUM


def test_header_label_wins_over_text_category() -> None:
    # A header labelled "Gender" should come back as HEADER_LABEL.
    assert _classify("Gender", in_headers=True) == ValueClass.HEADER_LABEL


def test_missing_token_wins_over_header_label() -> None:
    # A literal "N/A" in a header row is still a missing token — the user
    # probably wants to clean it, not ignore it.
    assert _classify("N/A", in_headers=True) == ValueClass.MISSING_TOKEN


def test_repeated_short_text_is_text_category() -> None:
    assert _classify("male", frequency=20) == ValueClass.TEXT_CATEGORY
    assert _classify("Very good", frequency=5) == ValueClass.TEXT_CATEGORY


def test_singleton_short_text_is_low_frequency() -> None:
    assert _classify("once-off", frequency=1) == ValueClass.LOW_FREQUENCY


def test_long_text_is_free_text() -> None:
    long = "This is a paragraph-style free-text response that goes on past sixty characters easily."
    assert _classify(long, frequency=3) == ValueClass.FREE_TEXT


def test_is_likely_missing_public_helper() -> None:
    assert is_likely_missing("n/a") is True
    assert is_likely_missing("male") is False
