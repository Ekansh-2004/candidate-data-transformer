"""Recruiter CSV parser for mapping structured tabular input into the canonical candidate model."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import pandas as pd

from models import Candidate, Education, Experience, Provenance, Skill, SourceType

from .base import CandidateParser

LOGGER = logging.getLogger(__name__)

LIST_SPLIT_PATTERN = re.compile(r"[,\n;/|]+")


class RecruiterCsvParser(CandidateParser):
    """Parses recruiter CSV files into the canonical candidate model."""

    FIELD_ALIASES: dict[str, tuple[str, ...]] = {
        "candidate_id": ("candidate_id", "candidate id", "id", "candidateid"),
        "full_name": ("full_name", "full name", "name", "candidate_name", "candidate name"),
        "headline": ("headline", "title", "current_title", "current title", "role"),
        "summary": ("summary", "profile_summary", "profile summary", "notes"),
        "email": ("email", "email_address", "email address", "primary_email"),
        "phone": ("phone", "phone_number", "phone number", "mobile", "contact_number"),
        "location": ("location", "city", "current_location", "current location"),
        "skills": ("skills", "skill", "skill_set", "skill set", "technologies"),
        "company": ("company", "current_company", "employer", "organization"),
        "job_title": ("job_title", "job title", "designation", "position"),
        "experience_description": (
            "experience_description",
            "experience description",
            "job_description",
            "job description",
        ),
        "institution": ("institution", "college", "school", "university"),
        "degree": ("degree", "qualification", "education"),
        "field_of_study": ("field_of_study", "field of study", "major", "specialization"),
        "grade": ("grade", "gpa", "percentage"),
    }

    def parse(self, source_path: str | Path) -> Candidate:
        """Read a recruiter CSV file and return a canonical candidate model."""
        path = Path(source_path)
        LOGGER.info("Parsing recruiter CSV file: %s", path)

        try:
            dataframe = pd.read_csv(path)
        except Exception:
            LOGGER.exception("Failed to read recruiter CSV file: %s", path)
            raise

        if dataframe.empty:
            LOGGER.warning("Recruiter CSV file is empty: %s", path)
            return Candidate()

        if len(dataframe.index) > 1:
            LOGGER.warning(
                "Recruiter CSV file contains %s rows; using the first row only: %s",
                len(dataframe.index),
                path,
            )

        row = dataframe.iloc[0]
        row_data = self._normalize_row(row)
        candidate = self._build_candidate(row_data=row_data, source_name=path.name)
        LOGGER.info("Parsed recruiter CSV candidate with id=%s", candidate.candidate_id)
        return candidate

    def _build_candidate(self, row_data: dict[str, str], source_name: str) -> Candidate:
        """Create a canonical candidate model from a normalized CSV row."""
        candidate_id = self._get_value(row_data, "candidate_id")
        full_name = self._get_value(row_data, "full_name")
        headline = self._get_value(row_data, "headline")
        summary = self._get_value(row_data, "summary")
        email = self._get_value(row_data, "email")
        phone = self._get_value(row_data, "phone")
        location = self._get_value(row_data, "location")
        skills_text = self._get_value(row_data, "skills")

        experience = self._build_experience(row_data, source_name, candidate_id)
        education = self._build_education(row_data, source_name, candidate_id)
        skills = self._build_skills(skills_text, source_name, candidate_id)

        provenance: dict[str, list[Provenance]] = {}
        self._add_candidate_provenance(
            provenance=provenance,
            source_name=source_name,
            candidate_id=candidate_id,
            field_name="candidate_id",
            value=candidate_id,
        )
        self._add_candidate_provenance(
            provenance=provenance,
            source_name=source_name,
            candidate_id=candidate_id,
            field_name="full_name",
            value=full_name,
        )
        self._add_candidate_provenance(
            provenance=provenance,
            source_name=source_name,
            candidate_id=candidate_id,
            field_name="headline",
            value=headline,
        )
        self._add_candidate_provenance(
            provenance=provenance,
            source_name=source_name,
            candidate_id=candidate_id,
            field_name="summary",
            value=summary,
        )
        self._add_candidate_provenance(
            provenance=provenance,
            source_name=source_name,
            candidate_id=candidate_id,
            field_name="emails",
            value=email,
        )
        self._add_candidate_provenance(
            provenance=provenance,
            source_name=source_name,
            candidate_id=candidate_id,
            field_name="phone_numbers",
            value=phone,
        )
        self._add_candidate_provenance(
            provenance=provenance,
            source_name=source_name,
            candidate_id=candidate_id,
            field_name="locations",
            value=location,
        )
        self._add_candidate_provenance(
            provenance=provenance,
            source_name=source_name,
            candidate_id=candidate_id,
            field_name="skills",
            value=skills_text,
        )

        return Candidate(
            candidate_id=candidate_id,
            full_name=full_name,
            headline=headline,
            summary=summary,
            emails=[email] if email else [],
            phone_numbers=[phone] if phone else [],
            locations=[location] if location else [],
            experience=[experience] if experience else [],
            education=[education] if education else [],
            skills=skills,
            provenance=provenance,
        )

    def _build_experience(
        self,
        row_data: dict[str, str],
        source_name: str,
        candidate_id: str | None,
    ) -> Experience | None:
        """Build an experience entry if the CSV row contains experience data."""
        company = self._get_value(row_data, "company")
        title = self._get_value(row_data, "job_title")
        description = self._get_value(row_data, "experience_description")

        if not company and not title and not description:
            return None

        if not company or not title:
            LOGGER.warning(
                "Skipping partial experience data because company or title is missing for source=%s",
                source_name,
            )
            return None

        return Experience(
            company=company,
            title=title,
            description=description,
            provenance=[
                self._make_provenance(
                    field_path="experience",
                    source_name=source_name,
                    candidate_id=candidate_id,
                    extracted_value=" | ".join(
                        value for value in (company, title, description) if value
                    ),
                )
            ],
        )

    def _build_education(
        self,
        row_data: dict[str, str],
        source_name: str,
        candidate_id: str | None,
    ) -> Education | None:
        """Build an education entry if the CSV row contains education data."""
        institution = self._get_value(row_data, "institution")
        degree = self._get_value(row_data, "degree")
        field_of_study = self._get_value(row_data, "field_of_study")
        grade = self._get_value(row_data, "grade")

        if not institution and not degree and not field_of_study and not grade:
            return None

        if not institution:
            LOGGER.warning(
                "Skipping partial education data because institution is missing for source=%s",
                source_name,
            )
            return None

        return Education(
            institution=institution,
            degree=degree,
            field_of_study=field_of_study,
            grade=grade,
            provenance=[
                self._make_provenance(
                    field_path="education",
                    source_name=source_name,
                    candidate_id=candidate_id,
                    extracted_value=" | ".join(
                        value for value in (institution, degree, field_of_study, grade) if value
                    ),
                )
            ],
        )

    def _build_skills(
        self,
        skills_text: str | None,
        source_name: str,
        candidate_id: str | None,
    ) -> list[Skill]:
        """Build canonical skill entries from a delimited skill string."""
        if not skills_text:
            return []

        skills: list[Skill] = []
        seen_names: set[str] = set()

        for skill_name in self._split_list_value(skills_text):
            normalized_name = skill_name.strip()
            normalized_key = normalized_name.casefold()
            if normalized_key in seen_names:
                continue

            seen_names.add(normalized_key)
            skills.append(
                Skill(
                    name=normalized_name,
                    provenance=[
                        self._make_provenance(
                            field_path="skills",
                            source_name=source_name,
                            candidate_id=candidate_id,
                            extracted_value=normalized_name,
                        )
                    ],
                )
            )

        return skills

    def _normalize_row(self, row: pd.Series) -> dict[str, str]:
        """Convert a pandas row into a normalized string-keyed dictionary."""
        normalized: dict[str, str] = {}
        for column_name, value in row.items():
            if not isinstance(column_name, str):
                continue

            text_value = self._clean_value(value)
            if text_value is None:
                continue

            normalized[self._normalize_column_name(column_name)] = text_value

        return normalized

    def _get_value(self, row_data: dict[str, str], field_name: str) -> str | None:
        """Return the first matching value for a logical field alias set."""
        aliases = self.FIELD_ALIASES[field_name]
        for alias in aliases:
            if alias in row_data:
                return row_data[alias]
        return None

    def _normalize_column_name(self, column_name: str) -> str:
        """Normalize a raw column name for alias-based lookup."""
        return column_name.strip().lower().replace("-", "_")

    def _clean_value(self, value: Any) -> str | None:
        """Convert CSV cell values into clean strings while ignoring missing values."""
        if pd.isna(value):
            return None

        text = str(value).strip()
        if not text:
            return None

        return text

    def _split_list_value(self, value: str) -> list[str]:
        """Split a delimited CSV field into distinct non-empty tokens."""
        return [token.strip() for token in LIST_SPLIT_PATTERN.split(value) if token.strip()]

    def _make_provenance(
        self,
        field_path: str,
        source_name: str,
        candidate_id: str | None,
        extracted_value: str | None,
    ) -> Provenance:
        """Create a provenance entry for recruiter CSV data."""
        return Provenance(
            source_type=SourceType.RECRUITER_CSV,
            source_name=source_name,
            field_path=field_path,
            source_record_id=candidate_id,
            source_file=source_name,
            extracted_value=extracted_value,
        )

    def _add_candidate_provenance(
        self,
        provenance: dict[str, list[Provenance]],
        source_name: str,
        candidate_id: str | None,
        field_name: str,
        value: str | None,
    ) -> None:
        """Attach field-level provenance when a top-level candidate field is populated."""
        if value is None:
            return

        provenance[field_name] = [
            self._make_provenance(
                field_path=field_name,
                source_name=source_name,
                candidate_id=candidate_id,
                extracted_value=value,
            )
        ]
