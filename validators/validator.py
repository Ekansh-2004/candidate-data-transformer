"""Validation helpers for final projected pipeline output."""

from __future__ import annotations

from typing import Any


def validate_output_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate that the projected payload is a non-empty JSON-compatible dictionary."""
    if not isinstance(payload, dict):
        raise TypeError("Projected output must be a dictionary.")
    if not payload:
        raise ValueError("Projected output cannot be empty.")
    return payload
