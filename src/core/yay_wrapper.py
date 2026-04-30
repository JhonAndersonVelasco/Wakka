from __future__ import annotations

import logging
import os
import random
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Callable, Dict, List

from PyQt6.QtCore import QCoreApplication

from core.arch_wiki import fetch_wiki_applications_by_category
from core.pacman_text import parse_upgrade_line

logger = logging.getLogger(__name__)


@dataclass
class Package:
    name: str
    version: str
    description: str
    repo: str  # core, extra, aur, community
    installed: bool
    size: str = ""
    install_date: str = ""
    votes: str = "0"
    popularity: str = "0"
    last_used: str = ""  # Fecha de último uso (atime de ejecutables)


class YayWrapper:
    def __init__(self) -> None:
        self.yay_path = shutil.which("yay") or "/usr/bin/yay"
        self.pacman_path = shutil.which("pacman") or "/usr/bin/pacman"

    def _run(self, cmd: List[str]) -> subprocess.CompletedProcess | None:
        """Ejecuta un comando yay/pacman de forma segura y captura su salida."""
        try:
            return subprocess.run(cmd, capture_output=True, text=True, check=False)
        except OSError as e:
            logger.error("Error ejecutando comando %s: %s", cmd, e)
            return None

    def get_available_updates(self) -> List[Package]:
        """Obtiene lista de actualizaciones disponibles"""
        updates = []
        
        # 1. Repositorios oficiales (usamos checkupdates si está disponible para info fresca sin root)
        if shutil.which("checkupdates"):
            res_repo = self._run(["checkupdates"])
        else:
            # Fallback a pacman -Qu (solo verá lo que ya esté sincronizado)
            res_repo = self._run([self.pacman_path, "-Qu"])
            
        if res_repo and res_repo.stdout:
            for line in res_repo.stdout.strip().splitlines():
                parsed = parse_upgrade_line(line)
                if parsed:
                    name, cur, new = parsed
                    updates.append(Package(
                        name=name,
                        version=new,
                        description=QCoreApplication.translate("YayWrapper", "Actualización disponible (Repo)"),
                        repo="repo",
                        installed=True,
                        install_date=cur,
                    ))
                    
        # 2. AUR (yay -Qua solo muestra actualizaciones de AUR)
        res_aur = self._run([self.yay_path, "-Qua", "--color", "never"])
        if res_aur and res_aur.stdout:
            for line in res_aur.stdout.strip().splitlines():
                parsed = parse_upgrade_line(line)
                if parsed:
                    name, cur, new = parsed
                    if not any(p.name == name for p in updates):
                        updates.append(Package(
                            name=name,
                            version=new,
                            description=QCoreApplication.translate("YayWrapper", "Actualización disponible (AUR)"),
                            repo="aur",
                            installed=True,
                            install_date=cur,
                        ))
                        
        return updates

    def search_packages(self, query: str) -> List[Package]:
        """Busca paquetes en repos y AUR"""
        # Dividimos por espacios para que pacman/yay busquen cada término (comportamiento AND)
        cmd = [self.yay_path, "-Ss"] + query.split()
        result = self._run(cmd)
        packages = []

        if result and result.stdout:
            lines = result.stdout.strip().split('\n')
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if not line:
                    i += 1
                    continue

                if not line.startswith(' '):
                    parts = line.split()
                    repo_pkg = parts[0]
                    version = parts[1] if len(parts) > 1 else ""
                    installed = "[instalado]" in line.lower() or "[installed]" in line.lower()

                    if '/' in repo_pkg:
                        repo, name = repo_pkg.split('/', 1)
                    else:
                        repo, name = "aur", repo_pkg

                    votes = "0"
                    popularity = "0"
                    if repo == "aur":
                        for idx, p in enumerate(parts):
                            if p.startswith("(+"):
                                votes = p.replace("(+", "").replace(")", "")
                                if idx + 1 < len(parts):
                                    popularity = parts[idx+1].replace(")", "")

                    description = ""
                    if i + 1 < len(lines) and lines[i+1].startswith(' '):
                        description = lines[i+1].strip()
                        i += 1

                    packages.append(Package(
                        name=name, version=version, description=description,
                        repo=repo, installed=installed,
                        votes=votes, popularity=popularity
                    ))
                i += 1
        return packages

    def get_package_last_used(self, name: str) -> str:
        """
        Lee el último tiempo de acceso (atime) de los ejecutables del paquete
        para estimar cuándo fue utilizado por última vez.
        Lee directamente el îndice de pacman para rapidez (sin subprocess).
        """
        pacman_db = f"/var/lib/pacman/local/{name}"

        # Buscar el directorio del paquete (puede tener versión en el nombre)
        if not os.path.isdir(pacman_db):
            try:
                candidates = [
                    d for d in os.listdir("/var/lib/pacman/local")
                    if d == name or d.startswith(f"{name}-")
                ]
                if not candidates:
                    return ""
                pacman_db = f"/var/lib/pacman/local/{candidates[0]}"
            except OSError:
                return ""

        files_list = os.path.join(pacman_db, "files")
        if not os.path.exists(files_list):
            return ""

        # Directorios de interés para determinar "uso"
        EXEC_DIRS = ("/usr/bin/", "/usr/sbin/", "/bin/", "/sbin/",
                     "/usr/lib/", "/usr/lib64/", "/usr/libexec/")

        latest_atime = 0.0
        try:
            with open(files_list) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("%"):
                        continue
                    # El archivo lists las rutas sin la "/" inicial
                    full_path = f"/{line}"
                    if not any(full_path.startswith(d) for d in EXEC_DIRS):
                        continue
                    try:
                        st = os.stat(full_path)
                        if st.st_atime > latest_atime:
                            latest_atime = st.st_atime
                    except (OSError, PermissionError):
                        continue
        except Exception:
            return ""

        if latest_atime == 0.0:
            return ""

        import datetime
        dt = datetime.datetime.fromtimestamp(latest_atime)
        return dt.strftime("%d %b %Y")

    def get_installed_packages(self) -> List[Package]:
        """Obtiene todos los paquetes instalados (Pacman + Externos)"""
        result = self._run([self.pacman_path, "-Qi"])
        packages = []

        if result and result.stdout:
            sections = result.stdout.strip().split('\n\n')
            for section in sections:
                pkg_info = {}
                for line in section.split('\n'):
                    if ' : ' in line:
                        key, val = line.split(' : ', 1)
                        pkg_info[key.strip()] = val.strip()

                name = pkg_info.get('Name', pkg_info.get('Nombre', ''))
                if name:
                    raw_date = pkg_info.get('Install Date', pkg_info.get('Fecha de instalación', ''))
                    date_parts = raw_date.split()
                    short_date = " ".join(date_parts[1:4]) if len(date_parts) >= 4 else raw_date

                    packages.append(Package(
                        name=name,
                        version=pkg_info.get('Version', pkg_info.get('Versión', '')),
                        description=pkg_info.get('Description', pkg_info.get('Descripción', '')),
                        repo="local",
                        installed=True,
                        install_date=short_date,
                        size=pkg_info.get('Installed Size', pkg_info.get('Tamaño de la instalación', '')),
                        last_used=self.get_package_last_used(name)
                    ))
        
        # Añadir paquetes externos (AppImages)
        packages.extend(self.get_external_packages())
        return packages

    def get_external_packages(self) -> List[Package]:
        """Busca paquetes instalados manualmente (AppImages) registrados por Wakka"""
        external = []
        apps_dir = "/usr/share/applications"
        if not os.path.exists(apps_dir):
            return []
            
        for f in os.listdir(apps_dir):
            if f.endswith(".desktop"):
                path = os.path.join(apps_dir, f)
                try:
                    with open(path, "r", errors="ignore") as fd:
                        content = fd.read()
                        if "X-Wakka-Installed=true" in content:
                            name = ""
                            desc = "AppImage (Manual)"
                            for line in content.splitlines():
                                if line.startswith("Name="): name = line.split("=", 1)[1]
                                elif line.startswith("Comment="): desc = line.split("=", 1)[1]
                            
                            if name:
                                external.append(Package(
                                    name=f"{name} (AppImage)",
                                    version="Local",
                                    description=desc,
                                    repo="appimage",
                                    installed=True,
                                    install_date=time.strftime("%d %b %Y", time.localtime(os.path.getmtime(path)))
                                ))
                except Exception:
                    continue
        return external

    def get_popular_suggestions(
        self,
        progress_callback: Callable[[str], None] | None = None,
    ) -> dict[str, list[Package]]:
        """
        Obtiene sugerencias populares de la Arch Wiki agrupadas por categoría,
        filtrando las que ya están instaladas.
        """
        wiki_apps_by_category = fetch_wiki_applications_by_category()
        installed = self.get_installed_packages()
        installed_names = {p.name.lower() for p in installed}

        suggestions_by_category: Dict[str, List[Package]] = {}

        for category, apps_list in wiki_apps_by_category.items():
            if not apps_list:
                continue

            if progress_callback:
                # Traducir el nombre de la categoría (ej. Documents -> Documentos)
                translated_cat = QCoreApplication.translate("WikiCategories", category)
                msg = QCoreApplication.translate("YayWrapper", "Analizando categoría: {0}...")
                progress_callback(msg.format(translated_cat))

            available_apps = [app for app in apps_list if app['name'].lower() not in installed_names]
            random.shuffle(available_apps)

            selected_apps_for_category = []
            for app_info in available_apps[:4]: # Select up to 4 apps per category
                app_name = app_info['name']
                scraped_description = app_info['description']
                search_result = self.search_packages(app_name)
                if search_result:
                    pkg = search_result[0]
                    if scraped_description: # Prioritize scraped description
                        pkg.description = scraped_description
                    selected_apps_for_category.append(pkg)
            if selected_apps_for_category:
                suggestions_by_category[category] = selected_apps_for_category

        return suggestions_by_category

    def is_locked(self) -> bool:
        """Verifica si existe el archivo de bloqueo de pacman"""
        return os.path.exists("/var/lib/pacman/db.lck")

    def unlock(self) -> bool:
        """Elimina el archivo de bloqueo de pacman usando el ayudante"""
        try:
            # Capturar salida para poder informar si falla (ej. error de pkexec o del script)
            result = subprocess.run(
                ["pkexec", "/usr/bin/wakka-helper", "unlock"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            msg = e.stderr if e.stderr else e.stdout
            logger.error("Error al desbloquear: %s", msg)
            return False
        except Exception:
            logger.exception("Error inesperado al desbloquear")
            return False

    def refresh_databases(self) -> subprocess.Popen:
        """Sincroniza las bases de datos de los repositorios (requiere root)"""
        return subprocess.Popen(["pkexec", "/usr/bin/wakka-background-helper", "refresh"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)

    def install(self, packages: List[str]) -> subprocess.Popen:
        """Instala paquetes (retorna proceso para terminal)"""
        cmd = ["pkexec", "/usr/bin/wakka-helper", "install"] + packages
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)

    def remove(self, packages: List[str]) -> subprocess.Popen:
        """Desinstala paquetes"""
        cmd = ["pkexec", "/usr/bin/wakka-helper", "remove"] + packages
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)

    def update_system(self) -> subprocess.Popen:
        """Actualiza todo el sistema"""
        return subprocess.Popen(["pkexec", "/usr/bin/wakka-helper", "update"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)

    def download_updates(self, packages: List[str] = None) -> subprocess.Popen:
        """Descarga actualizaciones sin instalarlas (yay -Sw)"""
        cmd = ["pkexec", "/usr/bin/wakka-background-helper", "download"]
        if packages:
            cmd += packages
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)

    def install_local_package(self, file_path: str) -> subprocess.Popen:
        """Instala paquete .pkg.tar.zst local"""
        return subprocess.Popen(["pkexec", "/usr/bin/wakka-helper", "install-local", file_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)

    def clean_cache(self, orphans: bool = False) -> subprocess.Popen:
        """Limpia caché de paquetes y/o huérfanos."""
        if orphans:
            return subprocess.Popen(
                ["pkexec", "/usr/bin/wakka-helper", "clean"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=True
            )
        else:
            # Limpiar caché de AUR de forma segura, sin shell ni globbing
            yay_cache = os.path.expanduser("~/.cache/yay")
            try:
                if os.path.isdir(yay_cache):
                    shutil.rmtree(yay_cache)
                    os.makedirs(yay_cache, exist_ok=True)
                msg_success = QCoreApplication.translate("YayWrapper", "Caché de AUR limpiada correctamente")
                proc = subprocess.Popen(
                    ["echo", msg_success],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
            except Exception as e:
                msg_error = QCoreApplication.translate("YayWrapper", "Error al limpiar caché: {0}")
                proc = subprocess.Popen(
                    ["echo", msg_error.format(e)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
            return proc