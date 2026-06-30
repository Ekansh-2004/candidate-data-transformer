"""Tests for deterministic resume PDF parsing."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

try:
    import fitz
except ModuleNotFoundError:  # pragma: no cover - import path depends on PyMuPDF build
    import pymupdf as fitz

from parsers.resume_parser import ResumePdfParser


def _create_pdf(path: Path, lines: list[str]) -> None:
    """Create a simple text PDF for parser tests."""
    document = fitz.open()
    page = document.new_page()
    y_position = 72
    for line in lines:
        if line:
            page.insert_text((72, y_position), line, fontsize=11)
        y_position += 16
    document.save(path)
    document.close()


def test_parse_resume_extracts_candidate_sections(tmp_path: Path) -> None:
    """The parser should map common resume sections into a candidate profile."""
    pdf_path = tmp_path / "resume.pdf"
    _create_pdf(
        pdf_path,
        [
            "Ada Lovelace",
            "Staff Software Engineer",
            "ada@example.com | +1 415 555 0100 | London, UK",
            "",
            "Professional Summary",
            "Engineer with extensive experience building analytical systems.",
            "",
            "Work Experience",
            "Lead Engineer | Analytical Engines Ltd",
            "Jan 2020 - Present",
            "Built deterministic data processing systems.",
            "Improved reliability for production workflows.",
            "",
            "Education",
            "University of London",
            "BSc in Mathematics",
            "2015 - 2019",
            "GPA: 3.9",
            "",
            "Technical Skills",
            "Python, SQL, Pandas",
        ],
    )

    candidate = ResumePdfParser().parse(pdf_path)

    assert candidate.full_name == "Ada Lovelace"
    assert candidate.headline == "Staff Software Engineer"
    assert candidate.emails == ["ada@example.com"]
    assert candidate.phone_numbers == ["+1 415 555 0100"]
    assert candidate.locations == ["London, UK"]
    assert "analytical systems" in (candidate.summary or "")
    assert [skill.name for skill in candidate.skills] == ["Python", "SQL", "Pandas"]
    assert len(candidate.experience) == 1
    assert candidate.experience[0].company == "Analytical Engines Ltd"
    assert candidate.experience[0].title == "Lead Engineer"
    assert candidate.experience[0].end_date is None
    assert len(candidate.education) == 1
    assert candidate.education[0].institution == "University of London"
    assert candidate.education[0].degree == "BSc"
    assert candidate.education[0].field_of_study == "Mathematics"
    assert "full_name" in candidate.provenance


def test_parse_resume_supports_fuzzy_section_headers(tmp_path: Path) -> None:
    """The parser should handle minor variations in section headings."""
    pdf_path = tmp_path / "fuzzy_headers.pdf"
    _create_pdf(
        pdf_path,
        [
            "Grace Hopper",
            "Principal Engineer",
            "grace@example.com",
            "",
            "Techncal Skills",
            "COBOL | Leadership",
            "",
            "Profesional Experience",
            "Director at Navy Research",
            "2018 - 2020",
            "Led compiler and systems initiatives.",
        ],
    )

    candidate = ResumePdfParser().parse(pdf_path)

    assert [skill.name for skill in candidate.skills] == ["COBOL", "Leadership"]
    assert len(candidate.experience) == 1
    assert candidate.experience[0].company == "Navy Research"
    assert candidate.experience[0].title == "Director"


def test_parse_resume_handles_missing_sections_gracefully(tmp_path: Path) -> None:
    """The parser should return a partial candidate when sections are absent."""
    pdf_path = tmp_path / "minimal_resume.pdf"
    _create_pdf(
        pdf_path,
        [
            "Katherine Johnson",
            "Research Mathematician",
            "katherine@example.com",
        ],
    )

    candidate = ResumePdfParser().parse(pdf_path)

    assert candidate.full_name == "Katherine Johnson"
    assert candidate.headline == "Research Mathematician"
    assert candidate.emails == ["katherine@example.com"]
    assert candidate.skills == []
    assert candidate.experience == []
    assert candidate.education == []


def test_parse_resume_skips_unparseable_experience_blocks_and_logs_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """The parser should skip incomplete experience blocks instead of failing."""
    pdf_path = tmp_path / "partial_experience_resume.pdf"
    _create_pdf(
        pdf_path,
        [
            "Margaret Hamilton",
            "Software Engineer",
            "",
            "Experience",
            "Apollo Guidance Computer",
            "1969 - 1972",
        ],
    )

    with caplog.at_level(logging.WARNING):
        candidate = ResumePdfParser().parse(pdf_path)

    assert candidate.experience == []
    assert "Could not parse complete experience block" in caplog.text


def test_parse_resume_returns_empty_candidate_for_blank_pdf(tmp_path: Path) -> None:
    """The parser should return an empty candidate for PDFs without text."""
    pdf_path = tmp_path / "blank.pdf"
    _create_pdf(pdf_path, [])

    candidate = ResumePdfParser().parse(pdf_path)

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


def test_parse_resume_logs_pdf_open_failures(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """The parser should log extraction failures before re-raising the error."""
    pdf_path = tmp_path / "not_a_pdf.pdf"
    pdf_path.write_text("plain text, not a valid PDF", encoding="utf-8")

    with caplog.at_level(logging.ERROR):
        with pytest.raises(Exception):
            ResumePdfParser().parse(pdf_path)

    assert "Failed to parse resume PDF file" in caplog.text
