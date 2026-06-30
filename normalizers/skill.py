"""Skill name canonicalization utilities."""

from __future__ import annotations

import re

from models import Skill

WHITESPACE_PATTERN = re.compile(r"\s+")
NON_ALPHANUMERIC_PATTERN = re.compile(r"[^a-z0-9]+")


class SkillCanonicalizer:
    """Normalize skill names into a consistent canonical vocabulary."""

    CANONICAL_SKILLS: dict[str, str] = {
        "apache kafka": "Apache Kafka",
        "c plus plus": "C++",
        "c++": "C++",
        "chromadb": "ChromaDB",
        "fastapi": "FastAPI",
        "github": "GitHub",
        "golang": "Go",
        "java": "Java",
        "javascript": "JavaScript",
        "js": "JavaScript",
        "langchain": "LangChain",
        "langgraph": "LangGraph",
        "mongodb": "MongoDB",
        "mysql": "MySQL",
        "node": "Node.js",
        "node js": "Node.js",
        "nodejs": "Node.js",
        "pgvector": "pgvector",
        "postgres": "PostgreSQL",
        "postgresql": "PostgreSQL",
        "py": "Python",
        "python": "Python",
        "react": "React.js",
        "react js": "React.js",
        "reactjs": "React.js",
        "rest api": "REST APIs",
        "rest apis": "REST APIs",
        "spring boot": "Spring Boot",
        "tailwind": "Tailwind CSS",
        "tailwind css": "Tailwind CSS",
        "ts": "TypeScript",
        "typescript": "TypeScript",
    }

    def normalize_name(self, value: str | None) -> str | None:
        """Return a canonical skill name or ``None`` when the input is empty."""
        if value is None:
            return None

        normalized = WHITESPACE_PATTERN.sub(" ", value).strip()
        if not normalized:
            return None

        lookup_key = NON_ALPHANUMERIC_PATTERN.sub(" ", normalized.casefold()).strip()
        lookup_key = WHITESPACE_PATTERN.sub(" ", lookup_key).strip()
        canonical_name = self.CANONICAL_SKILLS.get(lookup_key)
        if canonical_name is not None:
            return canonical_name

        if normalized.isupper() and len(normalized) <= 5:
            return normalized

        if any(char.isupper() for char in normalized):
            return normalized

        return normalized.title()

    def normalize(self, skill: Skill) -> Skill:
        """Return a new skill model with a canonicalized skill name."""
        normalized_name = self.normalize_name(skill.name)
        if normalized_name is None:
            return skill

        return skill.model_copy(update={"name": normalized_name})

    def normalize_many(self, skills: list[Skill]) -> list[Skill]:
        """Canonicalize skills while removing duplicate names."""
        normalized_skills: list[Skill] = []
        seen: set[str] = set()

        for skill in skills:
            normalized_skill = self.normalize(skill)
            key = normalized_skill.name.casefold()
            if key in seen:
                continue
            seen.add(key)
            normalized_skills.append(normalized_skill)

        return normalized_skills
