"""Tests for focused field normalizers."""

from __future__ import annotations

from datetime import date

from models import Skill
from normalizers import DateNormalizer, EmailNormalizer, PhoneNormalizer, SkillCanonicalizer


def test_email_normalizer_lowercases_and_trims() -> None:
    """Email normalization should lowercase, trim, and deduplicate addresses."""
    normalizer = EmailNormalizer()

    assert normalizer.normalize(" Ada@Example.COM ") == "ada@example.com"
    assert normalizer.normalize_many(
        [" Ada@Example.COM ", "ada@example.com", "invalid-email"]
    ) == ["ada@example.com"]


def test_email_normalizer_returns_none_for_invalid_values() -> None:
    """Invalid email values should be dropped instead of raising."""
    normalizer = EmailNormalizer()

    assert normalizer.normalize(None) is None
    assert normalizer.normalize("   ") is None
    assert normalizer.normalize("invalid-email") is None


def test_phone_normalizer_formats_numbers_in_e164() -> None:
    """Phone normalization should convert valid numbers into E.164 format."""
    normalizer = PhoneNormalizer(default_region="US")

    assert normalizer.normalize("(415) 555-0100") == "+14155550100"
    assert normalizer.normalize_many(
        ["(415) 555-0100", "+1 415 555 0100", "not-a-number"]
    ) == ["+14155550100"]


def test_phone_normalizer_returns_none_for_invalid_values() -> None:
    """Invalid phone values should be discarded cleanly."""
    normalizer = PhoneNormalizer(default_region="US")

    assert normalizer.normalize(None) is None
    assert normalizer.normalize("   ") is None
    assert normalizer.normalize("12345") is None


def test_date_normalizer_parses_dates_consistently() -> None:
    """Date normalization should support year-only and month-year formats."""
    normalizer = DateNormalizer()

    assert normalizer.normalize("2024") == date(2024, 1, 1)
    assert normalizer.normalize("Jan 2024") == date(2024, 1, 1)
    assert normalizer.normalize("2024-06-15") == date(2024, 6, 15)
    assert normalizer.normalize(date(2020, 5, 1)) == date(2020, 5, 1)


def test_date_normalizer_returns_none_for_unparseable_values() -> None:
    """Invalid date-like values should return None."""
    normalizer = DateNormalizer()

    assert normalizer.normalize(None) is None
    assert normalizer.normalize("   ") is None
    assert normalizer.normalize("not-a-date") is None


def test_skill_canonicalizer_maps_aliases_and_deduplicates() -> None:
    """Skill canonicalization should map aliases and remove duplicates."""
    canonicalizer = SkillCanonicalizer()
    skills = [
        Skill(name="python"),
        Skill(name="Py"),
        Skill(name="node js"),
        Skill(name="SQL"),
    ]

    normalized_skills = canonicalizer.normalize_many(skills)

    assert [skill.name for skill in normalized_skills] == [
        "Python",
        "Node.js",
        "SQL",
    ]


def test_skill_canonicalizer_title_cases_unknown_skills() -> None:
    """Unknown skills should still be normalized into a readable form."""
    canonicalizer = SkillCanonicalizer()

    assert canonicalizer.normalize_name("machine learning") == "Machine Learning"
    assert canonicalizer.normalize_name(None) is None
