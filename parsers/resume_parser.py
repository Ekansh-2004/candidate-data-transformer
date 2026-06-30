"""Resume PDF parser for deterministic candidate extraction using text heuristics."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from dateutil import parser as date_parser
from rapidfuzz import fuzz, process

try:
    import fitz
except ModuleNotFoundError:  # pragma: no cover - import path depends on PyMuPDF build
    import pymupdf as fitz

from models import Candidate, Education, Experience, Provenance, Skill, SourceType

from .base import CandidateParser

LOGGER = logging.getLogger(__name__)

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?:(?:\+?\d{1,3}[\s().-]*)?(?:\d[\s().-]*){9,15})")
DATE_RANGE_PATTERN = re.compile(
    r"(?P<start>(?:[A-Za-z]{3,9}\s+\d{4})|\d{4})\s*[-–]\s*(?P<end>(?:[A-Za-z]{3,9}\s+\d{4})|\d{4}|Present|Current)",
    re.IGNORECASE,
)
WHITESPACE_PATTERN = re.compile(r"\s+")
SEPARATOR_PATTERN = re.compile(r"\s*[|@]\s*")
LIST_SPLIT_PATTERN = re.compile(r"[,;/|]+")

SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "summary": ("summary", "professional summary", "profile", "about"),
    "experience": (
        "experience",
        "work experience",
        "employment",
        "professional experience",
    ),
    "education": ("education", "academic background", "academics"),
    "skills": (
        "skills",
        "technical skills",
        "core skills",
        "technologies",
        "technical proficiency",
    ),
    "projects": ("projects", "personal projects", "selected projects"),
    "honors": ("honors", "awards", "achievements", "honors and awards"),
    "certifications": ("certifications", "licenses", "certificates"),
}

MAJOR_SECTION_NAMES: frozenset[str] = frozenset(
    {
        "header",
        "summary",
        "experience",
        "education",
        "skills",
        "projects",
        "honors",
        "certifications",
    }
)


class ResumePdfParser(CandidateParser):
    """Parses resume PDFs into the canonical candidate model using deterministic heuristics."""

    def parse(self, source_path: str | Path) -> Candidate:
        """Extract text from a PDF resume and map it to the canonical candidate model."""
        path = Path(source_path)
        LOGGER.info("Parsing resume PDF file: %s", path)

        try:
            text = self._extract_text(path)
        except Exception:
            LOGGER.exception("Failed to parse resume PDF file: %s", path)
            raise

        if not text.strip():
            LOGGER.warning("Resume PDF did not contain extractable text: %s", path)
            return Candidate()

        lines = self._prepare_lines(text)
        sections = self._detect_sections(lines)
        candidate = self._build_candidate(
            lines=lines, sections=sections, source_name=path.name
        )
        LOGGER.info("Parsed resume PDF candidate with name=%s", candidate.full_name)
        return candidate

    def _extract_text(self, path: Path) -> str:
        """Extract concatenated text from all PDF pages."""
        with fitz.open(path) as document:
            return "\n".join(page.get_text("text") for page in document)

    def _prepare_lines(self, text: str) -> list[str]:
        """Normalize extracted text into cleaned logical lines."""
        cleaned_lines: list[str] = []
        for raw_line in text.splitlines():
            line = WHITESPACE_PATTERN.sub(" ", raw_line).strip()
            if not line:
                cleaned_lines.append("")
                continue
            cleaned_lines.append(line)
        return cleaned_lines

    def _detect_sections(self, lines: list[str]) -> dict[str, list[str]]:
        """Group lines into resume sections using exact and fuzzy header detection."""
        sections: dict[str, list[str]] = {"header": []}
        current_section = "header"

        for line in lines:
            if not line:
                if sections.get(current_section):
                    sections[current_section].append("")
                continue

            matched_section = self._match_section_header(line)
            if matched_section:
                current_section = matched_section
                sections.setdefault(current_section, [])
                continue

            sections.setdefault(current_section, []).append(line)

        return sections

    def _match_section_header(self, line: str) -> str | None:
        """Return the canonical section name for a heading-like line."""
        normalized_line = line.strip().lower().rstrip(":")
        if not normalized_line or len(normalized_line) > 40:
            return None

        for section_name, aliases in SECTION_ALIASES.items():
            if normalized_line in aliases:
                return section_name

        all_aliases = {
            alias: section_name
            for section_name, aliases in SECTION_ALIASES.items()
            for alias in aliases
        }
        best_match = process.extractOne(
            normalized_line,
            list(all_aliases.keys()),
            scorer=fuzz.WRatio,
            score_cutoff=88,
        )
        if best_match is None:
            return None

        alias, _, _ = best_match
        return all_aliases[alias]

    def _build_candidate(
        self,
        lines: list[str],
        sections: dict[str, list[str]],
        source_name: str,
    ) -> Candidate:
        """Build a canonical candidate model from extracted resume content."""
        header_lines = [line for line in sections.get("header", []) if line]
        full_name = self._extract_full_name(header_lines)
        headline = self._extract_headline(header_lines, full_name)
        emails = self._extract_emails(lines)
        phone_numbers = self._extract_phone_numbers(lines)
        location = self._extract_location(header_lines)
        summary = self._extract_summary(sections)
        skills = self._extract_skills(sections, source_name)
        experience = self._extract_experience(sections, source_name)
        education = self._extract_education(sections, source_name)

        provenance: dict[str, list[Provenance]] = {}
        self._add_candidate_provenance(provenance, source_name, "full_name", full_name)
        self._add_candidate_provenance(provenance, source_name, "headline", headline)
        self._add_candidate_provenance(provenance, source_name, "summary", summary)
        if emails:
            provenance["emails"] = [
                self._make_provenance("emails", source_name, extracted_value=value)
                for value in emails
            ]
        if phone_numbers:
            provenance["phone_numbers"] = [
                self._make_provenance(
                    "phone_numbers", source_name, extracted_value=value
                )
                for value in phone_numbers
            ]
        if location:
            provenance["locations"] = [
                self._make_provenance(
                    "locations", source_name, extracted_value=location
                )
            ]
        if skills:
            provenance["skills"] = [
                self._make_provenance("skills", source_name, extracted_value=skill.name)
                for skill in skills
            ]

        return Candidate(
            full_name=full_name,
            headline=headline,
            summary=summary,
            emails=emails,
            phone_numbers=phone_numbers,
            locations=[location] if location else [],
            experience=experience,
            education=education,
            skills=skills,
            provenance=provenance,
        )

    def _extract_full_name(self, header_lines: list[str]) -> str | None:
        """Infer the candidate name from the first likely header line."""
        for line in header_lines[:3]:
            if self._looks_like_name(line):
                return line
        return None

    def _extract_headline(
        self, header_lines: list[str], full_name: str | None
    ) -> str | None:
        """Infer a short professional headline from early header lines."""
        for line in header_lines[1:5]:
            if self._is_contact_line(line):
                continue
            if full_name and line == full_name:
                continue
            return line
        return None

    def _extract_location(self, header_lines: list[str]) -> str | None:
        """Infer location from the header block using conservative heuristics."""
        for line in header_lines[:6]:
            if "|" in line:
                for part in [part.strip() for part in line.split("|")]:
                    if self._looks_like_location(part):
                        return part
            if "@" in line or self._contains_phone_number(line):
                continue
            if self._looks_like_location(line):
                return line
        return None

    def _extract_summary(self, sections: dict[str, list[str]]) -> str | None:
        """Return summary text from the summary section when present."""
        summary_lines = [line for line in sections.get("summary", []) if line]
        if not summary_lines:
            return None
        return " ".join(summary_lines)

    def _extract_emails(self, lines: list[str]) -> list[str]:
        """Extract distinct email addresses from the full resume text."""
        emails: list[str] = []
        seen: set[str] = set()
        for line in lines:
            for match in EMAIL_PATTERN.findall(line):
                normalized = match.lower()
                if normalized in seen:
                    continue
                seen.add(normalized)
                emails.append(normalized)
        return emails

    def _extract_phone_numbers(self, lines: list[str]) -> list[str]:
        """Extract distinct phone numbers from the full resume text."""
        phone_numbers: list[str] = []
        seen: set[str] = set()
        for line in lines:
            for match in PHONE_PATTERN.findall(line):
                normalized = self._normalize_phone_number(match)
                if not normalized:
                    continue
                if normalized in seen:
                    continue
                seen.add(normalized)
                phone_numbers.append(normalized)
        return phone_numbers

    def _extract_skills(
        self, sections: dict[str, list[str]], source_name: str
    ) -> list[Skill]:
        """Extract skills only from a dedicated skills section and ignore adjacent prose."""
        skills_section = sections.get("skills", [])
        if not skills_section:
            return []

        skills: list[Skill] = []
        seen: set[str] = set()
        for line in skills_section:
            if not line:
                continue
            normalized_line = line.lstrip("-*• ").strip()
            if not normalized_line:
                continue
            for token in self._extract_skill_tokens(normalized_line):
                cleaned_token = self._clean_skill_token(token)
                if not cleaned_token:
                    continue
                key = cleaned_token.casefold()
                if key in seen:
                    continue
                seen.add(key)
                skills.append(
                    Skill(
                        name=cleaned_token,
                        provenance=[
                            self._make_provenance(
                                "skills", source_name, extracted_value=cleaned_token
                            )
                        ],
                    )
                )
        return skills

    def _extract_experience(
        self, sections: dict[str, list[str]], source_name: str
    ) -> list[Experience]:
        """Extract work experience entries from the experience section."""
        experience_section = sections.get("experience", [])
        if not experience_section:
            return []

        experiences: list[Experience] = []
        for block in self._split_blocks(experience_section):
            experience = self._parse_experience_block(block, source_name)
            if experience is None:
                continue
            experiences.append(experience)
        return experiences

    def _extract_education(
        self, sections: dict[str, list[str]], source_name: str
    ) -> list[Education]:
        """Extract education entries from the education section."""
        education_section = sections.get("education", [])
        if not education_section:
            return []

        education_entries: list[Education] = []
        for block in self._split_blocks(education_section):
            education = self._parse_education_block(block, source_name)
            if education is None:
                continue
            education_entries.append(education)
        return education_entries

    def _parse_experience_block(
        self, block: list[str], source_name: str
    ) -> Experience | None:
        """Parse one experience block using line and separator heuristics."""
        if not block:
            return None

        first_line = block[0].lstrip("-*• ").strip()
        second_line = block[1].strip() if len(block) > 1 else ""

        title, company = self._extract_title_and_company(first_line, second_line)
        start_date, end_date = self._extract_dates_from_lines(block)
        description_lines = [
            line.lstrip("-*• ").strip()
            for line in block[2:]
            if line and not self._line_contains_date_range(line)
        ]
        if len(block) > 1 and second_line and second_line not in description_lines:
            if (
                not self._line_contains_date_range(second_line)
                and second_line != company
            ):
                description_lines.insert(0, second_line)

        description = " ".join(description_lines) if description_lines else None
        highlights = [line for line in description_lines if line]

        if not company or not title:
            LOGGER.warning(
                "Could not parse complete experience block in resume: %s", block
            )
            return None

        return Experience(
            company=company,
            title=title,
            start_date=start_date,
            end_date=end_date,
            description=description,
            highlights=highlights,
            provenance=[
                self._make_provenance(
                    "experience",
                    source_name,
                    extracted_value=" | ".join(block),
                )
            ],
        )

    def _parse_education_block(
        self, block: list[str], source_name: str
    ) -> Education | None:
        """Parse one education block using line and separator heuristics."""
        if not block:
            return None

        institution_line = block[0].lstrip("-*• ").strip()
        institution, location = self._split_institution_and_location(institution_line)
        degree = None
        field_of_study = None
        grade = None
        start_date, end_date = self._extract_dates_from_lines(block)

        for line in block[1:]:
            normalized_line = line.lstrip("-*• ").strip()
            if not normalized_line:
                continue
            if self._line_contains_date_range(normalized_line):
                continue
            if self._looks_like_grade_line(normalized_line):
                grade = normalized_line
                continue
            if location is None and self._looks_like_location(normalized_line):
                location = normalized_line
                continue
            if degree is None and not self._looks_like_institution(normalized_line):
                degree, field_of_study = self._split_degree_and_field(normalized_line)

        if not institution:
            LOGGER.warning("Could not parse education block in resume: %s", block)
            return None

        return Education(
            institution=institution,
            degree=degree,
            location=location,
            field_of_study=field_of_study,
            start_date=start_date,
            end_date=end_date,
            grade=grade,
            provenance=[
                self._make_provenance(
                    "education",
                    source_name,
                    extracted_value=" | ".join(block),
                )
            ],
        )

    def _extract_title_and_company(
        self, first_line: str, second_line: str
    ) -> tuple[str | None, str | None]:
        """Infer title and company from the first two lines of an experience block."""
        parts = [
            part.strip() for part in SEPARATOR_PATTERN.split(first_line) if part.strip()
        ]
        if len(parts) >= 2:
            return parts[0], parts[1]

        at_match = re.match(
            r"(?P<title>.+?)\s+at\s+(?P<company>.+)", first_line, re.IGNORECASE
        )
        if at_match:
            return at_match.group("title").strip(), at_match.group("company").strip()

        if second_line and not self._line_contains_date_range(second_line):
            return first_line, second_line

        return None, None

    def _extract_dates_from_lines(
        self, lines: list[str]
    ) -> tuple[object | None, object | None]:
        """Parse a date range from the provided block lines when possible."""
        for line in lines:
            match = DATE_RANGE_PATTERN.search(line)
            if match is None:
                continue
            start_date = self._parse_date_token(match.group("start"))
            end_token = match.group("end")
            end_date = (
                None
                if end_token.lower() in {"present", "current"}
                else self._parse_date_token(end_token)
            )
            return start_date, end_date
        return None, None

    def _parse_date_token(self, value: str) -> object | None:
        """Convert a year or month-year token into a date object when possible."""
        cleaned = value.strip()
        try:
            if re.fullmatch(r"\d{4}", cleaned):
                return (
                    date_parser.parse(
                        cleaned, default=date_parser.parse("January 1 1900")
                    )
                    .date()
                    .replace(month=1, day=1)
                )
            return (
                date_parser.parse(cleaned, default=date_parser.parse("January 1 1900"))
                .date()
                .replace(day=1)
            )
        except (ValueError, OverflowError):
            return None

    def _split_degree_and_field(self, value: str) -> tuple[str | None, str | None]:
        """Split a degree line into degree and field of study when possible."""
        if not value:
            return None, None
        normalized = value.strip()
        if not normalized:
            return None, None

        if re.search(r"\s+in\s+", normalized, flags=re.IGNORECASE):
            prefix, suffix = re.split(
                r"\s+in\s+", normalized, maxsplit=1, flags=re.IGNORECASE
            )
            return prefix.strip(), suffix.strip()

        if "," in normalized:
            degree, field_of_study = [part.strip() for part in normalized.split(",", 1)]
            if degree and field_of_study:
                return degree, field_of_study

        return normalized, None

    def _split_institution_and_location(
        self, value: str
    ) -> tuple[str | None, str | None]:
        """Split a first-line institution entry that also includes a location."""
        cleaned = value.strip()
        if not cleaned:
            return None, None
        if "|" not in cleaned:
            return cleaned, None

        parts = [part.strip() for part in cleaned.split("|", 1)]
        if len(parts) != 2:
            return cleaned, None
        institution, location = parts
        if not institution or not location:
            return cleaned, None
        if self._looks_like_location(location):
            return institution, location
        return cleaned, None

    def _looks_like_institution(self, value: str) -> bool:
        """Return whether a line looks like an institution name rather than a degree line."""
        if not value:
            return False
        if self._looks_like_grade_line(value):
            return False
        if self._looks_like_location(value):
            return False
        if self._line_contains_date_range(value):
            return False
        if re.search(
            r"\b(?:bachelor|master|b\.sc|bsc|b\.tech|btech|bs|ba|ma|ms|m\.s|m\.tech|phd|mphil)\b",
            value,
            re.IGNORECASE,
        ):
            return False
        return True

    def _looks_like_grade_line(self, value: str) -> bool:
        """Return whether a line looks like a grade or GPA field."""
        normalized = value.strip().lower()
        return normalized.startswith(("gpa", "grade", "cgpa", "percentage", "score"))

    def _split_blocks(self, lines: list[str]) -> list[list[str]]:
        """Split section lines into logical entry blocks using blank lines."""
        blocks: list[list[str]] = []
        current_block: list[str] = []
        for line in lines:
            if not line:
                if current_block:
                    blocks.append(current_block)
                    current_block = []
                continue
            current_block.append(line)
        if current_block:
            blocks.append(current_block)
        return blocks

    def _extract_skill_tokens(self, line: str) -> list[str]:
        """Split one skills line into candidate skill tokens while handling category labels."""
        if ":" in line:
            prefix, suffix = line.split(":", 1)
            if self._looks_like_skill_category(prefix):
                line = suffix.strip()
            else:
                line = line.strip()

        if not line:
            return []

        return [
            token.strip() for token in LIST_SPLIT_PATTERN.split(line) if token.strip()
        ]

    def _looks_like_skill_category(self, value: str) -> bool:
        """Return whether a label looks like a skills category heading."""
        normalized = value.strip().lower()
        return normalized in {
            "languages",
            "frameworks",
            "frameworks & libraries",
            "libraries",
            "databases",
            "tools",
            "tools & platforms",
            "platforms",
            "concepts",
            "skills",
        }

    def _clean_skill_token(self, token: str) -> str | None:
        """Remove noise and keep only plausible skill-like values."""
        cleaned = token.strip()
        if not cleaned:
            return None
        if cleaned.endswith((":", ".")):
            cleaned = cleaned[:-1].strip()
        if not cleaned:
            return None
        if len(cleaned) <= 1:
            return None
        if self._looks_like_sentence(cleaned):
            return None
        if self._contains_percent(cleaned):
            return None
        if self._looks_like_project_title(cleaned):
            return None
        return cleaned

    def _looks_like_sentence(self, value: str) -> bool:
        """Return whether a token resembles prose rather than a skill."""
        if not value:
            return False
        if " " in value:
            parts = value.split()
            if all(re.fullmatch(r"[A-Za-z0-9+/.-]+", part) for part in parts):
                return False
            return True
        return not re.fullmatch(r"[A-Za-z0-9+/.-]+", value)

    def _contains_percent(self, value: str) -> bool:
        """Return whether the token contains a percentage or metric."""
        return "%" in value or re.search(r"\b\d+(?:\.\d+)?%", value) is not None

    def _looks_like_project_title(self, value: str) -> bool:
        """Return whether the token resembles a project title or achievement phrase."""
        if len(value.split()) > 4:
            return True
        if value.lower().startswith(
            ("built", "developed", "created", "improved", "won")
        ):
            return True
        return False

    def _normalize_phone_number(self, value: str) -> str | None:
        """Normalize phone text while keeping the original readable structure."""
        normalized = " ".join(value.strip().split())
        digits_only = re.sub(r"\D", "", normalized)
        if len(digits_only) < 10:
            return None
        return normalized

    def _looks_like_name(self, value: str) -> bool:
        """Check whether a line resembles a person name."""
        if "@" in value or self._contains_phone_number(value):
            return False
        tokens = value.split()
        if not 2 <= len(tokens) <= 4:
            return False
        return all(token[:1].isupper() for token in tokens if token)

    def _looks_like_location(self, value: str) -> bool:
        """Check whether a line resembles a location string."""
        if "@" in value or self._contains_phone_number(value):
            return False
        if len(value.split()) > 5:
            return False
        return "," in value or value.lower().startswith(("remote", "hybrid"))

    def _is_contact_line(self, value: str) -> bool:
        """Check whether a line contains likely contact information."""
        return "@" in value or self._contains_phone_number(value) or "|" in value

    def _contains_phone_number(self, value: str) -> bool:
        """Check whether a line contains a recognizable phone number."""
        return any(
            self._normalize_phone_number(match)
            for match in PHONE_PATTERN.findall(value)
        )

    def _line_contains_date_range(self, value: str) -> bool:
        """Check whether a line contains a supported date range token."""
        return DATE_RANGE_PATTERN.search(value) is not None

    def _make_provenance(
        self,
        field_path: str,
        source_name: str,
        extracted_value: str | None,
    ) -> Provenance:
        """Create a provenance entry for a resume-derived value."""
        return Provenance(
            source_type=SourceType.RESUME_PDF,
            source_name=source_name,
            field_path=field_path,
            source_file=source_name,
            extracted_value=extracted_value,
        )

    def _add_candidate_provenance(
        self,
        provenance: dict[str, list[Provenance]],
        source_name: str,
        field_name: str,
        value: str | None,
    ) -> None:
        """Attach field-level provenance for populated candidate fields."""
        if value is None:
            return
        provenance[field_name] = [
            self._make_provenance(field_name, source_name, extracted_value=value)
        ]
