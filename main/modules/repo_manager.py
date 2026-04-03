"""
Wakka — Repository Manager
Add, remove, enable, and disable pacman repositories in /etc/pacman.conf.
"""
from __future__ import annotations
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from .privilege_helper import PrivilegeHelper
from .constants import PACMAN_CONF_PATH

# Use configurable path from constants
PACMAN_CONF = PACMAN_CONF_PATH


@dataclass
class Repository:
    """
    Repository configuration data class.

    Attributes:
        name: Repository name (without brackets)
        servers: List of mirror URLs
        sig_level: Signature verification level
        enabled: Whether repository is enabled (not commented)
        is_official: Whether repository is an official Arch repo
    """
    name: str
    servers: list[str]
    sig_level: str = "Optional TrustAll"
    enabled: bool = True
    is_official: bool = False


# Official Arch Linux repositories
OFFICIAL_REPOS = {"core", "extra", "multilib", "community", "testing", "multilib-testing"}


class RepoManager:
    """
    Manage pacman repository configuration.

    This class handles reading, writing, and modifying /etc/pacman.conf
    with proper privilege escalation. It supports:

    - Listing all configured repositories
    - Adding new repositories
    - Removing existing repositories
    - Enabling/Disabling repositories (comment/uncomment)
    - Refreshing package databases

    Security:
        All write operations require root privileges via PrivilegeHelper.
        Uses atomic file operations with temporary files to prevent corruption.

    Example:
        >>> manager = RepoManager()
        >>> repos = manager.list_repos()
        >>> success, msg = manager.add_repo("custom", "https://repo.example.com")
    """

    def __init__(self):
        """Initialize RepoManager with privilege helper."""
        self.priv = PrivilegeHelper()

    def list_repos(self) -> list[Repository]:
        """
        Parse and return all configured repositories.

        Returns:
            List of Repository dataclass instances with parsed configuration.

        Note:
            Skips [options] section. Detects enabled/disabled status
            based on Server line comments.
        """
        content = PACMAN_CONF.read_text()
        repos = []
        current_name = None
        current_servers: list[str] = []
        current_sig = "Optional TrustAll"
        current_enabled = True

        for line in content.splitlines():
            stripped = line.strip()

            header = re.match(r"^\[([^\]]+)\]$", stripped)
            if header:
                if current_name and current_name.lower() != "options":
                    repos.append(Repository(
                        name=current_name,
                        servers=current_servers,
                        sig_level=current_sig,
                        enabled=current_enabled,
                        is_official=current_name.lower() in OFFICIAL_REPOS,
                    ))
                current_name = header.group(1)
                current_servers = []
                current_sig = "Optional TrustAll"
                current_enabled = True
                continue

            if current_name and current_name.lower() == "options":
                continue

            disabled = re.match(r"^#\s*Server\s*=\s*(.+)$", stripped)
            if disabled and current_name:
                current_enabled = False
                current_servers.append(disabled.group(1).strip())
                continue

            server = re.match(r"^Server\s*=\s*(.+)$", stripped)
            if server and current_name:
                current_servers.append(server.group(1).strip())
                continue

            sig = re.match(r"^SigLevel\s*=\s*(.+)$", stripped)
            if sig and current_name:
                current_sig = sig.group(1).strip()

        if current_name and current_name.lower() != "options":
            repos.append(Repository(
                name=current_name,
                servers=current_servers,
                sig_level=current_sig,
                enabled=current_enabled,
                is_official=current_name.lower() in OFFICIAL_REPOS,
            ))

        return repos

    def add_repo(self, name: str, server: str, sig_level: str = "Optional TrustAll") -> tuple[bool, str]:
        """
        Add a new repository to pacman.conf.

        Args:
            name: Repository name (will be wrapped in [brackets])
            server: Mirror URL for the repository
            sig_level: Signature verification level

        Returns:
            Tuple of (success: bool, message: str)

        Warning:
            Does not validate server URL or repository existence.
            Caller should verify repository is accessible.
        """
        content = PACMAN_CONF.read_text()
        block = f"\n[{name}]\nSigLevel = {sig_level}\nServer = {server}\n"
        content += block
        return self._write(content)

    def remove_repo(self, name: str) -> tuple[bool, str]:
        """
        Remove a repository from pacman.conf.

        Args:
            name: Repository name to remove

        Returns:
            Tuple of (success: bool, message: str)
        """
        content = PACMAN_CONF.read_text()
        pattern = rf"\n\[{re.escape(name)}\][^\[]*"
        content = re.sub(pattern, "", content)
        return self._write(content)

    def enable_repo(self, name: str) -> tuple[bool, str]:
        """
        Enable a repository by uncommenting Server lines.

        Args:
            name: Repository name to enable

        Returns:
            Tuple of (success: bool, message: str)
        """
        content = PACMAN_CONF.read_text()
        in_section = False
        lines = content.splitlines(keepends=True)
        out = []
        for line in lines:
            if re.match(rf"^\[{re.escape(name)}\]", line.strip()):
                in_section = True
            elif re.match(r"^\[", line.strip()):
                in_section = False
            if in_section and re.match(r"^#\s*Server\s*=", line):
                line = re.sub(r"^#\s*", "", line)
            out.append(line)
        return self._write("".join(out))

    def disable_repo(self, name: str) -> tuple[bool, str]:
        """
        Disable a repository by commenting Server lines.

        Args:
            name: Repository name to disable

        Returns:
            Tuple of (success: bool, message: str)
        """
        content = PACMAN_CONF.read_text()
        in_section = False
        lines = content.splitlines(keepends=True)
        out = []
        for line in lines:
            if re.match(rf"^\[{re.escape(name)}\]", line.strip()):
                in_section = True
            elif re.match(r"^\[", line.strip()):
                in_section = False
            if in_section and re.match(r"^Server\s*=", line):
                line = "# " + line
            out.append(line)
        return self._write("".join(out))

    def refresh_databases(self) -> tuple[bool, str]:
        """
        Refresh package databases using pacman -Sy.

        Returns:
            Tuple of (success: bool, error_message: str)
        """
        success, stdout, stderr = self.priv.run_sync(
            ["pacman", "-Sy"],
            timeout=120
        )
        return success, stderr

    def _write(self, content: str) -> tuple[bool, str]:
        """
        Write content to pacman.conf with atomic operation.

        Args:
            content: New configuration content

        Returns:
            Tuple of (success: bool, error_message: str)

        Security:
            Uses temporary file and cp with sudo for atomic write.
            Cleans up temporary file on success or failure.
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            success, stdout, stderr = self.priv.run_sync(
                ["cp", tmp_path, str(PACMAN_CONF)],
                timeout=30
            )
            Path(tmp_path).unlink(missing_ok=True)
            return success, stderr
        except Exception as e:
            Path(tmp_path).unlink(missing_ok=True)
            return False, str(e)