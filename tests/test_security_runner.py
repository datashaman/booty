"""Tests for Security runner."""

import pytest

from booty.security.runner import process_security_job


def test_process_security_job_callable() -> None:
    """process_security_job is callable."""
    assert callable(process_security_job)
