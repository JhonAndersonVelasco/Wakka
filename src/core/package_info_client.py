"""
Abre documentación local/pública sobre un paquete sin enviar la descripción a buscadores comerciales.
"""
from __future__ import annotations

import webbrowser
from urllib.parse import quote


class PackageInfoClient:
    """Wiki de Arch + búsqueda en archlinux.org (solo el nombre del paquete en la URL)."""

    def explain_package(self, package_name: str, description: str) -> None:
        wiki_search = "https://wiki.archlinux.org/index.php?title=Special:Search&search={0}".format(quote(package_name))
        repo_search = "https://archlinux.org/packages/?q=" + quote(package_name)
        webbrowser.open(wiki_search, new=2)
        webbrowser.open(repo_search, new=2)
