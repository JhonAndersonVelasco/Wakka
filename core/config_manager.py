"""
Wakka — Config Manager
Manages /etc/pacman.conf (via sudo) and ~/.config/wakka/settings.json.
"""
from __future__ import annotations
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any
from .privilege_helper import PrivilegeHelper

PACMAN_CONF = Path("/etc/pacman.conf")
SETTINGS_DIR = Path.home() / ".config" / "wakka"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "theme": "dark",
    "language": "auto",
    "autostart": True,
    "check_updates_on_start": True,
    "update_schedule": {
        "enabled": False,
        "frequency": "weekly",
        "day": "saturday",
        "hour": 10,
        "minute": 0,
    },
    "cache": {
        "auto_clean": False,
        "auto_clean_frequency": "monthly",
        "keep_versions": 2,
    },
    "shutdown_updates": False,
    "notifications": True,
    "parallel_downloads": 5,
}

class ConfigManager:
    def __init__(self):
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        self._settings = self._load_settings()
        self.priv = PrivilegeHelper()

    def _load_settings(self) -> dict:
        if SETTINGS_FILE.exists():
            try:
                data = json.loads(SETTINGS_FILE.read_text())
                return _deep_merge(DEFAULT_SETTINGS.copy(), data)
            except Exception:
                pass
        return DEFAULT_SETTINGS.copy()

    def save(self):
        SETTINGS_FILE.write_text(json.dumps(self._settings, indent=2, ensure_ascii=False))

    def get(self, key: str, default=None) -> Any:
        keys = key.split(".")
        val = self._settings
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    def set(self, key: str, value: Any):
        keys = key.split(".")
        d = self._settings
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value
        self.save()

    @property
    def settings(self) -> dict:
        return self._settings

    def _write_pacman_conf(self, content: str) -> tuple[bool, str]:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            success, stdout, stderr = self.priv.run_sync(
                ["cp", tmp_path, str(PACMAN_CONF)],
                timeout=30
            )
            Path(tmp_path).unlink(missing_ok=True)
            if success:
                return True, "OK"
            return False, stderr
        except Exception as e:
            Path(tmp_path).unlink(missing_ok=True)
            return False, str(e)

    def get_ignored_packages(self) -> list[str]:
        content = PACMAN_CONF.read_text()
        m = re.search(r"^IgnorePkg\s*=\s*(.*)$", content, re.MULTILINE)
        if m:
            return [p.strip() for p in m.group(1).split() if p.strip()]
        return []

    def set_ignored_packages(self, packages: list[str]) -> tuple[bool, str]:
        content = PACMAN_CONF.read_text()
        line = f"IgnorePkg = {' '.join(packages)}"
        if re.search(r"^IgnorePkg\s*=", content, re.MULTILINE):
            content = re.sub(r"^#?IgnorePkg\s*=.*$", line, content, flags=re.MULTILINE)
        else:
            content = re.sub(r"(\[options\])", r"\1\n" + line, content)
        return self._write_pacman_conf(content)

    def add_ignored_package(self, name: str) -> tuple[bool, str]:
        pkgs = self.get_ignored_packages()
        if name not in pkgs:
            pkgs.append(name)
        return self.set_ignored_packages(pkgs)

    def remove_ignored_package(self, name: str) -> tuple[bool, str]:
        pkgs = [p for p in self.get_ignored_packages() if p != name]
        return self.set_ignored_packages(pkgs)

    def get_parallel_downloads(self) -> int:
        content = PACMAN_CONF.read_text()
        m = re.search(r"^#?ParallelDownloads\s*=\s*(\d+)", content, re.MULTILINE)
        return int(m.group(1)) if m else 1

    def set_parallel_downloads(self, n: int) -> tuple[bool, str]:
        content = PACMAN_CONF.read_text()
        line = f"ParallelDownloads = {n}"
        if re.search(r"^#?ParallelDownloads\s*=", content, re.MULTILINE):
            content = re.sub(r"^#?ParallelDownloads\s*=.*$", line, content, flags=re.MULTILINE)
        else:
            content = re.sub(r"(\[options\])", r"\1\n" + line, content)
        return self._write_pacman_conf(content)

    def get_color_enabled(self) -> bool:
        content = PACMAN_CONF.read_text()
        return bool(re.search(r"^Color$", content, re.MULTILINE))

    def set_color(self, enabled: bool) -> tuple[bool, str]:
        content = PACMAN_CONF.read_text()
        if enabled:
            content = re.sub(r"^#Color$", "Color", content, flags=re.MULTILINE)
            if not re.search(r"^Color$", content, re.MULTILINE):
                content = re.sub(r"(\[options\])", r"\1\nColor", content)
        else:
            content = re.sub(r"^Color$", "#Color", content, flags=re.MULTILINE)
        return self._write_pacman_conf(content)

    def set_autostart(self, enabled: bool):
        self.set("autostart", enabled)
        autostart_dir = Path.home() / ".config" / "autostart"
        autostart_file = autostart_dir / "wakka.desktop"
        src = Path(__file__).resolve().parents[1] / "install" / "wakka-autostart.desktop"

        if enabled:
            autostart_dir.mkdir(parents=True, exist_ok=True)
            if src.exists():
                shutil.copy(src, autostart_file)
        else:
            autostart_file.unlink(missing_ok=True)

    def set_shutdown_updates(self, enabled: bool) -> tuple[bool, str]:
        self.set("shutdown_updates", enabled)
        action = "enable" if enabled else "disable"

        success, stdout, stderr = self.priv.run_sync(
            ["systemctl", action, "wakka-shutdown.service"],
            timeout=15
        )
        return success, stderr

def _deep_merge(base: dict, override: dict) -> dict:
    for key, val in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(val, dict):
            _deep_merge(base[key], val)
        else:
            base[key] = val
    return base