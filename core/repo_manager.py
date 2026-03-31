"""
Wakka — Repository Manager
Add, remove, enable, and disable pacman repositories in /etc/pacman.conf.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

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
        self._pkexec = shutil.which("pkexec")

    def list_repos(self) -> list[Repository]:
        content = PACMAN_CONF.read_text()
        repos = []
        current_name = None
        current_servers: list[str] = []
        current_sig = "Optional TrustAll"
        current_enabled = True

        for line in content.splitlines():
            stripped = line.strip()

            # Section header
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

            # Commented-out server (disabled repo)
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
        # Remove the whole section
        pattern = rf"\n\[{re.escape(name)}\][^\[]*"
        content = re.sub(pattern, "", content)
        return self._write(content)

    def enable_repo(self, name: str) -> tuple[bool, str]:
        content = PACMAN_CONF.read_text()
        # Remove comment from Server= lines within section
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
                line = "#" + line
            out.append(line)
        return self._write("".join(out))

    def refresh_databases(self) -> tuple[bool, str]:
        # Setup SUDO_ASKPASS
        askpass_path = Path(__file__).resolve().parent / "askpass.py"
        env = os.environ.copy()
        env["SUDO_ASKPASS"] = str(askpass_path)
        display = os.getenv("DISPLAY")
        if display is not None:
            env["DISPLAY"] = display

        try:
            result = subprocess.run(
                ["sudo", "-A", "pacman", "-Sy"],
                capture_output=True, text=True, timeout=120,
                env=env
            )
            return result.returncode == 0, result.stderr.strip()
        except Exception as e:
            return False, str(e)

    def _write(self, content: str) -> tuple[bool, str]:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        # Setup SUDO_ASKPASS
        askpass_path = Path(__file__).resolve().parent / "askpass.py"
        env = os.environ.copy()
        env["SUDO_ASKPASS"] = str(askpass_path)
        display = os.getenv("DISPLAY")
        if display is not None:
            env["DISPLAY"] = display

        try:
            result = subprocess.run(
                ["sudo", "-A", "cp", tmp_path, str(PACMAN_CONF)],
                capture_output=True, text=True, timeout=30,
                env=env
            )
            Path(tmp_path).unlink(missing_ok=True)
            return result.returncode == 0, result.stderr.strip()
        except Exception as e:
            Path(tmp_path).unlink(missing_ok=True)
            return False, str(e)
