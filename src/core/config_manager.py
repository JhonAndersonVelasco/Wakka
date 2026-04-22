"""
Wakka — Config Manager
Manages /etc/pacman.conf (via sudo) and ~/.config/wakka/settings.json.
"""
from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PACMAN_CONF = Path("/etc/pacman.conf")

# Repository section headers shipped / documented as Arch official or common testing repos.
OFFICIAL_PACMAN_SECTIONS: frozenset[str] = frozenset({
    "[options]",
    "[core]",
    "[extra]",
    "[community]",
    "[multilib]",
    "[core-testing]",
    "[extra-testing]",
    "[community-testing]",
    "[multilib-testing]",
    "[testing]",
    "[staging]",
    "[community-staging]",
    "[multilib-staging]",
    "[kde-unstable]",
    "[gnome-unstable]",
})
SETTINGS_DIR = Path.home() / ".config" / "wakka"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "theme": "system",
    "language": "auto",
    "autostart": True,
    "check_updates_on_start": True,
    "update_schedule": {
        "enabled": True,
        "frequency": "daily",
        "hour": 12,
        "minute": 0,
    },
    "cache": {
        "auto_clean": True,
        "keep_versions": 1,
        "schedule": {
            "enabled": False,
            "frequency": "monthly",
            "day": "1",
            "hour": 0,
            "minute": 0,
            "interval_hours": 6
        },
    },
    "shutdown_updates": False,
    "background_download": True,
    "notifications": True,
    "parallel_downloads": 5,
}


