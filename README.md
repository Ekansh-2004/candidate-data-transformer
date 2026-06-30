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

By default, the pipeline writes a clean consumer-facing JSON payload containing only the canonical candidate profile. Confidence, provenance, and extraction details are omitted unless you request verbose debug output.

Optional arguments:

```bash
python main.py path/to/candidate.csv path/to/resume.pdf \
  --output output/candidate.json \
  --projection-config path/to/projection.json \
  --debug \
  --debug-output output/candidate.debug.json
```

The implemented CLI arguments are:

- `csv_path` (required positional argument)
- `resume_path` (required positional argument)
- `--output` (optional output file path for the clean JSON payload)
- `--projection-config` (optional projection configuration JSON file)
- `--debug` (write a separate verbose JSON payload with confidence, provenance, and extraction metadata)
- `--debug-output` (optional file path for the verbose debug payload)

## Configuration

Projection behavior is controlled by a JSON configuration file passed through `--projection-config`. The engine operates in two modes:

1. **Legacy Mode (Default):** When `fields` is omitted, all canonical fields are outputted using standard mapping rules (e.g. `field_aliases`, `include_confidence`, `include_provenance`).
2. **Field Projection Mode:** When `fields` is specified, the output is restricted *exactly* to the whitelisted fields mapped from paths in the canonical profile.

### Config Options

* `fields`: An array of field specifications. Each spec supports:
  * `path` (required): The target key name in the output JSON.
  * `from` (optional): Source path in the canonical candidate profile. Defaults to `path`. Supports path resolution:
    * Attribute access: `"full_name"`
    * List index selection: `"emails[0]"` or `"phone_numbers[0]"`
    * Array property flattening: `"skills[].name"`
  * `type` (optional): Expected data type (informational).
  * `required` (optional): Set `true` to make this field mandatory.
  * `normalize` (optional): Transform the output value:
    * `"E164"` – Formats telephone string to E.164.
    * `"canonical"` – Canonicalizes casing and spelling (e.g. `React.js`, `FastAPI`).
* `on_missing`: Action when a field is missing (default `"omit"`):
  * `"omit"` – Exclude the key from the output payload.
  * `"null"` – Render the key as a JSON `null`.
  * `"error"` – Raise a `ValueError` if the field is required.

### Example Configuration

```json
{
  "fields": [
    { "path": "name", "from": "full_name", "type": "string", "required": true },
    { "path": "primary_email", "from": "emails[0]", "type": "string", "required": true },
    { "path": "phone", "from": "phone_numbers[0]", "type": "string", "normalize": "E164" },
    { "path": "skills", "from": "skills[].name", "type": "string[]", "normalize": "canonical" }
  ],
  "on_missing": "null",
  "include_confidence": true
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

The default output is a clean canonical profile for downstream consumers:

```json
{
  "candidate_id": "cand-001",
  "full_name": "Ada Lovelace",
  "headline": "Staff Engineer",
  "emails": ["ada@example.com"],
  "phone_numbers": ["+14155550100"],
  "locations": ["London"],
  "overall_confidence": 0.85,
  "experience": [
    {
      "company": "Analytical Engines Ltd",
      "title": "Lead Engineer",
      "highlights": null,
      "description": "Designed computation workflows"
    }
  ],
  "skills": [
    "Python",
    "SQL"
  ]
}
```

When `--debug` is enabled, the pipeline also writes a separate verbose payload that includes confidence, provenance, and other extraction metadata.

## Design Decisions

- A canonical candidate model is used so all parsers produce the same structure and downstream stages can operate consistently.
- The pipeline is modular so each stage is easy to test and extend independently.
- Deterministic rule-based parsing was chosen to keep the project fully offline and explainable without relying on external services or machine learning.
- The default projection keeps the output clean and consumer-facing, while optional debug output retains provenance and confidence data for investigation and troubleshooting.

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
