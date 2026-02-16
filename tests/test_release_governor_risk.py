"""Tests for risk scoring from paths touched vs production_sha."""

import unittest.mock

import pytest

from booty.release_governor.risk import compute_risk_class
from booty.test_runner.config import ReleaseGovernorConfig


def _mk_file(filename: str):
    f = unittest.mock.MagicMock()
    f.filename = filename
    return f


def test_empty_diff_returns_low():
    comparison = unittest.mock.MagicMock()
    comparison.files = []
    config = ReleaseGovernorConfig()
    assert compute_risk_class(comparison, config) == "LOW"


def test_no_files_returns_low():
    comparison = unittest.mock.MagicMock()
    comparison.files = None
    config = ReleaseGovernorConfig()
    assert compute_risk_class(comparison, config) == "LOW"


def test_high_risk_path_returns_high():
    comparison = unittest.mock.MagicMock()
    comparison.files = [_mk_file(".github/workflows/foo.yml")]
    config = ReleaseGovernorConfig()
    assert compute_risk_class(comparison, config) == "HIGH"


def test_medium_risk_path_returns_medium():
    comparison = unittest.mock.MagicMock()
    comparison.files = [_mk_file("pyproject.toml")]
    config = ReleaseGovernorConfig()
    assert compute_risk_class(comparison, config) == "MEDIUM"


def test_mixed_paths_returns_highest():
    comparison = unittest.mock.MagicMock()
    comparison.files = [
        _mk_file("pyproject.toml"),
        _mk_file(".github/workflows/verify.yml"),
    ]
    config = ReleaseGovernorConfig()
    assert compute_risk_class(comparison, config) == "HIGH"


def test_unlisted_path_returns_low():
    comparison = unittest.mock.MagicMock()
    comparison.files = [_mk_file("src/foo.py")]
    config = ReleaseGovernorConfig()
    assert compute_risk_class(comparison, config) == "LOW"
