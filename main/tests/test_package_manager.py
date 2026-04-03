"""Unit tests for PackageManager module."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from modules.package_manager import PackageManager, Package, PkgSource, PkgStatus


class TestPackageManager:
    """Test suite for PackageManager class."""

    @pytest.fixture
    def pkg_manager(self):
        """Create a PackageManager instance with mocked dependencies."""
        with patch('modules.package_manager.shutil.which', return_value='/usr/bin/yay'):
            with patch('modules.package_manager.PrivilegeHelper'):
                return PackageManager(language="en")

    def test_yay_available(self, pkg_manager):
        """Test yay detection."""
        assert pkg_manager.yay_available is True

    def test_is_busy_when_idle(self, pkg_manager):
        """Test busy state when no operation is running."""
        assert pkg_manager.is_busy is False

    def test_parse_search_output(self):
        """Test search output parsing."""
        sample_output = """
aur/visual-studio-code-bin 1.85.0-1 (+123 4.56)
    Code editing. Redefined.
"""
        from modules.package_manager import _parse_search_output
        packages = _parse_search_output(sample_output)
        
        assert len(packages) == 1
        assert packages[0].name == "visual-studio-code-bin"
        assert packages[0].source == PkgSource.AUR
        assert packages[0].votes == 123

    def test_search_empty_query(self, pkg_manager):
        """Test search with empty query returns empty list."""
        mock_signal = Mock()
        pkg_manager.search_results_ready.connect(mock_signal)
        pkg_manager.search("")
        mock_signal.emit.assert_called_once_with([])

    def test_get_package_details_pacman(self, pkg_manager):
        """Test package details retrieval."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Name: test\nVersion: 1.0")
            result = pkg_manager.get_package_details("test")
            assert "Name: test" in result