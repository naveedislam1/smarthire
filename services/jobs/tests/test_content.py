"""Unit tests for the pure content helpers."""

from app.publishing.content import (
    breakdown_description,
    extract_keywords,
    extract_skills,
)

DESC = """
Responsibilities:
- Build Python FastAPI services
Requirements:
- Strong Python and PostgreSQL
- Kafka and Docker
Benefits:
- Remote work
"""


def test_breakdown() -> None:
    result = breakdown_description(DESC)
    assert any("FastAPI" in x for x in result["responsibilities"])
    assert any("PostgreSQL" in x for x in result["requirements"])
    assert any("Remote work" in x for x in result["benefits"])


def test_extract_skills() -> None:
    skills = extract_skills(DESC)
    assert {"python", "postgresql", "kafka", "docker"} <= set(skills)
    assert "rust" not in skills


def test_extract_keywords() -> None:
    kws = extract_keywords("python python fastapi the the the")
    assert "python" in kws and "fastapi" in kws
    assert "the" not in kws
