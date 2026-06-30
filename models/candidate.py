from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .confidence import Confidence
from .education import Education
from .experience import Experience
from .provenance import Provenance
from .skill import Skill

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Candidate(BaseModel):
    """Represents the canonical candidate profile shared across pipeline stages."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    candidate_id: str | None = Field(
        default=None,
        min_length=1,
        description="Optional stable identifier for the canonical candidate profile.",
    )
    full_name: str | None = Field(
        default=None,
        min_length=1,
        description="Candidate's full normalized name.",
    )
    headline: str | None = Field(
        default=None,
        min_length=1,
        description="Optional professional headline or short title.",
    )
    summary: str | None = Field(
        default=None,
        min_length=1,
        description="Optional free-text profile summary.",
    )
    emails: list[str] = Field(
        default_factory=list,
        description="Email addresses associated with the candidate.",
    )
    phone_numbers: list[str] = Field(
        default_factory=list,
        description="Phone numbers associated with the candidate.",
    )
    locations: list[str] = Field(
        default_factory=list,
        description="Location strings associated with the candidate.",
    )
    experience: list[Experience] = Field(
        default_factory=list,
        description="Canonical work experience entries.",
    )
    education: list[Education] = Field(
        default_factory=list,
        description="Canonical education entries.",
    )
    skills: list[Skill] = Field(
        default_factory=list,
        description="Canonical skill entries.",
    )
    confidence: dict[str, Confidence] = Field(
        default_factory=dict,
        description="Optional confidence scores keyed by canonical field path.",
    )
    provenance: dict[str, list[Provenance]] = Field(
        default_factory=dict,
        description="Optional provenance entries keyed by canonical field path.",
    )

    @field_validator("emails")
    @classmethod
    def validate_emails(cls, values: list[str]) -> list[str]:
        """Validate email address"""
        normalized_values: list[str] = []
        for value in values:
            normalized_value = value.strip().lower()
            if not EMAIL_PATTERN.match(normalized_value):
                raise ValueError(f"Invalid email address: {value}")
            normalized_values.append(normalized_value)
        return normalized_values

    @field_validator("phone_numbers", "locations")
    @classmethod
    def strip_list_values(cls, values: list[str]) -> list[str]:
        """Normalize simple string lists by trimming each value."""
        return [value.strip() for value in values]
