"""Education model definitions for canonical academic history."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .confidence import Confidence
from .provenance import Provenance


class Education(BaseModel):
    """Represents one education entry for a candidate."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    institution: str = Field(
        ..., min_length=1, description="School or university name."
    )
    degree: str | None = Field(
        default=None,
        min_length=1,
        description="Optional degree name, such as B.Tech or M.S.",
    )
    location: str | None = Field(
        default=None,
        min_length=1,
        description="Optional location associated with the education entry.",
    )
    field_of_study: str | None = Field(
        default=None,
        min_length=1,
        description="Optional major, specialization, or discipline.",
    )
    start_date: date | None = Field(
        default=None,
        description="Optional start date for the education entry.",
    )
    end_date: date | None = Field(
        default=None,
        description="Optional completion or end date for the education entry.",
    )
    grade: str | None = Field(
        default=None,
        min_length=1,
        description="Optional grade, GPA, or percentage.",
    )
    confidence: Confidence | None = Field(
        default=None,
        description="Optional confidence score for the education entry.",
    )
    provenance: list[Provenance] = Field(
        default_factory=list,
        description="Source metadata for the education entry.",
    )

    @model_validator(mode="after")
    def validate_date_range(self) -> "Education":
        """Ensure end dates do not precede start dates."""
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("Education end_date cannot be earlier than start_date.")
        return self
