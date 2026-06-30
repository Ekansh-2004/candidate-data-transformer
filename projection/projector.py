"""Pure candidate projection logic."""

from __future__ import annotations

from typing import Any

from models import Candidate, Education, Experience, Provenance, Skill

from .config import ProjectionConfig


class CandidateProjector:
    """Project canonical candidates into config-driven output dictionaries."""

    TOP_LEVEL_FIELDS: tuple[str, ...] = (
        "candidate_id",
        "full_name",
        "headline",
        "summary",
        "emails",
        "phone_numbers",
        "locations",
        "experience",
        "education",
        "skills",
    )

    def project(self, candidate: Candidate, config: ProjectionConfig) -> dict[str, Any]:
        """Project a canonical candidate into the configured output schema."""
        projected: dict[str, Any] = {}

        for field_name in self.TOP_LEVEL_FIELDS:
            output_key = config.field_aliases.get(field_name, field_name)
            value = getattr(candidate, field_name)
            projected_value = self._project_field(field_name, value, config)

            if self._should_include_value(projected_value, config):
                projected[output_key] = projected_value

        if config.include_confidence:
            confidence_payload = self._project_confidence(candidate)
            if self._should_include_value(confidence_payload, config):
                projected[config.field_aliases.get("confidence", "confidence")] = (
                    confidence_payload
                )

        if config.include_provenance:
            provenance_payload = self._project_top_level_provenance(candidate)
            if self._should_include_value(provenance_payload, config):
                projected[config.field_aliases.get("provenance", "provenance")] = (
                    provenance_payload
                )

        return projected

    def _project_field(
        self,
        field_name: str,
        value: Any,
        config: ProjectionConfig,
    ) -> Any:
        """Project one field from the canonical model into JSON-ready data."""
        if field_name == "experience":
            return [self._project_experience(item, config) for item in value]
        if field_name == "education":
            return [self._project_education(item, config) for item in value]
        if field_name == "skills":
            return [self._project_skill(item, config) for item in value]
        return value

    def _project_experience(
        self, experience: Experience, config: ProjectionConfig
    ) -> dict[str, Any]:
        """Project one experience entry."""
        payload = {
            "company": experience.company,
            "title": experience.title,
            "start_date": self._serialize_date(experience.start_date),
            "end_date": self._serialize_date(experience.end_date),
            "location": experience.location,
            "description": experience.description,
            "highlights": experience.highlights,
        }
        if config.include_confidence and experience.confidence is not None:
            payload["confidence"] = self._serialize_confidence(experience.confidence)
        if config.include_nested_provenance and experience.provenance:
            payload["provenance"] = [
                self._serialize_provenance(item) for item in experience.provenance
            ]
        return self._drop_empty_values(payload, config)

    def _project_education(
        self, education: Education, config: ProjectionConfig
    ) -> dict[str, Any]:
        """Project one education entry."""
        payload = {
            "institution": education.institution,
            "degree": education.degree,
            "location": education.location,
            "field_of_study": education.field_of_study,
            "start_date": self._serialize_date(education.start_date),
            "end_date": self._serialize_date(education.end_date),
            "grade": education.grade,
        }
        if config.include_confidence and education.confidence is not None:
            payload["confidence"] = self._serialize_confidence(education.confidence)
        if config.include_nested_provenance and education.provenance:
            payload["provenance"] = [
                self._serialize_provenance(item) for item in education.provenance
            ]
        return self._drop_empty_values(payload, config)

    def _project_skill(
        self, skill: Skill, config: ProjectionConfig
    ) -> dict[str, Any] | str:
        """Project one skill entry as a simple string when no extra metadata is needed."""
        should_emit_object = (
            skill.category is not None
            or skill.years_experience is not None
            or (config.include_confidence and skill.confidence is not None)
            or (config.include_nested_provenance and skill.provenance)
        )
        if not should_emit_object:
            return skill.name

        payload = {
            "name": skill.name,
            "category": skill.category,
            "years_experience": skill.years_experience,
        }
        if config.include_confidence and skill.confidence is not None:
            payload["confidence"] = self._serialize_confidence(skill.confidence)
        if config.include_nested_provenance and skill.provenance:
            payload["provenance"] = [
                self._serialize_provenance(item) for item in skill.provenance
            ]
        return self._drop_empty_values(payload, config)

    def _project_confidence(self, candidate: Candidate) -> dict[str, Any]:
        """Project top-level confidence values."""
        return {
            field_path: self._serialize_confidence(confidence)
            for field_path, confidence in candidate.confidence.items()
        }

    def _project_top_level_provenance(self, candidate: Candidate) -> dict[str, Any]:
        """Project top-level provenance values."""
        return {
            field_path: [self._serialize_provenance(item) for item in provenance]
            for field_path, provenance in candidate.provenance.items()
        }

    def _serialize_confidence(self, confidence: Any) -> dict[str, Any]:
        """Convert a confidence model into a JSON-ready dictionary."""
        return {
            "score": confidence.score,
            "level": confidence.level,
            "reason": confidence.reason,
        }

    def _serialize_provenance(self, provenance: Provenance) -> dict[str, Any]:
        """Convert a provenance model into a JSON-ready dictionary."""
        payload = {
            "source_type": provenance.source_type.value,
            "source_name": provenance.source_name,
            "field_path": provenance.field_path,
            "source_record_id": provenance.source_record_id,
            "source_file": provenance.source_file,
            "extracted_value": provenance.extracted_value,
            "notes": provenance.notes,
        }
        return {key: value for key, value in payload.items() if value is not None}

    def _serialize_date(self, value: Any) -> str | None:
        """Convert dates to ISO strings."""
        if value is None:
            return None
        return value.isoformat()

    def _drop_empty_values(
        self, payload: dict[str, Any], config: ProjectionConfig
    ) -> dict[str, Any]:
        """Remove empty and null values when configured to do so."""
        if config.output.include_empty_fields:
            return payload

        return {
            key: value
            for key, value in payload.items()
            if not self._is_empty_value(value)
        }

    def _should_include_value(self, value: Any, config: ProjectionConfig) -> bool:
        """Decide whether a projected field should be included."""
        if config.output.include_empty_fields:
            return True
        return not self._is_empty_value(value)

    def _is_empty_value(self, value: Any) -> bool:
        """Return whether a value should be considered empty in projected output."""
        return value is None or value == "" or value == [] or value == {}
