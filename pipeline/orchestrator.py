"""Orchestrator module for sequencing parsing, normalization, merging, projection, and validation."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from merger import CandidateMerger
from models import Candidate
from normalizers import CandidateNormalizer
from parsers.csv_parser import RecruiterCsvParser
from parsers.resume_parser import ResumePdfParser
from projection import CandidateProjector, ProjectionConfig, ProjectionConfigLoader
from validators import validate_output_payload

LOGGER = logging.getLogger(__name__)


class CandidateTransformationOrchestrator:
    """Coordinate the candidate transformation pipeline from input files to JSON output."""

    def __init__(self) -> None:
        """Create the orchestrator with the parser, normalizer, merger, and projector dependencies."""
        self.csv_parser = RecruiterCsvParser()
        self.resume_parser = ResumePdfParser()
        self.normalizer = CandidateNormalizer()
        self.merger = CandidateMerger()
        self.config_loader = ProjectionConfigLoader()
        self.projector = CandidateProjector()

    def run(
        self,
        csv_path: str | Path,
        resume_path: str | Path,
        output_path: str | Path | None = None,
        projection_config_path: str | Path | None = None,
    ) -> dict[str, Any]:
        """Execute the full pipeline and write the projected JSON payload to disk."""
        try:
            LOGGER.info("Starting candidate transformation pipeline")
            csv_source = self._resolve_input_path(csv_path, "CSV")
            resume_source = self._resolve_input_path(resume_path, "resume")

            self._read_input_files(csv_source, resume_source)
            csv_candidate = self._parse_csv(csv_source)
            resume_candidate = self._parse_resume(resume_source)
            normalized_candidates = [
                self._normalize_candidate(csv_candidate),
                self._normalize_candidate(resume_candidate),
            ]

            LOGGER.info("Merging parsed candidate profiles")
            merged_candidate = self.merger.merge(normalized_candidates)

            LOGGER.info("Applying projection configuration")
            projection_config = self.config_loader.load(projection_config_path)
            projected_payload = self.projector.project(
                merged_candidate, projection_config
            )

            LOGGER.info("Validating projected output")
            validated_payload = validate_output_payload(projected_payload)

            output_target = self._resolve_output_path(output_path, projection_config)
            self._write_output(validated_payload, output_target, projection_config)
            LOGGER.info("Candidate transformation pipeline completed successfully")
            return validated_payload
        except (
            Exception
        ) as exc:  # pragma: no cover - exercised through integration behavior
            LOGGER.exception("Candidate transformation pipeline failed")
            raise RuntimeError("Candidate transformation pipeline failed") from exc

    def _resolve_input_path(self, path: str | Path, label: str) -> Path:
        """Validate and return an input path for the requested source type."""
        candidate_path = Path(path)
        if not candidate_path.exists():
            raise FileNotFoundError(
                f"{label} input file does not exist: {candidate_path}"
            )
        return candidate_path

    def _read_input_files(self, csv_path: Path, resume_path: Path) -> None:
        """Read both source files into memory to confirm they are accessible."""
        for source_path, label in ((csv_path, "CSV"), (resume_path, "resume")):
            LOGGER.info("Reading %s input file: %s", label, source_path)
            with source_path.open("rb") as handle:
                handle.read(1)

    def _parse_csv(self, csv_path: Path) -> Candidate:
        """Parse the recruiter CSV input into the canonical model."""
        LOGGER.info("Parsing CSV candidate input")
        return self.csv_parser.parse(csv_path)

    def _parse_resume(self, resume_path: Path) -> Candidate:
        """Parse the resume PDF input into the canonical model."""
        LOGGER.info("Parsing resume candidate input")
        return self.resume_parser.parse(resume_path)

    def _normalize_candidate(self, candidate: Candidate) -> Candidate:
        """Normalize the parsed candidate using the existing normalizer modules."""
        return self.normalizer.normalize(candidate)

    def _resolve_output_path(
        self,
        output_path: str | Path | None,
        projection_config: ProjectionConfig,
    ) -> Path:
        """Resolve the target output path and ensure its parent directory exists."""
        if output_path is None:
            return Path("output/candidate.json")

        target_path = Path(output_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        return target_path

    def _write_output(
        self,
        payload: dict[str, Any],
        output_path: Path,
        projection_config: ProjectionConfig,
    ) -> None:
        """Serialize the validated payload to disk using the projection configuration."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(
                payload,
                handle,
                indent=projection_config.output.indent,
                ensure_ascii=projection_config.output.ensure_ascii,
                sort_keys=projection_config.output.sort_keys,
            )
            handle.write("\n")
