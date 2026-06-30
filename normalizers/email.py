"""Email normalization utilities."""

from __future__ import annotations

import re


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class EmailNormalizer:
    """Normalize email addresses into a deterministic lowercase form."""

    def normalize(self, value: str | None) -> str | None:
        """Return a trimmed, lowercase email address or ``None`` when invalid."""
        if value is None:
            return None

        normalized = value.strip().lower()
        if not normalized:
            return None
        if not EMAIL_PATTERN.match(normalized):
            return None
        return normalized

    def normalize_many(self, values: list[str]) -> list[str]:
        """Normalize a list of email addresses while removing duplicates."""
        normalized_values: list[str] = []
        seen: set[str] = set()

        for value in values:
            normalized = self.normalize(value)
            if normalized is None or normalized in seen:
                continue
            seen.add(normalized)
            normalized_values.append(normalized)

        return normalized_values
