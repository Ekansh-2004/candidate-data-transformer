"""Tests for deterministic resume PDF parsing."""

from __future__ import annotations

import logging
from datetime import date
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


def test_parse_resume_skips_placeholder_headlines_until_meaningful_text(
    tmp_path: Path,
) -> None:
    """The parser should ignore placeholder headline values and keep looking for a real title."""
    pdf_path = tmp_path / "placeholder_headline.pdf"
    _create_pdf(
        pdf_path,
        [
            "Ada Lovelace",
            "—",
            "Staff Software Engineer",
            "ada@example.com",
        ],
    )

    candidate = ResumePdfParser().parse(pdf_path)

    assert candidate.headline == "Staff Software Engineer"


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


def test_parse_resume_extracts_skills_only_from_skills_section(tmp_path: Path) -> None:
    """The parser should only extract skills from the dedicated skills section and ignore other prose."""
    pdf_path = tmp_path / "skills_section_resume.pdf"
    _create_pdf(
        pdf_path,
        [
            "Jane Doe",
            "Software Engineer",
            "jane@example.com",
            "",
            "Technical Skills",
            "Languages: Python, Java, Python",
            "Frameworks & Libraries: Django, React",
            "Databases: PostgreSQL, MySQL",
            "Tools & Platforms: Git, Docker",
            "Concepts: REST APIs, Microservices",
            "",
            "Projects",
            "Smart Inventory Platform",
            "Built an inventory platform that improved speed by 95%.",
            "",
            "Achievements",
            "Won the innovation award for reducing latency by 40%.",
        ],
    )

    candidate = ResumePdfParser().parse(pdf_path)

    assert [skill.name for skill in candidate.skills] == [
        "Python",
        "Java",
        "Django",
        "React",
        "PostgreSQL",
        "MySQL",
        "Git",
        "Docker",
        "REST APIs",
        "Microservices",
    ]


@pytest.mark.parametrize(
    (
        "lines",
        "expected_institution",
        "expected_degree",
        "expected_location",
        "expected_grade",
        "expected_start",
        "expected_end",
    ),
    [
        (
            [
                "The LNM Institute of Information Technology",
                "Jaipur, India",
                "Bachelor of Technology in Computer Science and Engineering",
                "CGPA: 9.36/10",
                "July 2023 - June 2027",
            ],
            "The LNM Institute of Information Technology",
            "Bachelor of Technology",
            "Jaipur, India",
            "CGPA: 9.36/10",
            "2023-07-01",
            "2027-06-01",
        ),
        (
            [
                "University of London",
                "London, UK",
                "BSc in Mathematics",
                "GPA: 3.9",
                "2015 - 2019",
            ],
            "University of London",
            "BSc",
            "London, UK",
            "GPA: 3.9",
            "2015-01-01",
            "2019-01-01",
        ),
        (
            [
                "Massachusetts Institute of Technology | Cambridge, MA, USA",
                "M.S. in Computer Science",
                "GPA: 4.0",
                "2019 - 2021",
            ],
            "Massachusetts Institute of Technology",
            "M.S.",
            "Cambridge, MA, USA",
            "GPA: 4.0",
            "2019-01-01",
            "2021-01-01",
        ),
        (
            [
                "Indian Institute of Technology",
                "Mumbai, India",
                "B.Tech in Electrical Engineering",
                "Percentage: 86%",
                "2018 - 2022",
            ],
            "Indian Institute of Technology",
            "B.Tech",
            "Mumbai, India",
            "Percentage: 86%",
            "2018-01-01",
            "2022-01-01",
        ),
        (
            [
                "Stanford University",
                "Palo Alto, CA",
                "Bachelor of Science, Computer Engineering",
                "Grade: A",
                "2014 - 2018",
            ],
            "Stanford University",
            "Bachelor of Science",
            "Palo Alto, CA",
            "Grade: A",
            "2014-01-01",
            "2018-01-01",
        ),
    ],
)
def test_parse_resume_extracts_education_fields_across_layouts(
    tmp_path: Path,
    lines: list[str],
    expected_institution: str,
    expected_degree: str,
    expected_location: str,
    expected_grade: str,
    expected_start: str,
    expected_end: str,
) -> None:
    """The parser should separate institution, location, degree, grade, and dates across common layouts."""
    pdf_path = tmp_path / "education_layout.pdf"
    _create_pdf(pdf_path, ["Jane Doe", "", "Education", *lines])

    candidate = ResumePdfParser().parse(pdf_path)

    assert len(candidate.education) == 1
    education = candidate.education[0]
    assert education.institution == expected_institution
    assert education.degree == expected_degree
    assert education.location == expected_location
    assert education.grade == expected_grade
    assert education.start_date == date.fromisoformat(expected_start)
    assert education.end_date == date.fromisoformat(expected_end)


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


