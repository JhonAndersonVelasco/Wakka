# Maintainer: Your Name <youremail@example.com>
# PKGBUILD for the Wakka system‑management tool.
# Adjust the placeholders (pkgver, url, license, source, sha256sums) as needed.

pkgname=wakka
pkgver=0.1.0          # <-- replace with the actual version
pkgrel=1
pkgdesc="Wakka – a system management utility"
arch=('x86_64')
url="https://example.com/wakka"   # <-- replace with the project's homepage
license=('MIT')                  # <-- adjust if different
depends=('python-pyqt6'          # official package that pulls Qt6
         'python-apscheduler'
         'python-dbus'
         'python-pydbus'
         'python-requests'
         'python-packaging'
         'python-psutil')
# If you want to be explicit about Qt6:
# depends+=('qt6-base')
makedepends=('git' 'python-pip')
source=("git+https://github.com/yourusername/wakka.git")   # <-- replace with real repo
sha256sums=('SKIP')   # <-- use a real checksum if you don’t want SKIP

# ----------------------------------------------------------------------
# 1️⃣ Prepare – generate a minimal pyproject.toml if it does not exist
# ----------------------------------------------------------------------
prepare() {
    cd "$srcdir/$pkgname"

    # Only create the file if the upstream does not already provide one.
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
# 2️⃣ Build – nothing to compile for a pure‑Python project
# ----------------------------------------------------------------------
build() {
    :
}

# ----------------------------------------------------------------------
# 3️⃣ Package – install the Python package and all auxiliary files
# ----------------------------------------------------------------------
package() {
    cd "$srcdir/$pkgname"

    # Install the Python package into $pkgdir/usr
    python -m pip install --root="$pkgdir" --prefix=/usr .

    # ---- Launchers ----------------------------------------------------
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

    # ---- Systemd service ------------------------------------------------
    install -Dm644 "install/wakka-shutdown.service" "$pkgdir/usr/lib/systemd/system/wakka-shutdown.service"

    # ---- Desktop entry -------------------------------------------------
    install -Dm644 "install/wakka.desktop" "$pkgdir/usr/share/applications/wakka.desktop"

    # ---- MIME type definition -------------------------------------------
    install -Dm644 "install/wakka-mime.xml" "$pkgdir/usr/share/mime/packages/wakka-mime.xml"

    # ---- Polkit rule ----------------------------------------------------
    install -Dm644 "install/10-wakka.rules" "$pkgdir/usr/share/polkit-1/rules.d/10-wakka.rules"

    # ---- Icons -----------------------------------------------------------
    # Scalable SVG
    install -Dm644 "ui/assets/wakka.svg" "$pkgdir/usr/share/icons/hicolor/scalable/apps/wakka.svg"

    # PNGs generated from the Qt SVG (requires PyQt6 at build time)
    DESTDIR="$pkgdir" PREFIX="/usr" python - <<'PYICON'
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), '..')))
try:
    from wakka.ui.styles.icons import get_logo_icon
except Exception as e:
    print(f"Warning: Could not import get_logo_icon: {e}", file=sys.stderr)
    sys.exit(0)   # Skip PNG generation if the import fails

sizes = [16, 22, 32, 48, 64, 128, 256]
for s in sizes:
    out_dir = f"{os.getenv('DESTDIR')}/usr/share/icons/hicolor/{s}x{s}/apps"
    os.makedirs(out_dir, exist_ok=True)
    icon = get_logo_icon(s)
    pixmap = icon.pixmap(s, s)
    pixmap.save(f"{out_dir}/wakka.png", "PNG")
PYICON
}