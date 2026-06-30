"""Command-line entry point for the candidate transformation pipeline."""

from __future__ import annotations

from pathlib import Path

import typer

from pipeline.orchestrator import CandidateTransformationOrchestrator

app = typer.Typer(add_completion=False)


@app.command()
def run(
    csv_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    resume_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    output_path: Path | None = typer.Option(
        None, "--output", help="Path for the final JSON payload."
    ),
    projection_config_path: Path | None = typer.Option(
        None,
        "--projection-config",
        help="Optional JSON file containing projection settings.",
    ),
) -> None:
    """Run the candidate transformation pipeline from CSV and resume inputs."""
    orchestrator = CandidateTransformationOrchestrator()
    orchestrator.run(
        csv_path=csv_path,
        resume_path=resume_path,
        output_path=output_path,
        projection_config_path=projection_config_path,
    )


if __name__ == "__main__":
    app()
