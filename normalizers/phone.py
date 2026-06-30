"""Phone number normalization utilities."""

from __future__ import annotations

import phonenumbers
from phonenumbers import NumberParseException


class PhoneNormalizer:
    """Normalize phone numbers into E.164 format when possible."""

    def __init__(self, default_region: str = "US") -> None:
        """Create a phone normalizer with a fallback parsing region."""
        self.default_region = default_region

    def normalize(self, value: str | None) -> str | None:
        """Return an E.164 phone number or ``None`` when parsing fails."""
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            return None

        try:
            parsed_number = phonenumbers.parse(normalized, self.default_region)
        except NumberParseException:
            return None

        if not phonenumbers.is_possible_number(parsed_number):
            return None
        if not phonenumbers.is_valid_number(parsed_number):
            return None

        return phonenumbers.format_number(
            parsed_number,
            phonenumbers.PhoneNumberFormat.E164,
        )

    def normalize_many(self, values: list[str]) -> list[str]:
        """Normalize a list of phone numbers while removing duplicates."""
        normalized_values: list[str] = []
        seen: set[str] = set()

        for value in values:
            normalized = self.normalize(value)
            if normalized is None or normalized in seen:
                continue
            seen.add(normalized)
            normalized_values.append(normalized)

        return normalized_values
