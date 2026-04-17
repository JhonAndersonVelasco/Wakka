import subprocess
import json
import os
import re
import random
import shutil
import time
from typing import List, Dict
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup
from PyQt6.QtCore import QCoreApplication

# Constantes del módulo
WIKI_CATEGORIES: dict[str, str] = {
    "Documents": "https://wiki.archlinux.org/title/List_of_applications/Documents",
    "Internet": "https://wiki.archlinux.org/title/List_of_applications/Internet",
    "Multimedia": "https://wiki.archlinux.org/title/List_of_applications/Multimedia",
    "Science": "https://wiki.archlinux.org/title/List_of_applications/Science",
    "Security": "https://wiki.archlinux.org/title/List_of_applications/Security",
    "Utilities": "https://wiki.archlinux.org/title/List_of_applications/Utilities",
    "Other": "https://wiki.archlinux.org/title/List_of_applications/Other",
}
WIKI_CACHE_FILE = os.path.expanduser("~/.cache/wakka/arch_wiki_apps.json")
WIKI_CACHE_DURATION = 24 * 60 * 60  # 24 horas en segundos

# Helper para que pylupdate6 detecte las categorías dinámicas
def _dummy_categories_i18n():
    QCoreApplication.translate("WikiCategories", "Documents")
    QCoreApplication.translate("WikiCategories", "Internet")
    QCoreApplication.translate("WikiCategories", "Multimedia")
    QCoreApplication.translate("WikiCategories", "Science")
    QCoreApplication.translate("WikiCategories", "Security")
    QCoreApplication.translate("WikiCategories", "Utilities")
    QCoreApplication.translate("WikiCategories", "Other")

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


