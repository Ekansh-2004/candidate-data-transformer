"""Tests for deterministic candidate profile merging."""

from __future__ import annotations

from datetime import date
import logging

import pytest

from merger import CandidateMerger
from models import Candidate, Education, Experience, Provenance, Skill, SourceType


def _make_provenance(
    source_type: SourceType,
    source_name: str,
    field_path: str,
    extracted_value: str | None = None,
) -> Provenance:
    """Create a small provenance fixture for merge tests."""
    return Provenance(
        source_type=source_type,
        source_name=source_name,
        field_path=field_path,
        source_file=source_name,
        extracted_value=extracted_value,
    )


def test_merge_prefers_higher_priority_scalar_source_and_logs_conflicts(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Scalar conflicts should prefer recruiter CSV values over resume values."""
    recruiter = Candidate(
        full_name="Ada Lovelace",
        provenance={
            "full_name": [
                _make_provenance(
                    SourceType.RECRUITER_CSV,
                    "recruiter.csv",
                    "full_name",
                    "Ada Lovelace",
                )
            ]
        },
    )
    resume = Candidate(
        full_name="Augusta Ada King",
        provenance={
            "full_name": [
                _make_provenance(
                    SourceType.RESUME_PDF,
                    "resume.pdf",
                    "full_name",
                    "Augusta Ada King",
                )
            ]
        },
    )

    with caplog.at_level(logging.WARNING):
        merged = CandidateMerger().merge([resume, recruiter])

    assert merged.full_name == "Ada Lovelace"
    assert "Merge conflict for full_name" in caplog.text
    assert merged.confidence["full_name"].score == 0.55


def test_merge_unions_and_normalizes_contact_fields() -> None:
    """Contact collections should be normalized, deduplicated, and ordered."""
    left = Candidate(
        emails=["Ada@Example.com"],
        phone_numbers=["(415) 555-0100"],
        locations=["London"],
        provenance={
            "emails": [_make_provenance(SourceType.RESUME_PDF, "resume.pdf", "emails")],
            "phone_numbers": [
                _make_provenance(SourceType.RESUME_PDF, "resume.pdf", "phone_numbers")
            ],
            "locations": [
                _make_provenance(SourceType.RESUME_PDF, "resume.pdf", "locations")
            ],
        },
    )
    right = Candidate(
        emails=["ada@example.com", "ada.work@example.com"],
        phone_numbers=["+1 415 555 0100"],
        locations=["London", "Remote"],
        provenance={
            "emails": [_make_provenance(SourceType.RECRUITER_CSV, "recruiter.csv", "emails")],
            "phone_numbers": [
                _make_provenance(SourceType.RECRUITER_CSV, "recruiter.csv", "phone_numbers")
            ],
            "locations": [
                _make_provenance(SourceType.RECRUITER_CSV, "recruiter.csv", "locations")
            ],
        },
    )

    merged = CandidateMerger().merge([left, right])

    assert merged.emails == ["ada@example.com", "ada.work@example.com"]
    assert merged.phone_numbers == ["+14155550100"]
    assert merged.locations == ["London", "Remote"]
    assert merged.confidence["emails"].level == "high"


def test_merge_combines_matching_skills_and_preserves_provenance() -> None:
    """Equivalent skills from different sources should merge into one canonical skill."""
    recruiter = Candidate(
        skills=[
            Skill(
                name="python",
                provenance=[
                    _make_provenance(SourceType.RECRUITER_CSV, "recruiter.csv", "skills", "python")
                ],
            )
        ],
        provenance={"skills": [_make_provenance(SourceType.RECRUITER_CSV, "recruiter.csv", "skills")]},
    )
    resume = Candidate(
        skills=[
            Skill(
                name="Py",
                provenance=[
                    _make_provenance(SourceType.RESUME_PDF, "resume.pdf", "skills", "Py")
                ],
            )
        ],
        provenance={"skills": [_make_provenance(SourceType.RESUME_PDF, "resume.pdf", "skills")]},
    )

    merged = CandidateMerger().merge([resume, recruiter])

    assert [skill.name for skill in merged.skills] == ["Python"]
    assert len(merged.skills[0].provenance) == 3
    assert merged.confidence["skills"].score == 0.95


def test_merge_combines_matching_experience_entries() -> None:
    """Matching experience entries should be merged into one richer record."""
    first = Candidate(
        experience=[
            Experience(
                company="Analytical Engines Ltd",
                title="Engineer",
                start_date=date(2020, 1, 1),
                end_date=date(2021, 1, 1),
                description="Built deterministic systems.",
                provenance=[
                    _make_provenance(SourceType.RECRUITER_CSV, "recruiter.csv", "experience")
                ],
            )
        ]
    )
    second = Candidate(
        experience=[
            Experience(
                company="Analytical Engines Ltd",
                title="Engineer",
                start_date=date(2020, 1, 1),
                end_date=date(2021, 1, 1),
                highlights=["Improved reliability."],
                provenance=[
                    _make_provenance(SourceType.RESUME_PDF, "resume.pdf", "experience")
                ],
            )
        ]
    )

    merged = CandidateMerger().merge([second, first])

    assert len(merged.experience) == 1
    assert merged.experience[0].description == "Built deterministic systems."
    assert merged.experience[0].highlights == ["Improved reliability."]
    assert merged.confidence["experience"].score == 0.95


def test_merge_combines_matching_education_entries() -> None:
    """Matching education entries should be merged into one richer record."""
    first = Candidate(
        education=[
            Education(
                institution="University of London",
                degree="BSc",
                field_of_study="Mathematics",
                start_date=date(2015, 1, 1),
                end_date=date(2019, 1, 1),
                provenance=[
                    _make_provenance(SourceType.RESUME_PDF, "resume.pdf", "education")
                ],
            )
        ]
    )
    second = Candidate(
        education=[
            Education(
                institution="University of London",
                degree="BSc",
                field_of_study="Mathematics",
                start_date=date(2015, 1, 1),
                end_date=date(2019, 1, 1),
                grade="GPA: 3.9",
                provenance=[
                    _make_provenance(SourceType.RECRUITER_CSV, "recruiter.csv", "education")
                ],
            )
        ]
    )

    merged = CandidateMerger().merge([first, second])

    assert len(merged.education) == 1
    assert merged.education[0].grade == "GPA: 3.9"
    assert merged.confidence["education"].score == 0.95


def test_merge_adds_derived_provenance_to_every_field() -> None:
    """Every top-level field should carry merge-engine provenance after merging."""
    candidate = Candidate(
        full_name="Ada Lovelace",
        provenance={
            "full_name": [
                _make_provenance(SourceType.RECRUITER_CSV, "recruiter.csv", "full_name")
            ]
        },
    )

    merged = CandidateMerger().merge([candidate])

    assert merged.provenance["full_name"][-1].source_type is SourceType.DERIVED
    assert merged.provenance["emails"][-1].source_type is SourceType.DERIVED
    assert "candidate_merger" == merged.provenance["full_name"][-1].source_name


def test_merge_returns_empty_candidate_when_no_inputs_exist() -> None:
    """Merging no profiles should return an empty canonical candidate."""
    merged = CandidateMerger().merge([])

    assert merged.model_dump() == Candidate().model_dump()
