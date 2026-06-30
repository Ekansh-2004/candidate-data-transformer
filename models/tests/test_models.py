"""Tests for canonical candidate domain models."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from models import (
    Candidate,
    Confidence,
    Education,
    Experience,
    OutputConfig,
    Provenance,
    Skill,
    SourceType,
)


def test_confidence_accepts_matching_score_and_level() -> None:
    """Confidence should accept aligned score and level values."""
    confidence = Confidence(score=0.8, level="high", reason="Matched in both sources")

    assert confidence.score == 0.8
    assert confidence.level == "high"


def test_confidence_rejects_mismatched_level() -> None:
    """Confidence should reject inconsistent score and level combinations."""
    with pytest.raises(ValidationError):
        Confidence(score=0.2, level="high")


def test_provenance_requires_core_fields() -> None:
    """Provenance should preserve core source metadata."""
    provenance = Provenance(
        source_type=SourceType.RECRUITER_CSV,
        source_name="recruiter_upload.csv",
        field_path="full_name",
        source_record_id="row-1",
    )

    assert provenance.source_type is SourceType.RECRUITER_CSV
    assert provenance.field_path == "full_name"


def test_experience_rejects_inverted_date_range() -> None:
    """Experience should reject end dates that precede start dates."""
    with pytest.raises(ValidationError):
        Experience(
            company="Example Corp",
            title="Engineer",
            start_date=date(2023, 1, 1),
            end_date=date(2022, 12, 31),
        )


def test_education_rejects_inverted_date_range() -> None:
    """Education should reject end dates that precede start dates."""
    with pytest.raises(ValidationError):
        Education(
            institution="Example University",
            start_date=date(2022, 1, 1),
            end_date=date(2021, 1, 1),
        )


def test_skill_requires_non_empty_name() -> None:
    """Skill names should not allow blank values."""
    with pytest.raises(ValidationError):
        Skill(name="   ")


def test_candidate_normalizes_emails_and_nests_entities() -> None:
    """Candidate should normalize email casing and retain nested domain entities."""
    candidate = Candidate(
        full_name="Ada Lovelace",
        emails=[" Ada@example.com "],
        experience=[
            Experience(
                company="Analytical Engines Ltd",
                title="Programmer",
                start_date=date(1843, 1, 1),
            )
        ],
        education=[
            Education(
                institution="Self Study",
                degree="Independent Research",
            )
        ],
        skills=[Skill(name="Python")],
        confidence={"skills": Confidence(score=0.75, level="high")},
        provenance={
            "skills": [
                Provenance(
                    source_type=SourceType.RESUME_PDF,
                    source_name="resume.pdf",
                    field_path="skills",
                )
            ]
        },
    )

    assert candidate.emails == ["ada@example.com"]
    assert candidate.experience[0].company == "Analytical Engines Ltd"
    assert candidate.skills[0].name == "Python"


def test_candidate_rejects_invalid_email() -> None:
    """Candidate should reject malformed email values."""
    with pytest.raises(ValidationError):
        Candidate(emails=["invalid-email"])


def test_output_config_validates_indent_range() -> None:
    """OutputConfig should reject unsupported indentation values."""
    with pytest.raises(ValidationError):
        OutputConfig(indent=9)
