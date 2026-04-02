# Maintainer: Jhon Velasco <jhandervelbux@gmail.com>
# PKGBUILD for the Wakka system packages management tool.

pkgname=wakka
pkgver=0.1.0          # <-- reemplaza con la versión real
pkgrel=1
pkgdesc="Wakka – a system management utility"
arch=('x86_64')
url="https://github.com/JhonAndersonVelasco/wakka"   # <-- reemplaza con la página del proyecto
license=('MIT')                  # <-- ajusta si es distinto
depends=('python-pyqt6'          # paquete oficial que incluye Qt6
         'python-apscheduler'
         'python-dbus'
         'python-pydbus'
         'python-requests'
         'python-packaging'
         'python-psutil')
# Si quieres ser más explícito con Qt6:
# depends+=('qt6-base')
makedepends=('git' 'python-pip')
source=("git+https://github.com/JhonAndersonVelasco/wakka.git")   # <-- reemplaza con el repo real
sha256sums=('SKIP')   # <-- usa checksum real si no quieres SKIP

# ----------------------------------------------------------------------
# 1️⃣ Prepare – generar un pyproject.toml mínimo si no existe
# ----------------------------------------------------------------------
prepare() {
    cd "$srcdir/$pkgname"

    # Sólo crear el archivo si el upstream no lo provee.
    if [[ ! -f pyproject.toml ]]; then
        cat > pyproject.toml <<'EOF'
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "wakka"
version = "0.1.0"
description = "Wakka – a system‑management utility"
authors = [{name = "Your Name", email = "you@example.com"}]
license = {text = "MIT"}
requires-python = ">=3.10"
dependencies = [
    "PyQt6>=6.6.0",
    "PyQt6-Qt6>=6.6.0",
    "apscheduler>=3.10.4",
    "dbus-python>=1.3.2",
    "pydbus>=0.6.0",
    "requests>=2.31.0",
    "packaging>=24.0",
    "psutil>=5.9.0"
]
EOF
    fi
}

# ----------------------------------------------------------------------
# 2️⃣ Build – nada que compilar para un proyecto puro de Python
# ----------------------------------------------------------------------
build() {
    :
}

# ----------------------------------------------------------------------
# 3️⃣ Package – instalar el paquete Python y los archivos auxiliares
# ----------------------------------------------------------------------
package() {
    cd "$srcdir/$pkgname"

    # --------------------------------------------------------------
    # 1️⃣ Instalar el paquete Python en $pkgdir/usr
    # --------------------------------------------------------------
    python -m pip install --root="$pkgdir" --prefix=/usr .

    # --------------------------------------------------------------
    # 2️⃣ Instaladores (launchers)
    # --------------------------------------------------------------
    install -Dm755 /dev/stdin "$pkgdir/usr/bin/wakka" <<'LAUNCHER'
#!/usr/bin/env python3
import sys
from wakka.main import main
if __name__ == '__main__':
    main()
LAUNCHER

    install -Dm755 /dev/stdin "$pkgdir/usr/bin/wakka-shutdown-helper" <<'HELPER'
#!/usr/bin/env python3
import sys
from wakka.systemd.shutdown_handler import shutdown_main
if __name__ == '__main__':
    shutdown_main()
HELPER

    # --------------------------------------------------------------
    # 3️⃣ Servicio systemd
    # --------------------------------------------------------------
    install -Dm644 "install/wakka-shutdown.service" "$pkgdir/usr/lib/systemd/system/wakka-shutdown.service"

    # --------------------------------------------------------------
    # 4️⃣ Entrada de escritorio
    # --------------------------------------------------------------
    install -Dm644 "install/wakka.desktop" "$pkgdir/usr/share/applications/wakka.desktop"

    # --------------------------------------------------------------
    # 5️⃣ Definición MIME
    # --------------------------------------------------------------
    install -Dm644 "install/wakka-mime.xml" "$pkgdir/usr/share/mime/packages/wakka-mime.xml"

    # --------------------------------------------------------------
    # 6️⃣ Regla polkit
    # --------------------------------------------------------------
    install -Dm644 "install/10-wakka.rules" "$pkgdir/usr/share/polkit-1/rules.d/10-wakka.rules"

    # --------------------------------------------------------------
    # 7️⃣ Iconos
    # --------------------------------------------------------------
    # 7a – SVG escalable
    install -Dm644 "ui/assets/wakka.svg" "$pkgdir/usr/share/icons/hicolor/scalable/apps/wakka.svg"

    # 7b – PNGs generados con get_logo_icon()
    #     Necesita una QApplication y ejecutarse en modo off‑screen.
    QT_QPA_PLATFORM=offscreen DESTDIR="$pkgdir" PREFIX="/usr" python - <<'PYICON'
import os
import sys

# Añadir el directorio raíz del proyecto al PYTHONPATH
sys.path.insert(0, os.getcwd())

try:
    # Importar la función que devuelve el QIcon
    from wakka.ui.styles.icons import get_logo_icon
except Exception as e:
    print(f"Warning: Could not import get_logo_icon: {e}", file=sys.stderr)
    sys.exit(0)   # Saltar generación de PNG si falla la importación

# Crear una QApplication (necesario para QPixmap/QIcon)
from PyQt6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

sizes = [16, 22, 32, 48, 64, 128, 256]
for s in sizes:
    out_dir = f"{os.getenv('DESTDIR')}/usr/share/icons/hicolor/{s}x{s}/apps"
    os.makedirs(out_dir, exist_ok=True)
    icon = get_logo_icon(s)
    pixmap = icon.pixmap(s, s)
    pixmap.save(f"{out_dir}/wakka.png", "PNG")
PYICON

    # --------------------------------------------------------------
    # 8️⃣ (Opcional) Actualizar cachés – normalmente lo hace pacman después de la instalación.
    # --------------------------------------------------------------
    # gtk-update-icon-cache -f -t "$pkgdir/usr/share/icons/hicolor"
    # update-desktop-database "$pkgdir/usr/share/applications"
    # update-mime-database "$pkgdir/usr/share/mime"
}