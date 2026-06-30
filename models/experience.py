"""Experience model definitions for canonical employment history."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .confidence import Confidence
from .provenance import Provenance


class Experience(BaseModel):
    """Represents one employment or project experience entry for a candidate."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    company: str = Field(..., min_length=1, description="Employer or organization name.")
    title: str = Field(..., min_length=1, description="Job title or role name.")
    start_date: date | None = Field(
        default=None,
        description="Optional start date for the experience entry.",
    )
    end_date: date | None = Field(
        default=None,
        description="Optional end date for the experience entry.",
    )
    location: str | None = Field(
        default=None,
        min_length=1,
        description="Optional work location associated with the role.",
    )
    description: str | None = Field(
        default=None,
        min_length=1,
        description="Optional summary description of the role.",
    )
    highlights: list[str] = Field(
        default_factory=list,
        description="Optional bullet-style accomplishments for the role.",
    )
    confidence: Confidence | None = Field(
        default=None,
        description="Optional confidence score for the experience entry.",
    )
    provenance: list[Provenance] = Field(
        default_factory=list,
        description="Source metadata for the experience entry.",
    )

    @model_validator(mode="after")
    def validate_date_range(self) -> "Experience":
        """Ensure end dates do not precede start dates."""
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("Experience end_date cannot be earlier than start_date.")
        return self
