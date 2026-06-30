"""Projection-specific configuration schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from models import OutputConfig


class FieldSpec(BaseModel):
    """Declares one field in a field-level projection config.

    Attributes:
        path:      Output key written to the JSON payload.
        from_:     Source path in the canonical candidate model.  Supports
                   three syntaxes:
                   - ``"full_name"``         – simple attribute
                   - ``"emails[0]"``         – list index (returns None when
                     the list is shorter than the requested index)
                   - ``"skills[].name"``     – array-flatten: collect the named
                     attribute from every element of the list
                   When omitted, ``path`` is used as the source path.
        type:      Expected output type string for documentation / future
                   validation (``"string"``, ``"string[]"``).  Not enforced at
                   runtime in this implementation.
        required:  When ``True`` and the resolved value is missing/None, the
                   ``on_missing`` policy applies.
        normalize: Optional per-field normalization.  Supported values:
                   ``"E164"`` – format the value as an E.164 phone string.
                   ``"canonical"`` – canonicalize the value via SkillCanonicalizer.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        populate_by_name=True,
    )

    path: str = Field(description="Output key written to the projected payload.")
    from_: str | None = Field(
        default=None,
        alias="from",
        description="Source path in the canonical model.  Defaults to ``path`` when absent.",
    )
    type: str | None = Field(
        default=None,
        description="Expected output type (informational only).",
    )
    required: bool = Field(
        default=False,
        description="Whether a missing value should be treated as an error.",
    )
    normalize: Literal["E164", "canonical"] | None = Field(
        default=None,
        description="Optional per-field normalization to apply after resolving the value.",
    )

    @property
    def source_path(self) -> str:
        """Return the effective source path (``from_`` when set, else ``path``)."""
        return self.from_ if self.from_ is not None else self.path


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
    fields: list[FieldSpec] | None = Field(
        default=None,
        description=(
            "When set, enables field-by-field projection mode.  Only the declared fields "
            "are included in the output.  When absent, all canonical fields are projected "
            "using the legacy mode (backward compatible)."
        ),
    )
    on_missing: Literal["omit", "null", "error"] = Field(
        default="omit",
        description=(
            "Policy when a resolved field value is missing or None. "
            "``omit`` – exclude the field (default). "
            "``null`` – include the field with a null value. "
            "``error`` – raise a ValueError (only applies to required fields)."
        ),
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
