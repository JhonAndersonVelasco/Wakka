"""
Wakka — Package Manager Core
Async wrapper around yay/pacman using QProcess for real-time output.
"""
from __future__ import annotations
import os
import re
import shutil
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
from PyQt6.QtCore import QObject, QProcess, pyqtSignal, QProcessEnvironment, QLocale
from .privilege_helper import PrivilegeHelper


class PkgSource(Enum):
    """Package source enumeration."""
    OFFICIAL = "official"
    AUR = "aur"
    LOCAL = "local"


class PkgStatus(Enum):
    """Package installation status enumeration."""
    INSTALLED = auto()
    NOT_INSTALLED = auto()
    UPGRADABLE = auto()


@dataclass
class Package:
    """
    Package data class representing a software package.

    Attributes:
        name: Package name
        version: Current or available version
        description: Package description
        source: Package source (official, AUR, local)
        status: Installation status
        installed_version: Currently installed version
        new_version: Available update version
        size: Package size
        url: Package homepage URL
        licenses: List of licenses
        depends: List of dependencies
        provides: List of provided packages
        maintainer: Package maintainer
        votes: AUR vote count
        popularity: AUR popularity score
        selected: Selection state for batch operations
    """
    name: str
    version: str
    description: str = ""
    source: PkgSource = PkgSource.OFFICIAL
    status: PkgStatus = PkgStatus.NOT_INSTALLED
    installed_version: str = ""
    new_version: str = ""
    size: str = ""
    url: str = ""
    licenses: list[str] = field(default_factory=list)
    depends: list[str] = field(default_factory=list)
    provides: list[str] = field(default_factory=list)
    maintainer: str = ""
    votes: int = 0
    popularity: float = 0.0
    selected: bool = False


