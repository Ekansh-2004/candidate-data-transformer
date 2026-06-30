"""Tests for recruiter CSV parsing into canonical candidate models."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from parsers.csv_parser import RecruiterCsvParser


def test_parse_maps_primary_candidate_fields(tmp_path: Path) -> None:
    """The parser should map common recruiter CSV columns into a Candidate."""
    csv_path = tmp_path / "candidate.csv"
    csv_path.write_text(
        (
            "candidate_id,full_name,email,phone,location,headline,summary,"
            "skills,current_company,job_title,experience_description,"
            "institution,degree,field_of_study,grade\n"
            "cand-001,Ada Lovelace,ada@example.com,+1 555 0100,London,"
            "Staff Engineer,Builds analytical systems,"
            "\"Python; SQL; Python\",Analytical Engines Ltd,Lead Engineer,"
            "Designed computation workflows,University of London,BSc,Mathematics,A\n"
        ),
        encoding="utf-8",
    )

    candidate = RecruiterCsvParser().parse(csv_path)

    assert candidate.candidate_id == "cand-001"
    assert candidate.full_name == "Ada Lovelace"
    assert candidate.emails == ["ada@example.com"]
    assert candidate.phone_numbers == ["+1 555 0100"]
    assert candidate.locations == ["London"]
    assert candidate.headline == "Staff Engineer"
    assert candidate.summary == "Builds analytical systems"
    assert [skill.name for skill in candidate.skills] == ["Python", "SQL"]
    assert len(candidate.experience) == 1
    assert candidate.experience[0].company == "Analytical Engines Ltd"
    assert candidate.experience[0].title == "Lead Engineer"
    assert len(candidate.education) == 1
    assert candidate.education[0].institution == "University of London"
    assert "full_name" in candidate.provenance
    assert candidate.provenance["emails"][0].source_name == "candidate.csv"


def test_parse_supports_column_aliases(tmp_path: Path) -> None:
    """The parser should support common alternate recruiter CSV headers."""
    csv_path = tmp_path / "alias_headers.csv"
    csv_path.write_text(
        (
            "id,name,email_address,mobile,current_location,title,skill_set\n"
            "cand-002,Grace Hopper,grace@example.com,+1 555 0101,New York,Principal Engineer,"
            "\"COBOL, Leadership\"\n"
        ),
        encoding="utf-8",
    )

    candidate = RecruiterCsvParser().parse(csv_path)

    assert candidate.candidate_id == "cand-002"
    assert candidate.full_name == "Grace Hopper"
    assert candidate.headline == "Principal Engineer"
    assert candidate.locations == ["New York"]
    assert [skill.name for skill in candidate.skills] == ["COBOL", "Leadership"]


def test_parse_handles_missing_values_gracefully(tmp_path: Path) -> None:
    """The parser should return a partial candidate instead of failing on blank cells."""
    csv_path = tmp_path / "missing_values.csv"
    csv_path.write_text(
        "candidate_id,full_name,email,skills,current_company,job_title,institution\n"
        "cand-003,,,,,,\n",
        encoding="utf-8",
    )

    candidate = RecruiterCsvParser().parse(csv_path)

    assert candidate.candidate_id == "cand-003"
    assert candidate.full_name is None
    assert candidate.emails == []
    assert candidate.skills == []
    assert candidate.experience == []
    assert candidate.education == []


def test_parse_uses_first_row_when_multiple_candidates_exist(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """The parser should log and use the first row when multiple rows are present."""
    csv_path = tmp_path / "multiple_rows.csv"
    csv_path.write_text(
        (
            "candidate_id,full_name,email\n"
            "cand-004,First Candidate,first@example.com\n"
            "cand-005,Second Candidate,second@example.com\n"
        ),
        encoding="utf-8",
    )

    with caplog.at_level(logging.WARNING):
        candidate = RecruiterCsvParser().parse(csv_path)

    assert candidate.candidate_id == "cand-004"
    assert "using the first row only" in caplog.text


def test_parse_skips_partial_experience_and_logs_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """The parser should skip invalid partial experience rows without failing."""
    csv_path = tmp_path / "partial_experience.csv"
    csv_path.write_text(
        "candidate_id,full_name,current_company\ncand-006,Katherine Johnson,NASA\n",
        encoding="utf-8",
    )

    with caplog.at_level(logging.WARNING):
        candidate = RecruiterCsvParser().parse(csv_path)

    assert candidate.experience == []
    assert "Skipping partial experience data" in caplog.text


def test_parse_returns_empty_candidate_for_empty_csv(tmp_path: Path) -> None:
    """The parser should return an empty candidate for header-only CSV files."""
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("candidate_id,full_name,email\n", encoding="utf-8")

    candidate = RecruiterCsvParser().parse(csv_path)

    assert candidate.model_dump() == {
        "candidate_id": None,
        "full_name": None,
        "headline": None,
        "summary": None,
        "emails": [],
        "phone_numbers": [],
        "locations": [],
        "experience": [],
        "education": [],
        "skills": [],
        "confidence": {},
        "provenance": {},
    }
