"""Projection-specific configuration schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from models import OutputConfig


class ProjectionConfig(BaseModel):
    """Controls how the canonical candidate model is projected into output JSON."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    output: OutputConfig = Field(
        default_factory=OutputConfig,
        description="Serialization-oriented output settings.",
    )
    field_aliases: dict[str, str] = Field(
        default_factory=dict,
        description="Optional top-level output key aliases keyed by canonical field name.",
    )
    include_confidence: bool = Field(
        default=False,
        description="Whether projected output should include top-level confidence data.",
    )
    include_provenance: bool = Field(
        default=False,
        description="Whether projected output should include top-level provenance data.",
    )
    include_nested_provenance: bool = Field(
        default=False,
        description="Whether nested experience, education, and skills should include provenance.",
    )
