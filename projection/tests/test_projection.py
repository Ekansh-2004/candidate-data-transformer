"""Tests for runtime-configured candidate projection."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from models import (
    Candidate,
    Confidence,
    Education,
    Experience,
    Provenance,
    Skill,
    SourceType,
)
from projection import CandidateProjector, ProjectionConfig, ProjectionConfigLoader


def _make_provenance(field_path: str) -> Provenance:
    """Create a small provenance fixture for projection tests."""
    return Provenance(
        source_type=SourceType.RECRUITER_CSV,
        source_name="recruiter.csv",
        field_path=field_path,
        source_file="recruiter.csv",
    )


def test_projection_loader_reads_runtime_configuration(tmp_path: Path) -> None:
    """The loader should parse projection config from JSON."""
    config_path = tmp_path / "projection.json"
    config_path.write_text(
        json.dumps(
            {
                "output": {"include_empty_fields": True},
                "field_aliases": {"full_name": "name"},
                "include_confidence": False,
                "include_provenance": True,
                "include_nested_provenance": False,
            }
        ),
        encoding="utf-8",
    )

    config = ProjectionConfigLoader().load(config_path)

    assert config.output.include_empty_fields is True
    assert config.field_aliases["full_name"] == "name"
    assert config.include_confidence is False
    assert config.include_nested_provenance is False


def test_projector_projects_canonical_candidate_into_output_schema() -> None:
    """Projection should transform canonical candidate data into JSON-ready output."""
    candidate = Candidate(
        candidate_id="cand-001",
        full_name="Ada Lovelace",
        headline="Staff Engineer",
        emails=["ada@example.com"],
        phone_numbers=["+14155550100"],
        locations=["London"],
        experience=[
            Experience(
                company="Analytical Engines Ltd",
                title="Engineer",
                start_date=date(2020, 1, 1),
                end_date=date(2021, 1, 1),
                highlights=["Built deterministic systems."],
                provenance=[_make_provenance("experience")],
            )
        ],
        education=[
            Education(
                institution="University of London",
                degree="BSc",
                field_of_study="Mathematics",
                start_date=date(2015, 1, 1),
                end_date=date(2019, 1, 1),
                provenance=[_make_provenance("education")],
            )
        ],
        skills=[
            Skill(
                name="Python",
                years_experience=5.0,
                provenance=[_make_provenance("skills")],
            )
        ],
        confidence={
            "full_name": Confidence(score=0.95, level="high", reason="Matched")
        },
        provenance={"full_name": [_make_provenance("full_name")]},
    )
    config = ProjectionConfig(
        field_aliases={"full_name": "name", "phone_numbers": "phones"},
        include_confidence=True,
        include_provenance=True,
        include_nested_provenance=True,
    )

    projected = CandidateProjector().project(candidate, config)

    assert projected["candidate_id"] == "cand-001"
    assert projected["name"] == "Ada Lovelace"
    assert projected["phones"] == ["+14155550100"]
    assert projected["experience"][0]["start_date"] == "2020-01-01"
    assert projected["education"][0]["field_of_study"] == "Mathematics"
    assert projected["skills"][0]["years_experience"] == 5.0
    assert projected["confidence"]["full_name"]["level"] == "high"
    assert projected["provenance"]["full_name"][0]["source_name"] == "recruiter.csv"


def test_projector_defaults_to_clean_consumer_output() -> None:
    """Default projection should omit confidence and provenance for consumer-facing output."""
    candidate = Candidate(
        full_name="Ada Lovelace",
        confidence={
            "full_name": Confidence(score=0.95, level="high", reason="Matched")
        },
        provenance={"full_name": [_make_provenance("full_name")]},
    )

    projected = CandidateProjector().project(candidate, ProjectionConfig())

    assert projected == {"full_name": "Ada Lovelace"}


def test_projector_omits_empty_values_by_default() -> None:
    """Empty candidate fields should be dropped when include_empty_fields is false."""
    candidate = Candidate(full_name="Ada Lovelace")

    projected = CandidateProjector().project(candidate, ProjectionConfig())

    assert projected == {"full_name": "Ada Lovelace"}


def test_projector_projects_simple_skills_as_strings_in_clean_output() -> None:
    """Default projection should emit skills as plain strings even when they carry provenance."""
    candidate = Candidate(
        skills=[
            Skill(name="Python", provenance=[_make_provenance("skills")]),
            Skill(name="React.js", provenance=[_make_provenance("skills")]),
        ]
    )

    projected = CandidateProjector().project(candidate, ProjectionConfig())

    assert projected["skills"] == ["Python", "React.js"]


def test_projector_can_retain_empty_values_when_configured() -> None:
    """Projection should keep empty fields when the output config requests them."""
    candidate = Candidate(full_name="Ada Lovelace")
    config = ProjectionConfig.model_validate(
        {"output": {"include_empty_fields": True}, "include_confidence": False}
    )

    projected = CandidateProjector().project(candidate, config)

    assert projected["full_name"] == "Ada Lovelace"
    assert projected["emails"] == []
    assert projected["experience"] == []
    assert projected["skills"] == []


def test_projector_can_hide_confidence_and_provenance_sections() -> None:
    """Projection flags should control confidence and provenance visibility."""
    candidate = Candidate(
        full_name="Ada Lovelace",
        confidence={
            "full_name": Confidence(score=0.75, level="high", reason="Matched")
        },
        provenance={"full_name": [_make_provenance("full_name")]},
    )
    config = ProjectionConfig(
        include_confidence=False,
        include_provenance=False,
        include_nested_provenance=False,
    )

    projected = CandidateProjector().project(candidate, config)

    assert "confidence" not in projected
    assert "provenance" not in projected


def test_projector_hides_nested_provenance_when_disabled() -> None:
    """Nested records should emit as plain strings when provenance is disabled and no other metadata."""
    candidate = Candidate(
        skills=[Skill(name="Python", provenance=[_make_provenance("skills")])]
    )
    config = ProjectionConfig(include_nested_provenance=False)

    projected = CandidateProjector().project(candidate, config)

    assert projected["skills"] == ["Python"]
