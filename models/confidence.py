"""Confidence model definitions for deterministic candidate data scoring."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ConfidenceLevel = Literal["low", "medium", "high"]


class Confidence(BaseModel):
    """Represents a deterministic confidence assessment for a field or entity."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized confidence score between 0.0 and 1.0.",
    )
    level: ConfidenceLevel = Field(
        ...,
        description="Human-readable confidence bucket aligned with the score.",
    )
    reason: str | None = Field(
        default=None,
        min_length=1,
        description="Optional explanation for how the confidence was assigned.",
    )

    @model_validator(mode="after")
    def validate_level_matches_score(self) -> "Confidence":
        """Ensure the declared confidence level matches the score range."""
        expected_level: ConfidenceLevel
        if self.score < 0.4:
            expected_level = "low"
        elif self.score < 0.75:
            expected_level = "medium"
        else:
            expected_level = "high"

        if self.level != expected_level:
            raise ValueError(
                f"Confidence level '{self.level}' does not match score {self.score:.2f}."
            )
        return self