class ConfigManager:
    def __init__(self):
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        self._settings = self._load_settings()

    def _load_settings(self) -> dict:
        if SETTINGS_FILE.exists():
            try:
                data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                return _deep_merge(DEFAULT_SETTINGS.copy(), data)
            except Exception as e:
                logger.warning("No se pudo leer la configuración (%s): %s", SETTINGS_FILE, e)
                corrupt_backup = SETTINGS_FILE.with_name(
                    f"{SETTINGS_FILE.stem}.corrupt.{int(time.time())}{SETTINGS_FILE.suffix}"
                )
                try:
                    shutil.copy2(SETTINGS_FILE, corrupt_backup)
                    logger.info("Copia de seguridad del JSON dañado: %s", corrupt_backup)
                except OSError as copy_err:
                    logger.warning("No se pudo respaldar el archivo de configuración: %s", copy_err)
        return DEFAULT_SETTINGS.copy()

    def save(self):
        SETTINGS_FILE.write_text(
            json.dumps(self._settings, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

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
            # Usar el nuevo helper para aplicar cambios
            ok, msg = self._run_privileged(["/usr/bin/wakka-helper", "apply-pacman-conf", tmp_path], timeout=30)
            Path(tmp_path).unlink(missing_ok=True)
            return ok, msg
        except Exception as e:
            Path(tmp_path).unlink(missing_ok=True)
            if "pkexec" in str(e).lower():
                return False, "Cancelled"
            return False, str(e)

    def _run_privileged(self, cmd: list[str], timeout: int = 15) -> tuple[bool, str]:
        """Ejecuta un comando con pkexec y captura errores de forma robusta."""
        try:
            proc = subprocess.run(
                ["pkexec"] + cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            if proc.returncode == 0:
                return True, "OK"
            if proc.returncode in [126, 127]:
                return False, "Cancelled"
            
            err = (proc.stderr or proc.stdout or "").strip()
            if not err:
                err = f"Proceso falló con código {proc.returncode}"
            else:
                err = f"[Error {proc.returncode}] {err}"
            return False, err
        except Exception as e:
            if "pkexec" in str(e).lower():
                return False, "Cancelled"
            return False, str(e)

    def get_ignored_packages(self) -> list[str]:
        if not PACMAN_CONF.exists():
            return []
        content = PACMAN_CONF.read_text()
        m = re.search(r"^[ \t]*IgnorePkg[ \t]*=[ \t]*(.*)$", content, re.MULTILINE)
        if m:
            return [p.strip() for p in m.group(1).split() if p.strip()]
        return []

    def set_ignored_packages(self, packages: list[str]) -> tuple[bool, str]:
        if not PACMAN_CONF.exists():
            return False, "pacman.conf no existe"
        content = PACMAN_CONF.read_text()
        line = f"IgnorePkg = {' '.join(packages)}"
        if not packages:
            line = "#" + line
        if re.search(r"^[# \t]*IgnorePkg[ \t]*=", content, re.MULTILINE):
            content = re.sub(r"^[# \t]*IgnorePkg[ \t]*=.*$", line, content, flags=re.MULTILINE)
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
        if not PACMAN_CONF.exists():
            return 1
        content = PACMAN_CONF.read_text()
        m = re.search(r"^[# \t]*ParallelDownloads[ \t]*=[ \t]*(\d+)", content, re.MULTILINE)
        return int(m.group(1)) if m else 1

    def set_parallel_downloads(self, n: int) -> tuple[bool, str]:
        if not PACMAN_CONF.exists():
            return False, "pacman.conf no existe"
        content = PACMAN_CONF.read_text()
        line = f"ParallelDownloads = {n}"
        if bool(re.search(r"^[# \t]*ParallelDownloads[ \t]*=", content, re.MULTILINE)):
            content = re.sub(r"^[# \t]*ParallelDownloads[ \t]*=.*$", line, content, flags=re.MULTILINE)
        else:
            content = re.sub(r"(\[options\])", r"\1\n" + line, content)
        return self._write_pacman_conf(content)

    def get_color_enabled(self) -> bool:
        if not PACMAN_CONF.exists():
            return False
        content = PACMAN_CONF.read_text()
        return bool(re.search(r"^Color$", content, re.MULTILINE))

    def set_color(self, enabled: bool) -> tuple[bool, str]:
        if not PACMAN_CONF.exists():
            return False, "pacman.conf no existe"
        content = PACMAN_CONF.read_text()
        if enabled:
            content = re.sub(r"^#Color$", "Color", content, flags=re.MULTILINE)
            if not re.search(r"^Color$", content, re.MULTILINE):
                content = re.sub(r"(\[options\])", r"\1\nColor", content)
        else:
            if re.search(r"^Color$", content, re.MULTILINE):
                content = re.sub(r"^Color$", "#Color", content, flags=re.MULTILINE)
        return self._write_pacman_conf(content)

    def get_custom_repositories(self) -> str:
        if not PACMAN_CONF.exists():
            return ""
        content = PACMAN_CONF.read_text()
        
        lines = content.split('\n')

        custom_lines = []
        is_custom = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('[') and stripped.endswith(']'):
                if stripped in OFFICIAL_PACMAN_SECTIONS:
                    is_custom = False
                else:
                    is_custom = True

            if is_custom:
                custom_lines.append(line)
                
        return '\n'.join(custom_lines).strip()

    def set_custom_repositories(self, custom_text: str) -> tuple[bool, str]:
        if not PACMAN_CONF.exists():
            return False, "pacman.conf no existe"
            
        content = PACMAN_CONF.read_text()
        lines = content.split('\n')
        new_lines = []
        is_official = True

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('[') and stripped.endswith(']'):
                if stripped in OFFICIAL_PACMAN_SECTIONS:
                    is_official = True
                else:
                    is_official = False

            if is_official:
                new_lines.append(line)
                
        while new_lines and new_lines[-1].strip() == "":
            new_lines.pop()
            
        if custom_text.strip():
            new_lines.append("\n" + custom_text.strip() + "\n")
            
        new_content = '\n'.join(new_lines) + '\n'
        return self._write_pacman_conf(new_content)

    def apply_pacman_conf_changes(self, parallel: int, color: bool, ignore_pkgs: list[str], custom_repos: str) -> tuple[bool, str]:
        if not PACMAN_CONF.exists():
            return False, "pacman.conf no existe"
            
        content = PACMAN_CONF.read_text()
        
        # 1. Parallel Downloads
        line_pd = f"ParallelDownloads = {parallel}"
        if bool(re.search(r"^[# \t]*ParallelDownloads[ \t]*=", content, re.MULTILINE)):
            content = re.sub(r"^[# \t]*ParallelDownloads[ \t]*=.*$", line_pd, content, flags=re.MULTILINE)
        else:
            content = re.sub(r"(\[options\])", r"\1\n" + line_pd, content)
            
        # 2. Color
        if color:
            content = re.sub(r"^#Color$", "Color", content, flags=re.MULTILINE)
            if not re.search(r"^Color$", content, re.MULTILINE):
                content = re.sub(r"(\[options\])", r"\1\nColor", content)
        else:
            if re.search(r"^Color$", content, re.MULTILINE):
                content = re.sub(r"^Color$", "#Color", content, flags=re.MULTILINE)
                
        # 3. IgnorePkg
        line_ignore = f"IgnorePkg = {' '.join(ignore_pkgs)}"
        if not ignore_pkgs:
            line_ignore = "#" + line_ignore
        if re.search(r"^[# \t]*IgnorePkg[ \t]*=", content, re.MULTILINE):
            content = re.sub(r"^[# \t]*IgnorePkg[ \t]*=.*$", line_ignore, content, flags=re.MULTILINE)
        else:
            content = re.sub(r"(\[options\])", r"\1\n" + line_ignore, content)
            
        # 4. Custom Repositories
        lines = content.split('\n')
        new_lines = []
        is_official = True
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('[') and stripped.endswith(']'):
                is_official = stripped in OFFICIAL_PACMAN_SECTIONS
            if is_official:
                new_lines.append(line)
        while new_lines and new_lines[-1].strip() == "":
            new_lines.pop()
        if custom_repos.strip():
            new_lines.append("\n" + custom_repos.strip() + "\n")
        
        final_content = '\n'.join(new_lines) + '\n'
        return self._write_pacman_conf(final_content)

    def set_autostart(self, enabled: bool):
        self.set("autostart", enabled)
        autostart_dir = Path.home() / ".config" / "autostart"
        autostart_file = autostart_dir / "wakka-tray.desktop"
        
        # We use absolute paths to ensure the desktop entry works in dev environment
        # sys.argv[0] is the script path, sys.executable is the python path
        exec_path = Path(sys.argv[0]).resolve() if not sys.argv[0].endswith("wakka") else "wakka"
        cmd = f"{sys.executable} {exec_path} --tray" if isinstance(exec_path, Path) else "wakka --tray"
        
        if enabled:
            autostart_dir.mkdir(parents=True, exist_ok=True)
            content = f"""[Desktop Entry]
Name=Wakka (tray)
Comment=Moderno gestor gráfico de paquetes para Arch Linux con integración de IA
Comment[en]=Modern graphical package manager for Arch Linux with AI integration
Comment[de]=Moderner grafischer Paketmanager für Arch Linux mit KI-Integration
Comment[fr]=Gestionnaire de paquets graphique moderne pour Arch Linux avec intégration d'IA
Comment[it]=Gestore di pacchetti grafico moderno per Arch Linux con integrazione dell'intelligenza artificiale
Comment[ru]=Современный графический менеджер пакетов для Arch Linux с интеграцией ИИ
Comment[jp]=AIを統合したArch Linux向けの最新グラフィカルパッケージマネージャー
Comment[cn]=适用于 Arch Linux 的现代图形化软件包管理器，集成了 AI 技术
Exec={cmd}
Icon=wakka
Terminal=false
Type=Application
# Hidden from app menus — only for autostart
NoDisplay=true
X-GNOME-Autostart-enabled=true
X-KDE-autostart-after=panel
StartupNotify=false
"""
            autostart_file.write_text(content)
        else:
            autostart_file.unlink(missing_ok=True)

    def is_autostart_actually_enabled(self) -> bool:
        autostart_file = Path.home() / ".config" / "autostart" / "wakka-tray.desktop"
        return autostart_file.exists()

    def set_shutdown_updates(self, enabled: bool) -> tuple[bool, str]:
        action = "enable" if enabled else "disable"
        ok, msg = self._run_privileged(["/usr/bin/wakka-service-helper", "set-shutdown-service", action], timeout=15)
        if ok:
            self.set("shutdown_updates", enabled)
        return ok, msg


def _deep_merge(base: dict, override: dict) -> dict:
    for key, val in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(val, dict):
            _deep_merge(base[key], val)
        else:
            base[key] = val
    return base
