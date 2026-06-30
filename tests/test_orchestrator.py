"""Integration tests for the candidate transformation pipeline orchestrator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    import fitz
except ModuleNotFoundError:  # pragma: no cover - import path depends on PyMuPDF build
    import pymupdf as fitz

from pipeline.orchestrator import CandidateTransformationOrchestrator


def _create_pdf(path: Path, lines: list[str]) -> None:
    """Create a simple text PDF for pipeline integration tests."""
    document = fitz.open()
    page = document.new_page()
    y_position = 72
    for line in lines:
        if line:
            page.insert_text((72, y_position), line, fontsize=11)
        y_position += 16
    document.save(path)
    document.close()


def test_orchestrator_runs_full_pipeline_and_writes_json_output(tmp_path: Path) -> None:
    """The orchestrator should parse, normalize, merge, project, validate, and save output."""
    csv_path = tmp_path / "candidate.csv"
    resume_path = tmp_path / "resume.pdf"
    output_path = tmp_path / "output" / "candidate.json"
    config_path = tmp_path / "projection.json"

    csv_path.write_text(
        (
            "candidate_id,full_name,email,phone,location,headline,summary,skills,current_company,"
            "job_title,experience_description,institution,degree,field_of_study,grade\n"
            "cand-001,Ada Lovelace,ada@example.com,+1 555 0100,London,"
            "Staff Engineer,Builds analytical systems,Python; SQL,Analytical Engines Ltd,"
            "Lead Engineer,Designed computation workflows,University of London,BSc,Mathematics,A"
        ),
        encoding="utf-8",
    )
    _create_pdf(
        resume_path,
        [
            "Ada Lovelace",
            "Staff Software Engineer",
            "ada@example.com | +1 415 555 0100 | London, UK",
            "",
            "Professional Summary",
            "Engineer with extensive experience building analytical systems.",
            "",
            "Work Experience",
            "Lead Engineer | Analytical Engines Ltd",
            "Jan 2020 - Present",
            "Built deterministic data processing systems.",
            "",
            "Education",
            "University of London",
            "BSc in Mathematics",
            "2015 - 2019",
            "GPA: 3.9",
            "",
            "Technical Skills",
            "Python, SQL, Pandas",
        ],
    )
    config_path.write_text(
        json.dumps(
            {
                "output": {"include_empty_fields": False},
                "field_aliases": {"full_name": "name"},
                "include_confidence": True,
                "include_provenance": True,
                "include_nested_provenance": False,
            }
        ),
        encoding="utf-8",
    )

    orchestrator = CandidateTransformationOrchestrator()
    payload = orchestrator.run(
        csv_path=csv_path,
        resume_path=resume_path,
        output_path=output_path,
        projection_config_path=config_path,
    )

    assert output_path.exists()
    written_payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert written_payload["name"] == "Ada Lovelace"
    assert written_payload["emails"] == ["ada@example.com"]
    assert written_payload["skills"][0]["name"] in {"Python", "Pandas"}
    assert written_payload["confidence"]["full_name"]["level"] in {
        "high",
        "medium",
        "low",
    }
    assert (
        written_payload["provenance"]["full_name"][0]["source_name"] == "candidate.csv"
    )
    assert payload["name"] == "Ada Lovelace"


def test_orchestrator_writes_debug_payload_when_requested(tmp_path: Path) -> None:
    """The orchestrator should write a clean payload by default and a verbose payload when debug mode is enabled."""
    csv_path = tmp_path / "candidate.csv"
    resume_path = tmp_path / "resume.pdf"
    output_path = tmp_path / "output" / "candidate.json"
    debug_output_path = tmp_path / "output" / "candidate.debug.json"

    csv_path.write_text(
        "candidate_id,full_name,email,skills\n"
        "cand-003,Grace Hopper,grace@example.com,COBOL\n",
        encoding="utf-8",
    )
    _create_pdf(
        resume_path,
        ["Grace Hopper", "grace@example.com", "", "Technical Skills", "COBOL"],
    )

    orchestrator = CandidateTransformationOrchestrator()
    payload = orchestrator.run(
        csv_path=csv_path,
        resume_path=resume_path,
        output_path=output_path,
        debug_mode=True,
        debug_output_path=debug_output_path,
    )

    assert output_path.exists()
    assert debug_output_path.exists()
    assert payload["full_name"] == "Grace Hopper"
    assert "confidence" not in payload
    assert "provenance" not in payload

    debug_payload = json.loads(debug_output_path.read_text(encoding="utf-8"))
    assert debug_payload["full_name"] == "Grace Hopper"
    assert "confidence" in debug_payload
    assert "provenance" in debug_payload


def test_orchestrator_rejects_directory_inputs(tmp_path: Path) -> None:
    """The orchestrator should reject directory paths before attempting file reads."""
    csv_dir = tmp_path / "csv_inputs"
    csv_dir.mkdir()
    resume_path = tmp_path / "resume.pdf"
    _create_pdf(resume_path, ["Grace Hopper"])

    orchestrator = CandidateTransformationOrchestrator()

    with pytest.raises(ValueError, match="CSV input path must point to a file"):
        orchestrator.run(csv_path=csv_dir, resume_path=resume_path)


def test_orchestrator_uses_default_projection_config_when_not_provided(
    tmp_path: Path,
) -> None:
    """The orchestrator should still produce output when no projection config file is supplied."""
    csv_path = tmp_path / "candidate.csv"
    resume_path = tmp_path / "resume.pdf"
    output_path = tmp_path / "candidate.json"

    csv_path.write_text(
        "candidate_id,full_name,email,skills\n"
        "cand-002,Grace Hopper,grace@example.com,COBOL\n",
        encoding="utf-8",
    )
    _create_pdf(
        resume_path,
        ["Grace Hopper", "grace@example.com", "", "Technical Skills", "COBOL"],
    )

    orchestrator = CandidateTransformationOrchestrator()
    payload = orchestrator.run(
        csv_path=csv_path,
        resume_path=resume_path,
        output_path=output_path,
    )

    assert output_path.exists()
    assert payload["full_name"] == "Grace Hopper"
    assert payload["emails"] == ["grace@example.com"]
    assert payload["skills"][0]["name"] == "COBOL"
