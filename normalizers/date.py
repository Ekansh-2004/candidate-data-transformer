"""Date normalization utilities."""

from __future__ import annotations

from datetime import date, datetime
import re

from dateutil import parser as date_parser


YEAR_PATTERN = re.compile(r"^\d{4}$")


class DateNormalizer:
    """Normalize date-like input into ``datetime.date`` values."""

    def normalize(self, value: str | date | None) -> date | None:
        """Return a normalized date value or ``None`` when parsing fails."""
        if value is None:
            return None
        if isinstance(value, date):
            return value

        normalized = value.strip()
        if not normalized:
            return None

        try:
            if YEAR_PATTERN.fullmatch(normalized):
                return date(int(normalized), 1, 1)
            parsed_date = date_parser.parse(
                normalized,
                default=datetime(1900, 1, 1),
                fuzzy=False,
            )
        except (OverflowError, TypeError, ValueError):
            return None

        if YEAR_PATTERN.search(normalized):
            return parsed_date.date().replace(day=1)
        return parsed_date.date()