class YayWrapper:
    def __init__(self):
        self.yay_path = "/usr/bin/yay"
        self.pacman_path = "/usr/bin/pacman"

    def _run(self, cmd: List[str]) -> subprocess.CompletedProcess | None:
        """Ejecuta un comando yay/pacman de forma segura y captura su salida."""
        try:
            return subprocess.run(cmd, capture_output=True, text=True, check=False)
        except Exception as e:
            print(f"Error ejecutando comando: {e}")
            return None

    def _scrape_arch_wiki_applications(self) -> dict[str, list[dict[str, str]]]:
        """
        Hace scraping de la Arch Wiki para obtener aplicaciones categorizadas.
        El resultado se cachea en disco durante 24 horas para evitar peticiones repetidas.
        """
        os.makedirs(os.path.dirname(WIKI_CACHE_FILE), exist_ok=True)

        # Verificar caché
        if os.path.exists(WIKI_CACHE_FILE):
            try:
                with open(WIKI_CACHE_FILE, "r") as f:
                    cache_data = json.load(f)
                if time.time() - cache_data.get("timestamp", 0) < WIKI_CACHE_DURATION:
                    print("Cargando apps de la Arch Wiki desde caché.")
                    return cache_data.get("applications", {})
            except json.JSONDecodeError:
                print("Error decodificando caché de Arch Wiki, se re-hace el scraping.")
            except Exception as e:
                print(f"Error cargando caché de Arch Wiki: {e}, se re-hace el scraping.")

        applications_by_category: dict[str, list[dict[str, str]]] = {}

        for category_name, url in WIKI_CATEGORIES.items():
            print(f"Scraping Arch Wiki categoría: {category_name}...")
            applications_by_category[category_name] = []

            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')

                content_div = soup.find('div', {'class': 'mw-parser-output'})
                if not content_div:
                    continue

                # Buscamos todas las listas en la página
                for ul in content_div.find_all('ul'):
                    for li in ul.find_all('li', recursive=False):
                        app_name = ""
                        description = ""

                        # Find the bold tag which usually contains the app name
                        b_tag = li.find('b')
                        if b_tag:
                            # Check if the bold tag contains a link
                            a_tag_in_b = b_tag.find('a', href=True)
                            if a_tag_in_b:
                                app_name = a_tag_in_b.get_text(strip=True)
                            else:
                                app_name = b_tag.get_text(strip=True)

                            # Evitar capturar elementos de navegación o metadatos
                            if len(app_name) < 2 or app_name.startswith('Jump'):
                                continue

                            # Get description from siblings of the bold tag
                            description_parts = []
                            for sibling in b_tag.next_siblings:
                                if sibling.name == 'ul' or sibling.name == 'li': break # Stop if we hit another list or list item
                                if isinstance(sibling, str): description_parts.append(sibling.strip())
                                elif sibling.name == 'span' and 'mw-editsection' not in sibling.get('class', []):
                                    description_parts.append(sibling.get_text(strip=True))
                            description = " ".join(filter(None, description_parts)).strip()
                            # Clean leading separators like '—', ':', '-'
                            description = re.sub(r'^[—:\-\s]+', '', description).strip()

                            if app_name and app_name not in [a['name'] for a in applications_by_category[category_name]]:
                                applications_by_category[category_name].append({"name": app_name, "description": description})
            except Exception as e:
                print(f"Error parsing category {category_name}: {e}")

        # Guardar en caché
        try:
            with open(WIKI_CACHE_FILE, "w") as f:
                json.dump({"timestamp": time.time(), "applications": applications_by_category}, f, indent=2)
        except Exception as e:
            print(f"Error guardando caché de Arch Wiki: {e}")

        return applications_by_category

    def get_available_updates(self) -> List[Package]:
        """Obtiene lista de actualizaciones disponibles"""
        updates = []
        
        # 1. Repositorios oficiales (usamos checkupdates si está disponible para info fresca sin root)
        if shutil.which("checkupdates"):
            res_repo = self._run(["checkupdates", "--nocolor"])
        else:
            # Fallback a pacman -Qu (solo verá lo que ya esté sincronizado)
            res_repo = self._run([self.pacman_path, "-Qu", "--color", "never"])
            
        if res_repo and res_repo.stdout:
            for line in res_repo.stdout.strip().splitlines():
                m = re.match(r"(\S+)\s+(\S+)\s+->\s+(\S+)", line)
                if m:
                    updates.append(Package(
                        name=m.group(1),
                        version=m.group(3),
                        description=QCoreApplication.translate("YayWrapper", "Actualización disponible (Repo)"),
                        repo="repo",
                        installed=True,
                        install_date=m.group(2)
                    ))
                    
        # 2. AUR (yay -Qua solo muestra actualizaciones de AUR)
        res_aur = self._run([self.yay_path, "-Qua", "--color", "never"])
        if res_aur and res_aur.stdout:
            for line in res_aur.stdout.strip().splitlines():
                m = re.match(r"(\S+)\s+(\S+)\s+->\s+(\S+)", line)
                if m:
                    # Evitar duplicados si por alguna razón aparecen en ambos
                    if not any(p.name == m.group(1) for p in updates):
                        updates.append(Package(
                            name=m.group(1),
                            version=m.group(3),
                            description=QCoreApplication.translate("YayWrapper", "Actualización disponible (AUR)"),
                            repo="aur",
                            installed=True,
                            install_date=m.group(2)
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

    def get_installed_packages(self) -> List[Package]:
        """Obtiene todos los paquetes instalados"""
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
                        size=pkg_info.get('Installed Size', pkg_info.get('Tamaño de la instalación', ''))
                    ))
        return packages

    def get_popular_suggestions(
        self, progress_callback=None
    ) -> dict[str, list["Package"]]:
        """
        Obtiene sugerencias populares de la Arch Wiki agrupadas por categoría,
        filtrando las que ya están instaladas.
        """
        wiki_apps_by_category = self._scrape_arch_wiki_applications()
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
            print(f"Error al desbloquear: {msg}")
            return False
        except Exception as e:
            print(f"Error inesperado al desbloquear: {e}")
            return False

    def refresh_databases(self) -> subprocess.Popen:
        """Sincroniza las bases de datos de los repositorios (requiere root)"""
        return subprocess.Popen(["pkexec", "/usr/bin/wakka-helper", "refresh"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def install(self, packages: List[str]) -> subprocess.Popen:
        """Instala paquetes (retorna proceso para terminal)"""
        cmd = ["pkexec", "/usr/bin/wakka-helper", "install"] + packages
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def remove(self, packages: List[str]) -> subprocess.Popen:
        """Desinstala paquetes"""
        cmd = ["pkexec", "/usr/bin/wakka-helper", "remove"] + packages
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def update_system(self) -> subprocess.Popen:
        """Actualiza todo el sistema"""
        return subprocess.Popen(["pkexec", "/usr/bin/wakka-helper", "update"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def install_local_package(self, file_path: str) -> subprocess.Popen:
        """Instala paquete .pkg.tar.zst local"""
        return subprocess.Popen(["pkexec", "/usr/bin/wakka-helper", "install-local", file_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def clean_cache(self, orphans: bool = False) -> subprocess.Popen:
        """Limpia caché de paquetes y/o huérfanos."""
        if orphans:
            return subprocess.Popen(
                ["pkexec", "/usr/bin/wakka-helper", "clean"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
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