def test_parse_resume_logs_pdf_open_failures(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """The parser should log extraction failures before re-raising the error."""
    pdf_path = tmp_path / "not_a_pdf.pdf"
    pdf_path.write_text("plain text, not a valid PDF", encoding="utf-8")

    with caplog.at_level(logging.ERROR):
        with pytest.raises(Exception):
            ResumePdfParser().parse(pdf_path)

    assert "Failed to parse resume PDF file" in caplog.text


def test_parse_resume_skips_social_link_lines_for_headline(tmp_path: Path) -> None:
    """The parser should not use GitHub or LinkedIn lines as the candidate headline."""
    pdf_path = tmp_path / "social_headline.pdf"
    _create_pdf(
        pdf_path,
        [
            "Kartik Singh",
            "GitHub: github.com/23kartiksingh",
            "LinkedIn: linkedin.com/in/kartiksingh",
            "Backend Engineer",
            "kartik@example.com",
        ],
    )

    candidate = ResumePdfParser().parse(pdf_path)

    assert candidate.headline == "Backend Engineer"


def test_parse_resume_extracts_multi_word_tech_skills(tmp_path: Path) -> None:
    """The parser should extract multi-word tech skill names like 'REST APIs' and 'Tailwind CSS'."""
    pdf_path = tmp_path / "multi_word_skills.pdf"
    _create_pdf(
        pdf_path,
        [
            "Jane Doe",
            "",
            "Technical Skills",
            "Frameworks: FastAPI, React.js, Node.js",
            "Databases & Tools: MySQL, MongoDB, ChromaDB",
            "Other: REST APIs, Tailwind CSS, Apache Kafka",
        ],
    )

    candidate = ResumePdfParser().parse(pdf_path)
    skill_names = [skill.name for skill in candidate.skills]

    assert "FastAPI" in skill_names
    assert "React.js" in skill_names
    assert "Node.js" in skill_names
    assert "MySQL" in skill_names
    assert "MongoDB" in skill_names
    assert "REST APIs" in skill_names
    assert "Tailwind CSS" in skill_names
    assert "Apache Kafka" in skill_names


def test_parse_resume_treats_nested_category_labels_as_prefixes(
    tmp_path: Path,
) -> None:
    """Category label prefixes like 'Databases & Tools:' should not appear as skills."""
    pdf_path = tmp_path / "category_labels.pdf"
    _create_pdf(
        pdf_path,
        [
            "Jane Doe",
            "",
            "Technical Skills",
            "Languages: Python, Java",
            "Databases & Tools: PostgreSQL, Docker",
            "Soft Skills: Leadership, Communication",
            "Developer Tools: Git, GitHub",
        ],
    )

    candidate = ResumePdfParser().parse(pdf_path)
    skill_names = [skill.name for skill in candidate.skills]

    # Category labels must not appear as skills
    assert "Languages" not in skill_names
    assert "Databases & Tools" not in skill_names
    assert "Soft Skills" not in skill_names
    assert "Developer Tools" not in skill_names
    # Actual skills must be present
    assert "Python" in skill_names
    assert "Java" in skill_names
    assert "Docker" in skill_names
    assert "Leadership" in skill_names


def test_parse_resume_separates_degree_field_and_cgpa(tmp_path: Path) -> None:
    """The parser should split 'B.Tech - CSE; CGPA: 8.63' into degree, field_of_study, and grade."""
    pdf_path = tmp_path / "cgpa_education.pdf"
    _create_pdf(
        pdf_path,
        [
            "Kartik Singh",
            "",
            "Education",
            "The LNM Institute of Information Technology",
            "Jaipur, India",
            "Bachelor of Technology - Computer Science and Engineering; CGPA: 8.63",
            "July 2023 - June 2027",
        ],
    )

    candidate = ResumePdfParser().parse(pdf_path)

    assert len(candidate.education) == 1
    edu = candidate.education[0]
    assert edu.institution == "The LNM Institute of Information Technology"
    assert edu.degree == "Bachelor of Technology"
    assert edu.field_of_study == "Computer Science and Engineering"
    # CGPA should not appear inside the degree field
    assert "CGPA" not in (edu.degree or "")
    assert edu.location == "Jaipur, India"
