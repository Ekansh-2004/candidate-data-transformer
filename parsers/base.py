"""Shared parser interface definitions for canonical candidate ingestion."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from models import Candidate


class CandidateParser(ABC):
    """Abstract interface for parsers that convert one source into a candidate profile."""

    @abstractmethod
    def parse(self, source_path: str | Path) -> Candidate:
        """Parse a source file and return a canonical candidate model."""
