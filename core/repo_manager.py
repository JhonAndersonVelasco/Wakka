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

PACMAN_CONF = Path("/etc/pacman.conf")

@dataclass
class Repository:
    name: str
    servers: list[str]
    sig_level: str = "Optional TrustAll"
    enabled: bool = True
    is_official: bool = False

OFFICIAL_REPOS = {"core", "extra", "multilib", "community", "testing", "multilib-testing"}

class RepoManager:
    def __init__(self):
        self.priv = PrivilegeHelper()

    def list_repos(self) -> list[Repository]:
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
        content = PACMAN_CONF.read_text()
        block = f"\n[{name}]\nSigLevel = {sig_level}\nServer = {server}\n"
        content += block
        return self._write(content)

    def remove_repo(self, name: str) -> tuple[bool, str]:
        content = PACMAN_CONF.read_text()
        pattern = rf"\n\[{re.escape(name)}\][^\[]*"
        content = re.sub(pattern, "", content)
        return self._write(content)

    def enable_repo(self, name: str) -> tuple[bool, str]:
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
        success, stdout, stderr = self.priv.run_sync(
            ["pacman", "-Sy"],
            timeout=120
        )
        return success, stderr

    def _write(self, content: str) -> tuple[bool, str]:
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