class PackageManager(QObject):
    """
    Core package management operations for Arch-based systems.

    This class provides async wrapper around yay/pacman using QProcess
    for real-time output streaming. It handles:

    - Package search (official repos + AUR)
    - Installation/Removal operations
    - Update checking and execution
    - Package details retrieval

    Signals:
        output_line: Emitted for each line of command output
        operation_started: Emitted when an operation begins
        operation_finished: Emitted when an operation completes
        search_results_ready: Emitted with parsed search results
        installed_packages_ready: Emitted with installed package list
        updates_found: Emitted with available updates

    Example:
        >>> pkg_manager = PackageManager(language="es")
        >>> pkg_manager.search_results_ready.connect(handle_results)
        >>> pkg_manager.search("firefox")
    """

    output_line = pyqtSignal(str, bool)
    operation_started = pyqtSignal(str)
    operation_finished = pyqtSignal(bool, str, str)
    progress_updated = pyqtSignal(int, int)
    search_results_ready = pyqtSignal(list)
    installed_packages_ready = pyqtSignal(list)
    updates_found = pyqtSignal(list)

    def __init__(self, language: str = "auto", parent: Optional[QObject] = None):
        """
        Initialize PackageManager with language configuration.

        Args:
            language: Language code ('auto', 'es', 'en', or locale string)
            parent: Optional Qt parent object for memory management
        """
        super().__init__(parent)
        self._language = language
        self._process: Optional[QProcess] = None
        self._yay = shutil.which("yay")
        self._pacman = shutil.which("pacman")
        self.priv = PrivilegeHelper(parent)
        self.priv.output_line.connect(self.output_line)
        self.priv.operation_finished.connect(self._on_priv_finished)
        self._current_op: str = ""
        self._installed_output = ""
        self._file_install_queue: list[Path] = []
        self._query_process = QProcess()
        self._last_search_sort = "votes"
        self._last_search_direction = "desc"

    @property
    def yay_available(self) -> bool:
        """Check if yay AUR helper is available."""
        return self._yay is not None

    @property
    def is_busy(self) -> bool:
        """Check if an operation is currently in progress."""
        return self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning

    def _on_priv_finished(self, success: bool, msg: str, operation: str):
        """Handle privilege helper operation completion."""
        self.operation_finished.emit(success, msg, operation)

    def get_package_details(self, name: str) -> str:
        """
        Get detailed package information.

        Args:
            name: Package name to query

        Returns:
            Formatted package details string
        """
        env = self._get_env_dict()
        res = subprocess.run([self._pacman, "-Qi", name], capture_output=True, text=True, env=env)
        if res.returncode == 0:
            return res.stdout.strip()
        if self._yay:
            res = subprocess.run([self._yay, "-Si", name], capture_output=True, text=True, env=env)
            if res.returncode == 0:
                return res.stdout.strip()
        return "Información no disponible"

    def search(self, query: str, sort: str = "votes", page: int = 1, direction: str = "desc"):
        """
        Search for packages in official repos and AUR.

        Args:
            query: Search term (package name or description)
            sort: Sort criteria ('votes', 'popularity', 'name', 'modified')
            page: Page number for pagination (1-indexed)
            direction: Sort direction ('asc' or 'desc')

        Emits:
            search_results_ready: With list of Package objects

        Note:
            Empty queries emit empty list immediately without execution.
        """
        if not query.strip():
            self.search_results_ready.emit([])
            return
        self._last_search_sort = sort or "votes"
        self._last_search_direction = direction if direction in ("asc", "desc") else "desc"
        cmd = self._yay or self._pacman
        if cmd == self._yay:
            args = ["-Ss", "--noconfirm", "--sortby", self._last_search_sort, query]
        else:
            args = ["-Ss", query]
        self._run(cmd, args, self._on_search_output, operation="search", ignore_codes=[0, 1])

    def _on_search_output(self, stdout: str, _stderr: str):
        """Process search output and emit results."""
        packages = _parse_search_output(stdout)
        packages = self._apply_search_order(packages)
        self.search_results_ready.emit(packages)

    def _apply_search_order(self, packages: list[Package]) -> list[Package]:
        """Apply sorting to package list based on current settings."""
        reverse = self._last_search_direction == "desc"
        if self._last_search_sort == "name":
            return sorted(packages, key=lambda x: x.name.lower(), reverse=reverse)
        if self._last_search_sort == "votes":
            return sorted(packages, key=lambda x: x.votes, reverse=reverse)
        if self._last_search_sort == "popularity":
            return sorted(packages, key=lambda x: x.popularity, reverse=reverse)
        if self._last_search_sort == "modified":
            return list(reversed(packages)) if reverse else packages
        return list(reversed(packages)) if reverse else packages

    def get_installed(self):
        """Get list of installed packages via pacman -Q."""
        if self._query_process.state() != QProcess.ProcessState.NotRunning:
            return
        self._installed_output = ""
        self._query_process.readyReadStandardOutput.connect(self._on_installed_ready)
        self._query_process.finished.connect(self._on_installed_finished)
        self._query_process.start(self._pacman, ["-Q", "--color", "never"])

    def _on_installed_ready(self):
        """Accumulate installed packages output."""
        self._installed_output += self._query_process.readAllStandardOutput().data().decode()

    def _on_installed_finished(self, exit_code: int, _exit_status):
        """Parse and emit installed packages list."""
        try:
            self._query_process.readyReadStandardOutput.disconnect(self._on_installed_ready)
        except Exception:
            pass
        try:
            self._query_process.finished.disconnect(self._on_installed_finished)
        except Exception:
            pass
        packages = []
        for line in self._installed_output.strip().splitlines():
            parts = line.strip().split()
            if len(parts) >= 2:
                pkg = Package(name=parts[0], version=parts[1], status=PkgStatus.INSTALLED)
                packages.append(pkg)
        self.installed_packages_ready.emit(packages)

    def check_updates(self, silent: bool = False):
        """
        Check for available package updates.

        Args:
            silent: If True, suppress loading UI state
        """
        self._run(
            self._yay or self._pacman,
            ["-Qu", "--color", "never"],
            self._on_updates_output,
            operation="check_updates",
            ignore_codes=[0, 1],
            silent=silent
        )

    def _on_updates_output(self, stdout: str, _stderr: str):
        """Parse and emit available updates."""
        updates = []
        for line in stdout.strip().splitlines():
            m = re.match(r"(\S+)\s+(\S+)\s+->\s+(\S+)", line)
            if m:
                pkg = Package(
                    name=m.group(1),
                    version=m.group(3),
                    installed_version=m.group(2),
                    new_version=m.group(3),
                    status=PkgStatus.UPGRADABLE,
                )
                updates.append(pkg)
        self.updates_found.emit(updates)

    def check_updates_sync(self) -> list[Package]:
        """
        Synchronously check for available updates.

        Returns:
            List of Package objects with update information
        """
        try:
            result = subprocess.run(
                [self._yay or self._pacman, "-Qu", "--color", "never"],
                capture_output=True, text=True, timeout=60
            )
            updates = []
            for line in result.stdout.strip().splitlines():
                m = re.match(r"(\S+)\s+(\S+)\s+->\s+(\S+)", line)
                if m:
                    pkg = Package(
                        name=m.group(1),
                        version=m.group(3),
                        installed_version=m.group(2),
                        new_version=m.group(3),
                        status=PkgStatus.UPGRADABLE,
                    )
                    updates.append(pkg)
            return updates
        except Exception:
            return []

    def install(self, packages: list[str]):
        """
        Install one or more packages.

        Args:
            packages: List of package names to install

        Emits:
            operation_started: With operation identifier
            operation_finished: With success status and message

        Security:
            Uses SUDO_ASKPASS for privilege escalation.
            Requires user authentication via askpass.py dialog.
        """
        if not packages:
            return
        self.operation_started.emit(f"install:{','.join(packages)}")
        if self._yay:
            self._run(
                self._yay,
                ["-S", "--noconfirm", "--cleanafter", "--sudo", "sudo", "--sudoflags", "-A"] + packages,
                self._on_generic_finish,
                operation="install",
            )
        else:
            self.priv.run_async(
                ["pacman", "-S", "--noconfirm"] + packages,
                operation="install",
            )

    def uninstall(self, packages: list[str]):
        """
        Uninstall one or more packages.

        Args:
            packages: List of package names to remove

        Emits:
            operation_started: With operation identifier
            operation_finished: With success status and message
        """
        if not packages:
            return
        self.operation_started.emit(f"uninstall:{','.join(packages)}")
        self.priv.run_async(
            ["pacman", "-Rns", "--noconfirm"] + packages,
            operation="uninstall",
        )

    def install_files(self, paths: list[str]):
        """
        Install packages from local files (.pkg.tar.zst or .deb).

        Args:
            paths: List of file paths to install
        """
        package_paths = []
        for path in paths:
            file_path = self._normalize_path(path)
            if not file_path.exists():
                self.output_line.emit(f"[wakka] Archivo no encontrado: {path}\n", True)
                continue
            if self._is_arch_package(file_path) or self._is_debian_package(file_path):
                package_paths.append(file_path)
            else:
                self.output_line.emit(f"[wakka] Tipo de archivo no soportado: {path}\n", True)
        if not package_paths:
            return
        self._file_install_queue.extend(package_paths)
        if not self.is_busy:
            self._run_next_package_file()

    def _run_next_package_file(self) -> None:
        """Process next package file in install queue."""
        if self.is_busy or not self._file_install_queue:
            return
        package_file = self._file_install_queue.pop(0)
        if self._is_arch_package(package_file):
            command = ["pacman", "-U", "--noconfirm", str(package_file)]
            operation = f"install-file:{package_file.name}"
        else:
            if not shutil.which("dpkg"):
                self.output_line.emit("[wakka] dpkg no está disponible para instalar .deb\n", True)
                if self._file_install_queue:
                    self._run_next_package_file()
                return
            command = ["dpkg", "-i", str(package_file)]
            operation = f"install-deb:{package_file.name}"
        self.operation_started.emit(operation)
        self.priv.run_async(command, operation=operation)

    def _is_arch_package(self, file_path: Path) -> bool:
        """Check if file is an Arch Linux package."""
        return "".join(file_path.suffixes[-3:]) == ".pkg.tar.zst"

    def _is_debian_package(self, file_path: Path) -> bool:
        """Check if file is a Debian package."""
        return file_path.suffix == ".deb"

    def _normalize_path(self, path: str) -> Path:
        """Normalize file path, handling file:// URLs."""
        if path.startswith("file://"):
            from urllib.parse import unquote, urlparse
            parsed = urlparse(path)
            if parsed.scheme == "file":
                return Path(unquote(parsed.path))
        return Path(path)

    def update_all(self):
        """Update all installed packages."""
        self.operation_started.emit("update_all")
        if self._yay:
            self._run(
                self._yay,
                ["-Syu", "--noconfirm", "--sudo", "sudo", "--sudoflags", "-A"],
                self._on_generic_finish,
                operation="update_all",
            )
        else:
            self.priv.run_async(
                ["pacman", "-Syu", "--noconfirm"],
                operation="update_all",
            )

    def update_selected(self, packages: list[str]):
        """
        Update specific packages.

        Args:
            packages: List of package names to update
        """
        if not packages:
            return
        self.operation_started.emit(f"update:{','.join(packages)}")
        if self._yay:
            self._run(
                self._yay,
                ["-S", "--noconfirm", "--sudo", "sudo", "--sudoflags", "-A"] + packages,
                self._on_generic_finish,
                operation="update",
            )
        else:
            self.priv.run_async(
                ["pacman", "-S", "--noconfirm"] + packages,
                operation="update",
            )

    def _on_generic_finish(self, stdout: str, stderr: str):
        """Generic operation finish handler."""
        pass

    def _run(self, program: str, args: list[str], on_finish_callback, *,
             operation: str, ignore_codes: list[int] = None, silent: bool = False):
        """
        Run command asynchronously with QProcess.

        Args:
            program: Executable to run
            args: Command arguments
            on_finish_callback: Callback for completion
            operation: Operation identifier for logging
            ignore_codes: Exit codes to treat as success
            silent: Suppress output emission
        """
        if self.is_busy:
            if not silent:
                self.output_line.emit("[wakka] Operación en progreso, espera...\n", True)
            return
        if not program:
            self.operation_finished.emit(False, "Programa no encontrado", operation)
            return
        ignore_codes = ignore_codes or [0]
        self._current_op = operation
        process = QProcess(self)
        self._process = process
        env = QProcessEnvironment.systemEnvironment()
        env.insert("SUDO_ASKPASS", str(Path(__file__).parent / "askpass.py"))
        display = os.getenv("DISPLAY")
        if display is not None:
            env.insert("DISPLAY", display)
        locale_val = self._get_locale_string()
        if locale_val:
            env.insert("LC_ALL", locale_val)
        process.setProcessEnvironment(env)
        process.setProgram(program)
        process.setArguments(args)
        stdout_accumulator = []
        stderr_accumulator = []

        def on_stdout():
            try:
                data = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
                stdout_accumulator.append(data)
                if not silent:
                    for line in data.splitlines(keepends=True):
                        self.output_line.emit(line, False)
            except RuntimeError:
                pass

        def on_stderr():
            try:
                data = bytes(process.readAllStandardError()).decode("utf-8", errors="replace")
                stderr_accumulator.append(data)
                if not silent:
                    for line in data.splitlines(keepends=True):
                        self.output_line.emit(line, True)
            except RuntimeError:
                pass

        def on_finished(exit_code, _exit_status):
            try:
                success = exit_code in ignore_codes
                stdout = "".join(stdout_accumulator)
                stderr = "".join(stderr_accumulator)

                # 🔥 Clear askpass state on success
                if success:
                    from pathlib import Path
                    Path("/tmp/wakka_sudo_attempt").unlink(missing_ok=True)

                on_finish_callback(stdout, stderr)
                msg = "OK" if success else f"Error (código {exit_code})"
                self.operation_finished.emit(success, msg, operation)

                if self._process == process:
                    self._process = None
            except RuntimeError:
                pass

        process.readyReadStandardOutput.connect(on_stdout)
        process.readyReadStandardError.connect(on_stderr)
        process.finished.connect(on_finished)
        process.start()

    def cancel(self):
        """Cancel current running operation."""
        if self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.terminate()
            self._process.waitForFinished(3000)
            if self._process.state() != QProcess.ProcessState.NotRunning:
                self._process.kill()
                self._process.waitForFinished(3000)

    def _get_locale_string(self) -> str:
        """Get locale string for command environment."""
        if self._language == "auto":
            return QLocale.system().name() + ".UTF-8"
        elif self._language == "es":
            return "es_ES.UTF-8"
        elif self._language == "en":
            return "en_US.UTF-8"
        return self._language + ".UTF-8"

    def _get_env_dict(self) -> dict:
        """Get environment dictionary for subprocess calls."""
        env = os.environ.copy()
        locale_val = self._get_locale_string()
        if locale_val:
            env["LC_ALL"] = locale_val
        return env


