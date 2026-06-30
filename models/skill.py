"""Skill model definitions for canonical candidate skill data."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .confidence import Confidence
from .provenance import Provenance


class Skill(BaseModel):
    """Represents a canonical skill entry for a candidate."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(..., min_length=1, description="Normalized skill name.")
    category: str | None = Field(
        default=None,
        min_length=1,
        description="Optional category such as language, framework, or tool.",
    )
    years_experience: float | None = Field(
        default=None,
        ge=0.0,
        description="Optional estimate of time spent using the skill.",
    )
    confidence: Confidence | None = Field(
        default=None,
        description="Optional confidence score for the skill entry.",
    )
    provenance: list[Provenance] = Field(
        default_factory=list,
        description="Source metadata for the skill entry.",
    )

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """Store skill names without surrounding whitespace."""
        return value.strip()
