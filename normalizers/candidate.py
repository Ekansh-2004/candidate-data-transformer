"""Candidate-level normalization helpers for the pipeline orchestration layer."""

from __future__ import annotations

from models import Candidate

from .date import DateNormalizer
from .email import EmailNormalizer
from .phone import PhoneNormalizer
from .skill import SkillCanonicalizer


class CandidateNormalizer:
    """Normalize parsed candidate data using the existing field-specific normalizers."""

    def __init__(self) -> None:
        """Create the candidate normalizer with the shared field normalizers."""
        self.email_normalizer = EmailNormalizer()
        self.phone_normalizer = PhoneNormalizer()
        self.skill_canonicalizer = SkillCanonicalizer()
        self.date_normalizer = DateNormalizer()

    def normalize(self, candidate: Candidate) -> Candidate:
        """Return a normalized copy of a candidate profile."""
        if not candidate.model_dump():
            return candidate

        normalized_emails = self.email_normalizer.normalize_many(candidate.emails)
        normalized_phone_numbers = self.phone_normalizer.normalize_many(
            candidate.phone_numbers
        )
        normalized_skills = self.skill_canonicalizer.normalize_many(candidate.skills)
        normalized_experience = [
            self._normalize_experience(item) for item in candidate.experience
        ]
        normalized_education = [
            self._normalize_education(item) for item in candidate.education
        ]

        return candidate.model_copy(
            update={
                "emails": normalized_emails,
                "phone_numbers": normalized_phone_numbers,
                "experience": normalized_experience,
                "education": normalized_education,
                "skills": normalized_skills,
            }
        )

    def _normalize_experience(self, experience: object) -> object:
        """Normalize dates for a single experience entry."""
        return experience.model_copy(
            update={
                "start_date": self.date_normalizer.normalize(experience.start_date),
                "end_date": self.date_normalizer.normalize(experience.end_date),
            }
        )

    def _normalize_education(self, education: object) -> object:
        """Normalize dates for a single education entry."""
        return education.model_copy(
            update={
                "start_date": self.date_normalizer.normalize(education.start_date),
                "end_date": self.date_normalizer.normalize(education.end_date),
            }
        )
