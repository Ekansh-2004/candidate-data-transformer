"""Configuration schema definitions for output-oriented pipeline settings."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class OutputConfig(BaseModel):
    """Validates simple configuration values for final JSON serialization."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    indent: int = Field(
        default=2,
        ge=0,
        le=8,
        description="Number of spaces to use when pretty-printing JSON output.",
    )
    ensure_ascii: bool = Field(
        default=False,
        description="Whether JSON output should escape non-ASCII characters.",
    )
    sort_keys: bool = Field(
        default=True,
        description="Whether output keys should be serialized in sorted order.",
    )
    include_empty_fields: bool = Field(
        default=False,
        description="Whether fields with empty collections or null values should be retained.",
    )
