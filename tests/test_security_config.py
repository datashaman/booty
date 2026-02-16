"""Tests for SecurityConfig and related config loading."""

import os

import pytest
from pydantic import ValidationError

from booty.test_runner.config import (
    BootyConfigV1,
    SecurityConfig,
    apply_security_env_overrides,
    load_booty_config_from_content,
)


class TestSecurityConfig:
    """SecurityConfig validation tests."""

    def test_accepts_valid_config(self) -> None:
        """SecurityConfig accepts enabled, fail_severity, sensitive_paths."""
        c = SecurityConfig(
            enabled=True,
            fail_severity="high",
            sensitive_paths=[".github/workflows/**", "infra/**"],
        )
        assert c.enabled is True
        assert c.fail_severity == "high"
        assert ".github/workflows/**" in c.sensitive_paths

    def test_rejects_unknown_keys(self) -> None:
        """SecurityConfig rejects unknown keys (extra='forbid')."""
        with pytest.raises(Exception):  # ValidationError
            SecurityConfig(enabled=True, unknown_key="x")

    def test_defaults(self) -> None:
        """SecurityConfig has expected defaults."""
        c = SecurityConfig()
        assert c.enabled is True
        assert c.fail_severity == "high"
        assert ".github/workflows/**" in c.sensitive_paths
        assert c.secret_scanner == "gitleaks"
        assert c.secret_scan_exclude == []

    def test_secret_scanner_default_and_trufflehog(self) -> None:
        """secret_scanner defaults to gitleaks; trufflehog parses correctly."""
        c = SecurityConfig()
        assert c.secret_scanner == "gitleaks"
        c2 = SecurityConfig(secret_scanner="trufflehog")
        assert c2.secret_scanner == "trufflehog"

    def test_secret_scan_exclude(self) -> None:
        """secret_scan_exclude with paths parses correctly."""
        c = SecurityConfig(secret_scan_exclude=["tests/fixtures/**", "vendor/**"])
        assert "tests/fixtures/**" in c.secret_scan_exclude
        assert "vendor/**" in c.secret_scan_exclude

    def test_invalid_secret_scanner(self) -> None:
        """Invalid secret_scanner value raises ValidationError."""
        with pytest.raises(ValidationError):
            SecurityConfig(secret_scanner="invalid")


class TestBootyConfigV1Security:
    """BootyConfigV1 with security block."""

    def test_with_valid_security_block(self) -> None:
        """BootyConfigV1 with valid security block loads."""
        yaml = """
schema_version: 1
test_command: pytest
security:
  enabled: true
  fail_severity: high
"""
        c = load_booty_config_from_content(yaml)
        assert isinstance(c, BootyConfigV1)
        assert c.security is not None
        assert c.security.enabled is True
        assert c.security.fail_severity == "high"

    def test_with_invalid_security_block_unknown_keys(self) -> None:
        """BootyConfigV1 with security block containing unknown keys loads with security=None."""
        yaml = """
schema_version: 1
test_command: pytest
security:
  enabled: false
  unknown_key: x
"""
        c = load_booty_config_from_content(yaml)
        assert isinstance(c, BootyConfigV1)
        assert c.security is None

    def test_without_security_key(self) -> None:
        """BootyConfigV1 without security key loads with security=None."""
        yaml = """
schema_version: 1
test_command: pytest
"""
        c = load_booty_config_from_content(yaml)
        assert isinstance(c, BootyConfigV1)
        assert c.security is None


class TestApplySecurityEnvOverrides:
    """apply_security_env_overrides tests."""

    def test_secuity_enabled_false(self) -> None:
        """SECURITY_ENABLED=false disables security."""
        os.environ["SECURITY_ENABLED"] = "false"
        c = SecurityConfig(enabled=True)
        c2 = apply_security_env_overrides(c)
        assert c2.enabled is False
        del os.environ["SECURITY_ENABLED"]

    def test_security_enabled_true(self) -> None:
        """SECURITY_ENABLED=true enables security."""
        os.environ["SECURITY_ENABLED"] = "true"
        c = SecurityConfig(enabled=False)
        c2 = apply_security_env_overrides(c)
        assert c2.enabled is True
        del os.environ["SECURITY_ENABLED"]

    def test_security_fail_severity_override(self) -> None:
        """SECURITY_FAIL_SEVERITY overrides fail_severity."""
        os.environ["SECURITY_FAIL_SEVERITY"] = "critical"
        c = SecurityConfig(fail_severity="high")
        c2 = apply_security_env_overrides(c)
        assert c2.fail_severity == "critical"
        del os.environ["SECURITY_FAIL_SEVERITY"]
