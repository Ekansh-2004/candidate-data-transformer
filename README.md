# Candidate Data Transformation Engine

This project is an offline, deterministic Python pipeline for transforming candidate information from recruiter CSV files and resume PDF files into a single canonical JSON profile. It is designed for clarity, maintainability, and explainability rather than machine-learning-based extraction.

## Features

The current implementation includes:

- Multi-source candidate ingestion from recruiter CSV and resume PDF inputs
- Deterministic resume PDF parsing using text extraction and heuristic rules
- Recruiter CSV parsing with alias-based column handling
- A shared canonical candidate model for all parsed sources
- Normalization of emails, phone numbers, dates, and skills
- Deterministic candidate merging across sources
- Provenance tracking for source-based values
- Confidence scoring for merged fields
- Config-driven output projection into JSON
- Final output validation before writing files
- CLI support through Typer

## Project Architecture

The pipeline runs in the following order:

CSV Parser
Resume Parser
↓
Canonical Candidate Model
↓
Normalization
↓
Merge Engine
↓
Confidence + Provenance
↓
Config Projection
↓
Output Validation
↓
Final JSON

Module responsibilities:

- `parsers/csv_parser.py`: parses structured recruiter CSV input into the canonical candidate model.
- `parsers/resume_parser.py`: extracts resume content from PDF files and maps it to the same canonical structure.
- `models/`: defines the canonical Pydantic models for candidate data, provenance, confidence, and output configuration.
- `normalizers/`: standardizes values such as emails, phone numbers, dates, and skill names.
- `merger/engine.py`: merges multiple candidate profiles deterministically while preserving provenance and confidence.
- `projection/`: projects the canonical candidate into a configurable JSON schema.
- `validators/`: validates the projected payload before it is written to disk.
- `pipeline/orchestrator.py`: coordinates the complete pipeline end to end.
- `main.py`: provides the CLI entry point.

## Folder Structure

```text
.
├── main.py
├── requirements.txt
├── README.md
├── configs/
├── merger/
├── models/
├── normalizers/
├── output/
├── parsers/
├── pipeline/
├── projection/
├── sample_inputs/
├── tests/
├── utils/
├── validators/
└── venv/
```

## Installation

This project requires Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Run the CLI with a recruiter CSV file and a resume PDF file:

```bash
python main.py path/to/candidate.csv path/to/resume.pdf
```

Optional arguments:

```bash
python main.py path/to/candidate.csv path/to/resume.pdf \
  --output output/candidate.json \
  --projection-config path/to/projection.json
```

The implemented CLI arguments are:

- `csv_path` (required positional argument)
- `resume_path` (required positional argument)
- `--output` (optional output file path)
- `--projection-config` (optional projection configuration JSON file)

## Configuration

Projection behavior is controlled by a JSON configuration file passed through `--projection-config`.

Supported keys include:

- `output.indent`
- `output.ensure_ascii`
- `output.sort_keys`
- `output.include_empty_fields`
- `field_aliases`
- `include_confidence`
- `include_provenance`
- `include_nested_provenance`

Example configuration:

```json
{
  "output": {
    "include_empty_fields": false,
    "indent": 2,
    "sort_keys": true,
    "ensure_ascii": false
  },
  "field_aliases": {
    "full_name": "name"
  },
  "include_confidence": true,
  "include_provenance": true,
  "include_nested_provenance": false
}
```

## Sample Input

Expected CSV input:

- A recruiter CSV with columns such as `candidate_id`, `full_name`, `email`, `phone`, `location`, `headline`, `summary`, `skills`, `current_company`, `job_title`, `institution`, `degree`, and `field_of_study`
- The parser also supports common aliases for many of these fields

Expected resume input:

- A PDF resume containing plain text content
- The parser looks for common sections such as `Summary`, `Experience`, `Education`, and `Skills`

## Sample Output

Example JSON output produced by the current implementation:

```json
{
  "candidate_id": "cand-001",
  "name": "Ada Lovelace",
  "headline": "Staff Engineer",
  "emails": ["ada@example.com"],
  "phone_numbers": ["+14155550100"],
  "locations": ["London"],
  "experience": [
    {
      "company": "Analytical Engines Ltd",
      "title": "Lead Engineer",
      "start_date": null,
      "end_date": null,
      "location": null,
      "description": "Designed computation workflows"
    }
  ],
  "skills": [
    {
      "name": "Python"
    }
  ],
  "confidence": {
    "full_name": {
      "score": 0.95,
      "level": "high",
      "reason": "Multiple sources agreed on full_name."
    }
  },
  "provenance": {
    "full_name": [
      {
        "source_type": "recruiter_csv",
        "source_name": "candidate.csv",
        "field_path": "full_name"
      }
    ]
  }
}
```

## Design Decisions

- A canonical candidate model is used so all parsers produce the same structure and downstream stages can operate consistently.
- The pipeline is modular so each stage is easy to test and extend independently.
- Deterministic rule-based parsing was chosen to keep the project fully offline and explainable without relying on external services or machine learning.
- Provenance and confidence data are preserved to make merge outcomes and extracted values understandable to downstream users.

## Testing

Run the test suite with:

```bash
pytest
```

## Future Improvements

The following are realistic future extensions and are not part of the current implementation:

- LinkedIn parser
- GitHub parser
- ATS JSON parser
- Optional LLM-based resume extraction

## License

This project is licensed under the MIT License.
