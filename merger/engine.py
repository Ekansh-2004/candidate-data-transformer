"""Deterministic merge engine for combining multiple candidate profiles."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Callable, Generic, TypeVar

from models import Candidate, Confidence, Education, Experience, Provenance, Skill, SourceType
from normalizers import EmailNormalizer, PhoneNormalizer, SkillCanonicalizer

LOGGER = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass(frozen=True)
class _ValueCandidate(Generic[T]):
    """Internal wrapper for a mergeable value and the profile it came from."""

    value: T
    candidate_index: int
    source_rank: int
    provenance: list[Provenance]


class CandidateMerger:
    """Merge multiple canonical candidate profiles into one deterministic profile.

    Merge rules:
    1. Scalar fields (`candidate_id`, `full_name`, `headline`, `summary`) keep one value.
       The chosen value is the highest-priority non-empty value by source type, then by
       the order of input candidates. Source priority is recruiter CSV, then resume PDF,
       then derived data, then unknown provenance.
    2. When scalar fields contain multiple distinct non-empty values, the chosen winner is
       still deterministic, and the conflict is logged. All source provenance is preserved.
    3. Collection fields (`emails`, `phone_numbers`, `locations`) are merged as ordered
       unions. Earlier higher-priority values are kept first, duplicates are removed.
    4. Skills are canonicalized by name, then merged by canonical skill key. The first
       non-null metadata wins for optional fields, and provenance from all matching skill
       entries is retained.
    5. Experience entries are merged by `(company, title, start_date, end_date)`.
       Matching entries are combined; unmatched entries are appended in deterministic order.
    6. Education entries are merged by `(institution, degree, field_of_study, start_date, end_date)`.
       Matching entries are combined; unmatched entries are appended in deterministic order.
    7. Every merged top-level field receives aggregated provenance from source profiles plus
       one derived provenance note describing that the field was produced by the merge engine.
    8. Every merged top-level field receives a deterministic confidence score.
       Exact agreement across multiple sources produces higher confidence than a single-source
       value, and conflicting values reduce confidence.
    """

    SOURCE_PRIORITY: dict[SourceType, int] = {
        SourceType.RECRUITER_CSV: 0,
        SourceType.RESUME_PDF: 1,
        SourceType.DERIVED: 2,
    }

    def __init__(self) -> None:
        """Create a merger with the normalizers needed for collection fields."""
        self.email_normalizer = EmailNormalizer()
        self.phone_normalizer = PhoneNormalizer()
        self.skill_canonicalizer = SkillCanonicalizer()

    def merge(self, candidates: list[Candidate]) -> Candidate:
        """Merge candidate profiles into one canonical candidate."""
        if not candidates:
            return Candidate()

        candidate_id, candidate_id_provenance, candidate_id_confidence = self._merge_scalar_field(
            candidates, "candidate_id"
        )
        full_name, full_name_provenance, full_name_confidence = self._merge_scalar_field(
            candidates, "full_name"
        )
        headline, headline_provenance, headline_confidence = self._merge_scalar_field(
            candidates, "headline"
        )
        summary, summary_provenance, summary_confidence = self._merge_scalar_field(
            candidates, "summary"
        )

        emails, emails_provenance, emails_confidence = self._merge_emails(candidates)
        phone_numbers, phone_provenance, phone_confidence = self._merge_phone_numbers(candidates)
        locations, locations_provenance, locations_confidence = self._merge_string_list_field(
            candidates,
            field_name="locations",
        )
        skills, skills_provenance, skills_confidence = self._merge_skills(candidates)
        experience, experience_provenance, experience_confidence = self._merge_experience(candidates)
        education, education_provenance, education_confidence = self._merge_education(candidates)

        return Candidate(
            candidate_id=candidate_id,
            full_name=full_name,
            headline=headline,
            summary=summary,
            emails=emails,
            phone_numbers=phone_numbers,
            locations=locations,
            experience=experience,
            education=education,
            skills=skills,
            confidence={
                "candidate_id": candidate_id_confidence,
                "full_name": full_name_confidence,
                "headline": headline_confidence,
                "summary": summary_confidence,
                "emails": emails_confidence,
                "phone_numbers": phone_confidence,
                "locations": locations_confidence,
                "skills": skills_confidence,
                "experience": experience_confidence,
                "education": education_confidence,
            },
            provenance={
                "candidate_id": candidate_id_provenance,
                "full_name": full_name_provenance,
                "headline": headline_provenance,
                "summary": summary_provenance,
                "emails": emails_provenance,
                "phone_numbers": phone_provenance,
                "locations": locations_provenance,
                "skills": skills_provenance,
                "experience": experience_provenance,
                "education": education_provenance,
            },
        )

    def _merge_scalar_field(
        self,
        candidates: list[Candidate],
        field_name: str,
    ) -> tuple[str | None, list[Provenance], Confidence]:
        """Merge one scalar candidate field with deterministic conflict resolution."""
        values = self._collect_scalar_values(candidates, field_name)
        if not values:
            return None, self._derived_only_provenance(field_name), self._build_confidence(
                score=0.0,
                reason=f"No source provided a value for {field_name}.",
            )

        distinct_values = {entry.value for entry in values}
        selected = values[0]
        if len(distinct_values) > 1:
            LOGGER.warning("Merge conflict for %s: %s", field_name, sorted(distinct_values))

        provenance = self._combine_provenance(
            field_path=field_name,
            source_provenance=[entry.provenance for entry in values],
            note=f"Merged scalar field '{field_name}' from {len(values)} source value(s).",
        )
        confidence = self._score_scalar(values, field_name)
        return selected.value, provenance, confidence

    def _merge_emails(
        self, candidates: list[Candidate]
    ) -> tuple[list[str], list[Provenance], Confidence]:
        """Merge email values after deterministic normalization."""
        normalized_values: list[_ValueCandidate[str]] = []
        for index, candidate in enumerate(candidates):
            source_rank = self._candidate_source_rank(candidate)
            provenance = candidate.provenance.get("emails", [])
            for email in self.email_normalizer.normalize_many(candidate.emails):
                normalized_values.append(
                    _ValueCandidate(
                        value=email,
                        candidate_index=index,
                        source_rank=source_rank,
                        provenance=provenance,
                    )
                )
        return self._merge_unique_values("emails", normalized_values)

    def _merge_phone_numbers(
        self, candidates: list[Candidate]
    ) -> tuple[list[str], list[Provenance], Confidence]:
        """Merge phone numbers after deterministic normalization."""
        normalized_values: list[_ValueCandidate[str]] = []
        for index, candidate in enumerate(candidates):
            source_rank = self._candidate_source_rank(candidate)
            provenance = candidate.provenance.get("phone_numbers", [])
            for phone_number in self.phone_normalizer.normalize_many(candidate.phone_numbers):
                normalized_values.append(
                    _ValueCandidate(
                        value=phone_number,
                        candidate_index=index,
                        source_rank=source_rank,
                        provenance=provenance,
                    )
                )
        return self._merge_unique_values("phone_numbers", normalized_values)

    def _merge_string_list_field(
        self,
        candidates: list[Candidate],
        field_name: str,
    ) -> tuple[list[str], list[Provenance], Confidence]:
        """Merge a top-level string-list field as an ordered union."""
        values: list[_ValueCandidate[str]] = []
        for index, candidate in enumerate(candidates):
            source_rank = self._candidate_source_rank(candidate)
            provenance = candidate.provenance.get(field_name, [])
            for value in getattr(candidate, field_name):
                cleaned = value.strip()
                if not cleaned:
                    continue
                values.append(
                    _ValueCandidate(
                        value=cleaned,
                        candidate_index=index,
                        source_rank=source_rank,
                        provenance=provenance,
                    )
                )
        return self._merge_unique_values(field_name, values)

    def _merge_skills(
        self, candidates: list[Candidate]
    ) -> tuple[list[Skill], list[Provenance], Confidence]:
        """Merge skills by canonicalized skill name."""
        grouped: dict[str, list[_ValueCandidate[Skill]]] = {}
        for index, candidate in enumerate(candidates):
            source_rank = self._candidate_source_rank(candidate)
            for skill in self.skill_canonicalizer.normalize_many(candidate.skills):
                key = skill.name.casefold()
                grouped.setdefault(key, []).append(
                    _ValueCandidate(
                        value=skill,
                        candidate_index=index,
                        source_rank=source_rank,
                        provenance=skill.provenance or candidate.provenance.get("skills", []),
                    )
                )

        merged_skills: list[Skill] = []
        all_provenance: list[Provenance] = []
        agreement_groups = 0

        for key in sorted(grouped):
            entries = sorted(grouped[key], key=self._value_sort_key)
            winner = entries[0].value
            provenance = self._combine_provenance(
                field_path="skills",
                source_provenance=[entry.provenance for entry in entries],
                note=f"Merged skill '{winner.name}' from {len(entries)} source value(s).",
            )
            if len(entries) > 1:
                agreement_groups += 1
            merged_skills.append(
                winner.model_copy(
                    update={
                        "category": self._first_non_null([entry.value.category for entry in entries]),
                        "years_experience": self._first_non_null(
                            [entry.value.years_experience for entry in entries]
                        ),
                        "provenance": provenance,
                    }
                )
            )
            all_provenance.extend(provenance)

        confidence = self._score_collection(
            field_name="skills",
            unique_count=len(merged_skills),
            source_occurrence_count=sum(len(entries) for entries in grouped.values()),
            repeated_value_count=agreement_groups,
        )
        return merged_skills, all_provenance or self._derived_only_provenance("skills"), confidence

    def _merge_experience(
        self, candidates: list[Candidate]
    ) -> tuple[list[Experience], list[Provenance], Confidence]:
        """Merge experience entries by employer, title, and date range."""
        return self._merge_model_collection(
            candidates=candidates,
            field_name="experience",
            key_builder=lambda item: (
                item.company.casefold(),
                item.title.casefold(),
                item.start_date,
                item.end_date,
            ),
            merger=self._merge_experience_entry,
        )

    def _merge_education(
        self, candidates: list[Candidate]
    ) -> tuple[list[Education], list[Provenance], Confidence]:
        """Merge education entries by institution, degree, field, and date range."""
        return self._merge_model_collection(
            candidates=candidates,
            field_name="education",
            key_builder=lambda item: (
                item.institution.casefold(),
                (item.degree or "").casefold(),
                (item.field_of_study or "").casefold(),
                item.start_date,
                item.end_date,
            ),
            merger=self._merge_education_entry,
        )

    def _merge_model_collection(
        self,
        candidates: list[Candidate],
        field_name: str,
        key_builder: Callable[[T], tuple[object, ...]],
        merger: Callable[[list[_ValueCandidate[T]]], T],
    ) -> tuple[list[T], list[Provenance], Confidence]:
        """Merge keyed model collections while preserving deterministic order."""
        grouped: dict[tuple[object, ...], list[_ValueCandidate[T]]] = {}
        for index, candidate in enumerate(candidates):
            source_rank = self._candidate_source_rank(candidate)
            for item in getattr(candidate, field_name):
                grouped.setdefault(key_builder(item), []).append(
                    _ValueCandidate(
                        value=item,
                        candidate_index=index,
                        source_rank=source_rank,
                        provenance=item.provenance or candidate.provenance.get(field_name, []),
                    )
                )

        merged_items: list[T] = []
        all_provenance: list[Provenance] = []
        repeated_groups = 0

        for _, entries in sorted(grouped.items(), key=lambda item: self._value_sort_key(item[1][0])):
            entries = sorted(entries, key=self._value_sort_key)
            if len(entries) > 1:
                repeated_groups += 1
            merged_item = merger(entries)
            merged_items.append(merged_item)
            all_provenance.extend(getattr(merged_item, "provenance"))

        confidence = self._score_collection(
            field_name=field_name,
            unique_count=len(merged_items),
            source_occurrence_count=sum(len(entries) for entries in grouped.values()),
            repeated_value_count=repeated_groups,
        )
        return (
            merged_items,
            all_provenance or self._derived_only_provenance(field_name),
            confidence,
        )

    def _merge_experience_entry(self, entries: list[_ValueCandidate[Experience]]) -> Experience:
        """Merge matching experience entries into one canonical experience item."""
        winner = entries[0].value
        provenance = self._combine_provenance(
            field_path="experience",
            source_provenance=[entry.provenance for entry in entries],
            note=(
                f"Merged experience '{winner.title}' at '{winner.company}' "
                f"from {len(entries)} source value(s)."
            ),
        )
        return winner.model_copy(
            update={
                "location": self._first_non_null([entry.value.location for entry in entries]),
                "description": self._first_non_null([entry.value.description for entry in entries]),
                "highlights": self._merge_string_lists(
                    [entry.value.highlights for entry in entries]
                ),
                "provenance": provenance,
            }
        )

    def _merge_education_entry(self, entries: list[_ValueCandidate[Education]]) -> Education:
        """Merge matching education entries into one canonical education item."""
        winner = entries[0].value
        provenance = self._combine_provenance(
            field_path="education",
            source_provenance=[entry.provenance for entry in entries],
            note=(
                f"Merged education '{winner.institution}' from {len(entries)} source value(s)."
            ),
        )
        return winner.model_copy(
            update={
                "degree": self._first_non_null([entry.value.degree for entry in entries]),
                "field_of_study": self._first_non_null(
                    [entry.value.field_of_study for entry in entries]
                ),
                "grade": self._first_non_null([entry.value.grade for entry in entries]),
                "provenance": provenance,
            }
        )

    def _merge_unique_values(
        self,
        field_name: str,
        values: list[_ValueCandidate[str]],
    ) -> tuple[list[str], list[Provenance], Confidence]:
        """Merge scalar collection values as an ordered distinct list."""
        ordered_values = sorted(values, key=self._value_sort_key)
        merged_values: list[str] = []
        seen: set[str] = set()
        source_provenance: list[list[Provenance]] = []
        repeated_value_count = 0

        counts: dict[str, int] = {}
        for item in ordered_values:
            counts[item.value] = counts.get(item.value, 0) + 1
            if item.value in seen:
                continue
            seen.add(item.value)
            merged_values.append(item.value)
            source_provenance.append(item.provenance)

        repeated_value_count = sum(1 for count in counts.values() if count > 1)
        provenance = self._combine_provenance(
            field_path=field_name,
            source_provenance=source_provenance,
            note=f"Merged collection field '{field_name}' into {len(merged_values)} unique value(s).",
        )
        confidence = self._score_collection(
            field_name=field_name,
            unique_count=len(merged_values),
            source_occurrence_count=len(values),
            repeated_value_count=repeated_value_count,
        )
        return merged_values, provenance, confidence

    def _collect_scalar_values(
        self, candidates: list[Candidate], field_name: str
    ) -> list[_ValueCandidate[str]]:
        """Collect and rank non-empty scalar values for a candidate field."""
        values: list[_ValueCandidate[str]] = []
        for index, candidate in enumerate(candidates):
            value = getattr(candidate, field_name)
            if value is None or not value.strip():
                continue
            values.append(
                _ValueCandidate(
                    value=value.strip(),
                    candidate_index=index,
                    source_rank=self._candidate_source_rank(candidate),
                    provenance=candidate.provenance.get(field_name, []),
                )
            )
        return sorted(values, key=self._value_sort_key)

    def _candidate_source_rank(self, candidate: Candidate) -> int:
        """Return the best available source rank for a candidate profile."""
        source_types = [
            provenance.source_type
            for provenance_list in candidate.provenance.values()
            for provenance in provenance_list
        ]
        if not source_types:
            return len(self.SOURCE_PRIORITY)
        return min(self.SOURCE_PRIORITY.get(source_type, len(self.SOURCE_PRIORITY)) for source_type in source_types)

    def _value_sort_key(self, item: _ValueCandidate[object]) -> tuple[int, int]:
        """Sort values by source priority and then by original candidate order."""
        return item.source_rank, item.candidate_index

    def _combine_provenance(
        self,
        field_path: str,
        source_provenance: list[list[Provenance]],
        note: str,
    ) -> list[Provenance]:
        """Combine source provenance with a derived merge provenance entry."""
        flattened: list[Provenance] = []
        seen: set[tuple[object, ...]] = set()
        for provenance_list in source_provenance:
            for provenance in provenance_list:
                key = (
                    provenance.source_type,
                    provenance.source_name,
                    provenance.field_path,
                    provenance.source_record_id,
                    provenance.source_file,
                    provenance.extracted_value,
                    provenance.notes,
                )
                if key in seen:
                    continue
                seen.add(key)
                flattened.append(provenance)

        flattened.append(
            Provenance(
                source_type=SourceType.DERIVED,
                source_name="candidate_merger",
                field_path=field_path,
                source_file="candidate_merger",
                notes=note,
            )
        )
        return flattened

    def _derived_only_provenance(self, field_path: str) -> list[Provenance]:
        """Create fallback provenance for fields absent from all sources."""
        return [
            Provenance(
                source_type=SourceType.DERIVED,
                source_name="candidate_merger",
                field_path=field_path,
                source_file="candidate_merger",
                notes=f"No source values were available for '{field_path}'.",
            )
        ]

    def _score_scalar(
        self, values: list[_ValueCandidate[str]], field_name: str
    ) -> Confidence:
        """Score a scalar field based on agreement across sources."""
        distinct_values = {entry.value for entry in values}
        if len(values) == 1:
            return self._build_confidence(
                score=0.75,
                reason=f"One source provided {field_name}.",
            )
        if len(distinct_values) == 1:
            return self._build_confidence(
                score=0.95,
                reason=f"{len(values)} sources agreed on {field_name}.",
            )
        return self._build_confidence(
            score=0.55,
            reason=f"{len(distinct_values)} conflicting values were found for {field_name}.",
        )

    def _score_collection(
        self,
        field_name: str,
        unique_count: int,
        source_occurrence_count: int,
        repeated_value_count: int,
    ) -> Confidence:
        """Score a collection field from source support and agreement."""
        if unique_count == 0:
            return self._build_confidence(
                score=0.0,
                reason=f"No source provided any values for {field_name}.",
            )
        if source_occurrence_count == unique_count:
            return self._build_confidence(
                score=0.75,
                reason=f"{field_name} values came from single-source observations only.",
            )

        agreement_ratio = repeated_value_count / unique_count
        score = min(0.95, 0.75 + (agreement_ratio * 0.20))
        return self._build_confidence(
            score=score,
            reason=f"{field_name} contained {repeated_value_count} repeated value(s) across sources.",
        )

    def _build_confidence(self, score: float, reason: str) -> Confidence:
        """Create a confidence model with the appropriate level for a score."""
        if score < 0.4:
            level = "low"
        elif score < 0.75:
            level = "medium"
        else:
            level = "high"
        return Confidence(score=round(score, 2), level=level, reason=reason)

    def _first_non_null(self, values: list[T | None]) -> T | None:
        """Return the first non-null value from an ordered list."""
        for value in values:
            if value is not None:
                return value
        return None

    def _merge_string_lists(self, values: list[list[str]]) -> list[str]:
        """Merge nested string lists into a distinct ordered list."""
        merged: list[str] = []
        seen: set[str] = set()
        for items in values:
            for item in items:
                cleaned = item.strip()
                if not cleaned or cleaned in seen:
                    continue
                seen.add(cleaned)
                merged.append(cleaned)
        return merged
