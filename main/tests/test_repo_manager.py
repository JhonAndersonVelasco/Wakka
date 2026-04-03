"""Unit tests for RepoManager module."""
import pytest
from unittest.mock import patch, MagicMock
from modules.repo_manager import RepoManager, Repository, OFFICIAL_REPOS


class TestRepoManager:
    """Test suite for RepoManager class."""

    @pytest.fixture
    def repo_manager(self):
        """Create a RepoManager instance with mocked dependencies."""
        with patch('modules.repo_manager.PrivilegeHelper'):
            return RepoManager()

    def test_official_repo_detection(self):
        """Test official repository detection."""
        for repo_name in OFFICIAL_REPOS:
            assert repo_name.lower() in OFFICIAL_REPOS

    def test_repository_dataclass(self):
        """Test Repository dataclass creation."""
        repo = Repository(
            name="custom",
            servers=["https://example.com/repo"],
            sig_level="Optional TrustAll",
            enabled=True,
            is_official=False
        )
        assert repo.name == "custom"
        assert len(repo.servers) == 1
        assert repo.enabled is True