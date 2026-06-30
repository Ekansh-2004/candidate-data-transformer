"""Provenance model definitions for tracking candidate data origins."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class SourceType(str, Enum):
    """Enumerates supported source categories for candidate data."""

    RECRUITER_CSV = "recruiter_csv"
    RESUME_PDF = "resume_pdf"
    DERIVED = "derived"


class Provenance(BaseModel):
    """Captures where a field or entity value originated from."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    source_type: SourceType = Field(
        ...,
        description="Category of source that contributed the value.",
    )
    source_name: str = Field(
        ...,
        min_length=1,
        description="Human-readable name for the source input.",
    )
    field_path: str = Field(
        ...,
        min_length=1,
        description="Canonical path for the field this provenance entry describes.",
    )
    source_record_id: str | None = Field(
        default=None,
        min_length=1,
        description="Optional source-side record identifier, such as a CSV row key.",
    )
    source_file: str | None = Field(
        default=None,
        min_length=1,
        description="Optional source filename that contributed the value.",
    )
    extracted_value: str | None = Field(
        default=None,
        min_length=1,
        description="Optional raw or normalized value observed in the source.",
    )
    notes: str | None = Field(
        default=None,
        min_length=1,
        description="Optional explanatory note about extraction or derivation.",
    )
