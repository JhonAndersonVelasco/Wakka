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
    OFFICIAL = "official"
    AUR = "aur"
    LOCAL = "local"

class PkgStatus(Enum):
    INSTALLED = auto()
    NOT_INSTALLED = auto()
    UPGRADABLE = auto()

@dataclass
class Package:
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
    output_line = pyqtSignal(str, bool)
    operation_started = pyqtSignal(str)
    operation_finished = pyqtSignal(bool, str, str)
    progress_updated = pyqtSignal(int, int)
    search_results_ready = pyqtSignal(list)
    installed_packages_ready = pyqtSignal(list)
    updates_found = pyqtSignal(list)

    def __init__(self, language: str = "auto", parent: Optional[QObject] = None):
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
        return self._yay is not None

    @property
    def is_busy(self) -> bool:
        return self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning

    def _on_priv_finished(self, success: bool, msg: str, operation: str):
        self.operation_finished.emit(success, msg, operation)

    def get_package_details(self, name: str) -> str:
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
        packages = _parse_search_output(stdout)
        packages = self._apply_search_order(packages)
        self.search_results_ready.emit(packages)

    def _apply_search_order(self, packages: list[Package]) -> list[Package]:
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
        if self._query_process.state() != QProcess.ProcessState.NotRunning:
            return
        self._installed_output = ""
        self._query_process.readyReadStandardOutput.connect(self._on_installed_ready)
        self._query_process.finished.connect(self._on_installed_finished)
        self._query_process.start(self._pacman, ["-Q", "--color", "never"])

    def _on_installed_ready(self):
        self._installed_output += self._query_process.readAllStandardOutput().data().decode()

    def _on_installed_finished(self, exit_code: int, _exit_status):
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
        self._run(
            self._yay or self._pacman,
            ["-Qu", "--color", "never"],
            self._on_updates_output,
            operation="check_updates",
            ignore_codes=[0, 1],
            silent=silent
        )

    def _on_updates_output(self, stdout: str, _stderr: str):
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
        if not packages:
            return
        self.operation_started.emit(f"uninstall:{','.join(packages)}")
        self.priv.run_async(
            ["pacman", "-Rns", "--noconfirm"] + packages,
            operation="uninstall",
        )

    def install_files(self, paths: list[str]):
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
        return "".join(file_path.suffixes[-3:]) == ".pkg.tar.zst"

    def _is_debian_package(self, file_path: Path) -> bool:
        return file_path.suffix == ".deb"

    def _normalize_path(self, path: str) -> Path:
        if path.startswith("file://"):
            from urllib.parse import unquote, urlparse
            parsed = urlparse(path)
            if parsed.scheme == "file":
                return Path(unquote(parsed.path))
        return Path(path)

    def update_all(self):
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
        pass

    def _run(self, program: str, args: list[str], on_finish_callback, *,
             operation: str, ignore_codes: list[int] = None, silent: bool = False):
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

                # 🔥 LIMPIAR ESTADO DE ASKPASS SI TODO FUE BIEN
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
        if self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.terminate()
            self._process.waitForFinished(3000)
            if self._process.state() != QProcess.ProcessState.NotRunning:
                self._process.kill()
                self._process.waitForFinished(3000)

    def _get_locale_string(self) -> str:
        if self._language == "auto":
            return QLocale.system().name() + ".UTF-8"
        elif self._language == "es":
            return "es_ES.UTF-8"
        elif self._language == "en":
            return "en_US.UTF-8"
        return self._language + ".UTF-8"

    def _get_env_dict(self) -> dict:
        env = os.environ.copy()
        locale_val = self._get_locale_string()
        if locale_val:
            env["LC_ALL"] = locale_val
        return env

def _parse_search_output(text: str) -> list[Package]:
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
    info = {}
    for line in text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            info[key.strip()] = value.strip()
    return info