"""Unit tests for ConfigManager module."""
import pytest
import json
from pathlib import Path
from unittest.mock import patch, mock_open
from modules.config_manager import ConfigManager, DEFAULT_SETTINGS


class TestConfigManager:
    """Test suite for ConfigManager class."""

    @pytest.fixture
    def config_manager(self):
        """Create a ConfigManager instance with mocked file system."""
        with patch('modules.config_manager.SETTINGS_FILE'):
            with patch('modules.config_manager.SETTINGS_DIR'):
                return ConfigManager()

    def test_default_settings(self, config_manager):
        """Test default settings are loaded correctly."""
        assert config_manager.get("theme") == "dark"
        assert config_manager.get("autostart") is True

    def test_get_nested_key(self, config_manager):
        """Test getting nested configuration keys."""
        value = config_manager.get("update_schedule.enabled")
        assert value is False

    def test_set_value(self, config_manager):
        """Test setting configuration values."""
        config_manager.set("theme", "light")
        assert config_manager.get("theme") == "light"

    def test_set_nested_value(self, config_manager):
        """Test setting nested configuration values."""
        config_manager.set("cache.auto_clean", True)
        assert config_manager.get("cache.auto_clean") is True

    def test_ignored_packages_empty(self, config_manager):
        """Test getting ignored packages when none configured."""
        with patch('modules.config_manager.PACMAN_CONF_PATH') as mock_conf:
            mock_conf.read_text.return_value = "[options]\n"
            packages = config_manager.get_ignored_packages()
            assert packages == []