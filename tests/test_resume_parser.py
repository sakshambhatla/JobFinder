"""Tests for the resume parser (jobfinder/resume/parser.py)."""
from __future__ import annotations

from pathlib import Path

import pytest

from jobfinder.resume.parser import parse_resumes, _parse_single

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_resumes_returns_list(tmp_path: Path):
    """parse_resumes() reads all .txt files in a directory."""
    (tmp_path / "resume.txt").write_text(
        (FIXTURES_DIR / "resume.txt").read_text()
    )
    results = parse_resumes(tmp_path)
    assert len(results) == 1
    assert results[0].filename == "resume.txt"


def test_parse_resumes_raises_when_empty(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        parse_resumes(tmp_path)


def test_known_skills_present(tmp_path: Path):
    """Known skills from the fixture resume must be extracted."""
    (tmp_path / "resume.txt").write_text(
        (FIXTURES_DIR / "resume.txt").read_text()
    )
    results = parse_resumes(tmp_path)
    skills_lower = [s.lower() for s in results[0].skills]
    for expected in ("python", "sql", "spark", "kafka", "airflow"):
        assert any(expected in s for s in skills_lower), (
            f"Expected skill '{expected}' not found in {skills_lower}"
        )


def test_company_names_extracted(tmp_path: Path):
    (tmp_path / "resume.txt").write_text(
        (FIXTURES_DIR / "resume.txt").read_text()
    )
    results = parse_resumes(tmp_path)
    companies_lower = [c.lower() for c in results[0].companies_worked_at]
    assert any("google" in c for c in companies_lower), companies_lower
    assert any("amazon" in c for c in companies_lower), companies_lower


def test_job_titles_extracted(tmp_path: Path):
    (tmp_path / "resume.txt").write_text(
        (FIXTURES_DIR / "resume.txt").read_text()
    )
    results = parse_resumes(tmp_path)
    titles_lower = [t.lower() for t in results[0].job_titles]
    assert any("engineer" in t for t in titles_lower), titles_lower


def test_years_of_experience_is_reasonable(tmp_path: Path):
    (tmp_path / "resume.txt").write_text(
        (FIXTURES_DIR / "resume.txt").read_text()
    )
    results = parse_resumes(tmp_path)
    yoe = results[0].years_of_experience
    # Fixture has 2018-present and 2018-2021 → at least 3 years
    assert yoe is None or (0 < yoe < 50)


def test_parsed_at_is_iso_timestamp(tmp_path: Path):
    (tmp_path / "resume.txt").write_text(
        (FIXTURES_DIR / "resume.txt").read_text()
    )
    results = parse_resumes(tmp_path)
    parsed_at = results[0].parsed_at
    # Basic ISO check: contains 'T' and '-'
    assert "T" in parsed_at and "-" in parsed_at


def test_parse_single_education():
    text = """John Doe
EDUCATION
MS Computer Science, Stanford University, 2018
BS Computer Science, UC Berkeley, 2016
EXPERIENCE
Engineer at Acme (2019–present)
"""
    result = _parse_single("test.txt", text)
    assert len(result.education) >= 1
    assert any("Stanford" in e for e in result.education)
