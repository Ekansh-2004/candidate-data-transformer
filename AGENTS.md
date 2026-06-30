You are a senior Python software engineer.

We are building a production-quality Python project for an internship assignment.

Your goal is to produce clean, maintainable, well-structured code that another engineer can easily understand and extend.

This is an internship assignment, NOT an enterprise framework.

Prioritize:
- simplicity
- readability
- maintainability
- correctness

Avoid unnecessary abstractions.

Do NOT introduce dependency injection, factories, service locators, builder patterns, generic frameworks, or complex design patterns unless there is a very clear benefit.

If two implementations are possible, always choose the simpler one.

--------------------------------------------------------
PROJECT GOAL
--------------------------------------------------------

Build a Candidate Data Transformation Engine.

The system ingests candidate information from multiple sources and produces a single canonical JSON profile.

The pipeline should be deterministic, explainable and modular.

--------------------------------------------------------
CURRENT INPUT SOURCES
--------------------------------------------------------

1. Recruiter CSV (structured)

2. Resume PDF (unstructured)

Future sources such as:

- LinkedIn
- GitHub
- ATS JSON
- Recruiter Notes

should be easy to add later through additional parser modules, but DO NOT implement them now.

--------------------------------------------------------
HARD CONSTRAINTS
--------------------------------------------------------

The project must run completely offline.

Do NOT use:

- OpenAI
- Claude
- Gemini
- Ollama
- HuggingFace inference APIs
- paid APIs
- cloud services
- network calls

No API keys should ever be required.

--------------------------------------------------------
RESUME PARSING
--------------------------------------------------------

Resume parsing must be deterministic.

Use techniques such as:

- PyMuPDF text extraction
- regex
- section header detection
- heuristic parsing
- RapidFuzz where appropriate

Do NOT use machine learning or LLMs.

--------------------------------------------------------
PIPELINE
--------------------------------------------------------

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

The pipeline must be orchestrated by one dedicated orchestrator module.

main.py should only parse CLI arguments and invoke the orchestrator.

--------------------------------------------------------
PROJECT STRUCTURE
--------------------------------------------------------

candidate-transformer/

main.py

requirements.txt

README.md

pipeline/
    orchestrator.py

models/

parsers/
    base.py
    csv_parser.py
    resume_parser.py

normalizers/

merger/

projection/

validators/

utils/

configs/

tests/

sample_inputs/

output/

--------------------------------------------------------
TECH STACK
--------------------------------------------------------

Python 3.11

Pydantic

pandas

PyMuPDF

RapidFuzz

phonenumbers

python-dateutil

Typer

pytest

--------------------------------------------------------
ARCHITECTURE RULES
--------------------------------------------------------

Every parser returns the same Candidate model.

The parser interface should be defined in parsers/base.py.

Modules must be independent.

No module should access another module's internals.

Use composition where appropriate.

Keep functions small.

Use descriptive names.

Use type hints everywhere.

Use docstrings for all public classes and functions.

Avoid duplicate code.

Avoid global state.

Log important events such as:

- parser failures
- normalization fallbacks
- merge conflicts

Projection must ONLY read the canonical profile.

Projection must NEVER access raw source data.

--------------------------------------------------------
CODE STYLE
--------------------------------------------------------

Write production-quality Python.

Readable code is more important than clever code.

Optimize for maintainability.

Do not create empty placeholder classes that serve no purpose.

Only create abstractions that are genuinely useful.

Keep files reasonably small.

--------------------------------------------------------
TESTING
--------------------------------------------------------

Every implementation module should eventually have corresponding pytest tests.

--------------------------------------------------------
FIRST TASK
--------------------------------------------------------

Do NOT implement any business logic yet.

Instead:

1. Produce a short implementation plan.

Include:

- project architecture
- module responsibilities
- dependency graph
- implementation order

2. Wait for confirmation.

3. After confirmation generate ONLY:

- folder structure
- requirements.txt
- README.md
- empty module files
- docstring-only stubs

Do NOT implement parsing.

Do NOT implement normalization.

Do NOT implement merging.

Do NOT implement projection.

Do NOT implement validation.

Stop after creating the project skeleton and wait for the next instruction.