"""Tests for planner risk classification."""

import pytest

from booty.planner.risk import classify_risk_from_paths


class TestEmptyTouchPaths:
    def test_empty_returns_high(self) -> None:
        r, d = classify_risk_from_paths([])
        assert r == "HIGH"
        assert d == []

    def test_none_returns_high(self) -> None:
        r, d = classify_risk_from_paths(None)
        assert r == "HIGH"
        assert d == []


class TestHighRiskPaths:
    def test_github_workflows(self) -> None:
        r, d = classify_risk_from_paths([".github/workflows/ci.yml"])
        assert r == "HIGH"
        assert ".github/workflows/ci.yml" in d

    def test_infra(self) -> None:
        r, d = classify_risk_from_paths(["infra/terraform/main.tf"])
        assert r == "HIGH"

    def test_migrations(self) -> None:
        r, d = classify_risk_from_paths(["alembic/migrations/001_add_users.py"])
        assert r == "HIGH"

    def test_lockfiles(self) -> None:
        r, d = classify_risk_from_paths(["package-lock.json"])
        assert r == "HIGH"

    def test_deploy_scripts(self) -> None:
        r, d = classify_risk_from_paths(["scripts/deploy.sh"])
        assert r == "HIGH"


class TestMediumRiskPaths:
    def test_pyproject(self) -> None:
        r, d = classify_risk_from_paths(["pyproject.toml"])
        assert r == "MEDIUM"

    def test_requirements(self) -> None:
        r, d = classify_risk_from_paths(["requirements.txt"])
        assert r == "MEDIUM"

    def test_package_json(self) -> None:
        r, d = classify_risk_from_paths(["package.json"])
        assert r == "MEDIUM"


class TestLowRiskPaths:
    def test_src_file(self) -> None:
        r, d = classify_risk_from_paths(["src/foo.py"])
        assert r == "LOW"

    def test_test_file(self) -> None:
        r, d = classify_risk_from_paths(["tests/test_x.py"])
        assert r == "LOW"


class TestExcludedFromRisk:
    def test_readme(self) -> None:
        r, d = classify_risk_from_paths(["README.md"])
        assert r == "LOW"

    def test_docs(self) -> None:
        r, d = classify_risk_from_paths(["docs/foo.md"])
        assert r == "LOW"


class TestHighestWins:
    def test_mix_high_medium_returns_high(self) -> None:
        r, d = classify_risk_from_paths(
            ["src/foo.py", ".github/workflows/ci.yml", "pyproject.toml"]
        )
        assert r == "HIGH"
        assert ".github/workflows/ci.yml" in d

    def test_risk_drivers_contains_matching_paths(self) -> None:
        r, d = classify_risk_from_paths(["pyproject.toml", "requirements.txt"])
        assert r == "MEDIUM"
        assert len(d) >= 1
        assert "pyproject.toml" in d or "requirements.txt" in d
