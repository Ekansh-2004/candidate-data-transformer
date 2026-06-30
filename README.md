# Candidate Data Transformation Engine

An offline, deterministic Python project for transforming candidate data from multiple input sources into a single canonical JSON profile.

## Goals

- Keep the implementation simple, readable, and maintainable.
- Parse recruiter CSV data and resume PDF data into one shared candidate model.
- Normalize and merge source data deterministically.
- Preserve provenance and confidence information for explainability.
- Project the canonical profile into validated JSON output.

## Planned Pipeline

1. Parse recruiter CSV input.
2. Parse resume PDF input.
3. Map both sources into the canonical candidate model.
4. Normalize candidate fields.
5. Merge candidate data using explicit rules.
6. Attach confidence and provenance metadata.
7. Project the canonical profile into the final output shape.
8. Validate the final output.
9. Write the resulting JSON file.

## Project Structure

```text
.
├── main.py
├── requirements.txt
├── README.md
├── pipeline/
├── models/
├── parsers/
├── normalizers/
├── merger/
├── projection/
├── validators/
├── utils/
├── configs/
├── tests/
├── sample_inputs/
└── output/
```

## Current Status

This repository currently contains the project skeleton only.

Business logic for parsing, normalization, merging, projection, and validation has not been implemented yet.