def _parse_search_output(text: str) -> list[Package]:
    """
    Parse yay/pacman search output into Package objects.

    Args:
        text: Raw command output

    Returns:
        List of Package objects
    """
    packages = []
    lines = text.strip().splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^(\S+)/(\S+)\s+(\S+)(.*)", line)
        if m:
            repo = m.group(1)
            name = m.group(2)
            version = m.group(3)
            rest = m.group(4)
            votes = 0
            popularity = 0.0
            score_match = re.search(r"\+(\d+)\s+([0-9]+(?:\.[0-9]+)?)", rest)
            if score_match:
                votes = int(score_match.group(1))
                popularity = float(score_match.group(2))
            source = PkgSource.AUR if repo.lower() == "aur" else PkgSource.OFFICIAL
            if re.search(r"upgradable|actualizable", rest, re.IGNORECASE):
                status = PkgStatus.UPGRADABLE
            elif re.search(r"\[installed|\(installed\)|\(Instalado\)|\[Instalado\]", rest, re.IGNORECASE):
                status = PkgStatus.INSTALLED
            else:
                status = PkgStatus.NOT_INSTALLED
            desc = ""
            if i + 1 < len(lines) and lines[i + 1].startswith("    "):
                desc = lines[i + 1].strip()
                i += 1
            pkg = Package(
                name=name,
                version=version,
                description=desc,
                source=source,
                status=status,
                votes=votes,
                popularity=popularity,
            )
            packages.append(pkg)
        i += 1
    return packages


def _parse_info_output(text: str) -> dict:
    """
    Parse package info output into dictionary.

    Args:
        text: Raw pacman -Qi or yay -Si output

    Returns:
        Dictionary of key-value pairs
    """
    info = {}
    for line in text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            info[key.strip()] = value.strip()
    return info