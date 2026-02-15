"""Tests for webhook cooldown cleanup functionality."""

import time
from unittest.mock import MagicMock, patch

import pytest

from booty.webhooks import _cleanup_cooldown, _obsv_seen


@pytest.fixture(autouse=True)
def clear_cooldown():
    """Clear cooldown dictionary before and after each test."""
    _obsv_seen.clear()
    yield
    _obsv_seen.clear()


def test_cleanup_cooldown_removes_expired_entries():
    """Test that cleanup removes entries older than 2x cooldown window."""
    mock_settings = MagicMock()
    mock_settings.OBSV_COOLDOWN_HOURS = 1  # 1 hour cooldown
    
    with patch("booty.webhooks.get_settings", return_value=mock_settings):
        now = time.time()
        # Add entries: one recent, one expired
        _obsv_seen["recent"] = now - 3600  # 1 hour ago (within 2x window)
        _obsv_seen["expired"] = now - 7201  # Just over 2 hours ago (outside 2x window)
        
        # Run cleanup
        _cleanup_cooldown()
        
        # Verify only expired entry is removed
        assert "recent" in _obsv_seen
        assert "expired" not in _obsv_seen


def test_cleanup_cooldown_preserves_all_recent_entries():
    """Test that cleanup preserves all entries within 2x cooldown window."""
    mock_settings = MagicMock()
    mock_settings.OBSV_COOLDOWN_HOURS = 1
    
    with patch("booty.webhooks.get_settings", return_value=mock_settings):
        now = time.time()
        # Add multiple recent entries
        _obsv_seen["entry1"] = now - 1800  # 30 min ago
        _obsv_seen["entry2"] = now - 3600  # 1 hour ago
        _obsv_seen["entry3"] = now - 7199  # Just under 2 hours ago
        
        # Run cleanup
        _cleanup_cooldown()
        
        # Verify all entries are preserved
        assert len(_obsv_seen) == 3
        assert "entry1" in _obsv_seen
        assert "entry2" in _obsv_seen
        assert "entry3" in _obsv_seen


def test_cleanup_cooldown_removes_all_expired_entries():
    """Test that cleanup removes all entries older than 2x cooldown window."""
    mock_settings = MagicMock()
    mock_settings.OBSV_COOLDOWN_HOURS = 1
    
    with patch("booty.webhooks.get_settings", return_value=mock_settings):
        now = time.time()
        # Add multiple expired entries
        _obsv_seen["old1"] = now - 7300  # Over 2 hours ago
        _obsv_seen["old2"] = now - 10800  # 3 hours ago
        _obsv_seen["old3"] = now - 86400  # 24 hours ago
        
        # Run cleanup
        _cleanup_cooldown()
        
        # Verify all expired entries are removed
        assert len(_obsv_seen) == 0


def test_cleanup_cooldown_handles_empty_dictionary():
    """Test that cleanup handles empty cooldown dictionary gracefully."""
    mock_settings = MagicMock()
    mock_settings.OBSV_COOLDOWN_HOURS = 1
    
    with patch("booty.webhooks.get_settings", return_value=mock_settings):
        # Ensure dictionary is empty
        assert len(_obsv_seen) == 0
        
        # Run cleanup
        _cleanup_cooldown()
        
        # Verify dictionary is still empty
        assert len(_obsv_seen) == 0


def test_cleanup_cooldown_with_different_cooldown_hours():
    """Test cleanup with different OBSV_COOLDOWN_HOURS settings."""
    mock_settings = MagicMock()
    mock_settings.OBSV_COOLDOWN_HOURS = 2  # 2 hour cooldown
    
    with patch("booty.webhooks.get_settings", return_value=mock_settings):
        now = time.time()
        # Add entries: one recent, one expired for 2h window
        _obsv_seen["recent"] = now - 7200  # 2 hours ago (within 2x 2h window)
        _obsv_seen["expired"] = now - 14401  # Just over 4 hours ago (outside 2x 2h window)
        
        # Run cleanup
        _cleanup_cooldown()
        
        # Verify only expired entry is removed
        assert "recent" in _obsv_seen
        assert "expired" not in _obsv_seen


def test_cleanup_cooldown_logs_when_entries_removed():
    """Test that cleanup logs when entries are removed."""
    mock_settings = MagicMock()
    mock_settings.OBSV_COOLDOWN_HOURS = 1
    
    with patch("booty.webhooks.get_settings", return_value=mock_settings):
        with patch("booty.webhooks.get_logger") as mock_logger:
            now = time.time()
            _obsv_seen["expired1"] = now - 7300
            _obsv_seen["expired2"] = now - 8000
            
            # Run cleanup
            _cleanup_cooldown()
            
            # Verify logger.debug was called with removed_count
            mock_logger.return_value.debug.assert_called_once_with(
                "cooldown_cleanup", removed_count=2
            )


def test_cleanup_cooldown_does_not_log_when_no_entries_removed():
    """Test that cleanup does not log when no entries are removed."""
    mock_settings = MagicMock()
    mock_settings.OBSV_COOLDOWN_HOURS = 1
    
    with patch("booty.webhooks.get_settings", return_value=mock_settings):
        with patch("booty.webhooks.get_logger") as mock_logger:
            now = time.time()
            _obsv_seen["recent"] = now - 1800
            
            # Run cleanup
            _cleanup_cooldown()
            
            # Verify logger was not called
            mock_logger.return_value.debug.assert_not_called()
