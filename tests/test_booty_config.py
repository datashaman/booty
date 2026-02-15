"""Tests for .booty.yml configuration file."""
import os


def test_booty_yml_exists():
    """Test that .booty.yml file exists in the repository root."""
    booty_file = ".booty.yml"
    assert os.path.exists(booty_file), f"{booty_file} should exist in repository root"


def test_booty_yml_is_readable():
    """Test that .booty.yml file can be read."""
    booty_file = ".booty.yml"
    with open(booty_file, 'r') as f:
        content = f.read()
        assert content, "File should not be empty"


def test_booty_yml_contains_version():
    """Test that .booty.yml contains version field."""
    booty_file = ".booty.yml"
    with open(booty_file, 'r') as f:
        content = f.read()
    
    assert 'version:' in content or 'version :' in content, "Config should have 'version' field"


def test_booty_yml_contains_test_command():
    """Test that .booty.yml contains test_command field."""
    booty_file = ".booty.yml"
    with open(booty_file, 'r') as f:
        content = f.read()
    
    assert 'test_command:' in content or 'test_command :' in content, "Config should have 'test_command' field"


def test_booty_yml_contains_pytest():
    """Test that .booty.yml mentions pytest."""
    booty_file = ".booty.yml"
    with open(booty_file, 'r') as f:
        content = f.read()
    
    assert 'pytest' in content, "Config should reference 'pytest' as test command"


def test_booty_yml_format():
    """Test that .booty.yml has basic YAML-like structure."""
    booty_file = ".booty.yml"
    with open(booty_file, 'r') as f:
        lines = f.readlines()
    
    # Should have at least 2 lines (version and test_command)
    assert len(lines) >= 2, "Config should have at least 2 lines"
    
    # Check for colon separators (basic YAML structure)
    has_colons = any(':' in line for line in lines)
    assert has_colons, "Config should have YAML-style key:value pairs"
