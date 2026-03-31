#!/usr/bin/env bash
# Wakka — System Installation Script
# Run as root or with sudo: sudo bash install.sh
# For AUR packages, this is called from PKGBUILD's package() function.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

PREFIX="${PREFIX:-/usr}"
DESTDIR="${DESTDIR:-}"

echo "==> Installing Wakka to ${DESTDIR}${PREFIX}"

# ── Python package ─────────────────────────────────────────────────────────────
echo "  -> Installing Python package..."
pip install --root="${DESTDIR:-/}" \
    --prefix="$PREFIX" \
    --no-deps \
    --no-build-isolation \
    "$ROOT_DIR" 2>/dev/null || \
python3 -m pip install \
    --root="${DESTDIR:-/}" \
    --prefix="$PREFIX" \
    --no-deps \
    "$ROOT_DIR"

# ── Executables ────────────────────────────────────────────────────────────────
echo "  -> Installing executables..."
install -Dm755 /dev/stdin "${DESTDIR}${PREFIX}/bin/wakka" << 'LAUNCHER'
#!/usr/bin/env python3
import sys
from wakka.main import main
main()
LAUNCHER

install -Dm755 /dev/stdin "${DESTDIR}${PREFIX}/bin/wakka-shutdown-helper" << 'HELPER'
#!/usr/bin/env python3
import sys
from wakka.systemd.shutdown_handler import shutdown_main
shutdown_main()
HELPER

# ── systemd service ────────────────────────────────────────────────────────────
echo "  -> Installing systemd service..."
install -Dm644 \
    "${SCRIPT_DIR}/wakka-shutdown.service" \
    "${DESTDIR}/etc/systemd/system/wakka-shutdown.service"

# ── Desktop entry ──────────────────────────────────────────────────────────────
echo "  -> Installing desktop entry..."
install -Dm644 \
    "${SCRIPT_DIR}/wakka.desktop" \
    "${DESTDIR}${PREFIX}/share/applications/wakka.desktop"

# ── MIME types ─────────────────────────────────────────────────────────────────
echo "  -> Installing MIME type definitions..."
install -Dm644 \
    "${SCRIPT_DIR}/wakka-mime.xml" \
    "${DESTDIR}${PREFIX}/share/mime/packages/wakka-mime.xml"

# ── Icon ───────────────────────────────────────────────────────────────────────
echo "  -> Installing icon..."
# Generate icon from SVG using Python (no external deps)
python3 - << 'GENICON'
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from wakka.ui.styles.icons import get_logo_icon
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    icon = get_logo_icon(256)
    sizes = [16, 22, 32, 48, 64, 128, 256]
    destdir = os.environ.get('DESTDIR', '')
    prefix = os.environ.get('PREFIX', '/usr')
    for s in sizes:
        path = f"{destdir}{prefix}/share/icons/hicolor/{s}x{s}/apps"
        os.makedirs(path, exist_ok=True)
        pixmap = icon.pixmap(s, s)
        pixmap.save(f"{path}/wakka.png", "PNG")
    print(f"Icons installed for sizes: {sizes}")
except Exception as e:
    print(f"Warning: Could not generate PNG icons: {e}", file=sys.stderr)
    # Install a fallback SVG
    svg_path = f"{os.environ.get('DESTDIR','')}{os.environ.get('PREFIX','/usr')}/share/icons/hicolor/scalable/apps"
    os.makedirs(svg_path, exist_ok=True)
    print("Skipping icon installation (PyQt6 not available at build time)")
GENICON

# ── polkit ─────────────────────────────────────────────────────────────────────
echo "  -> Installing polkit rules..."
install -Dm644 /dev/stdin \
    "${DESTDIR}/usr/share/polkit-1/rules.d/10-wakka.rules" << 'POLKIT'
/* Allow Wakka users to run paccache and pacman without password prompt */
polkit.addRule(function(action, subject) {
    var allowedActions = [
        "org.freedesktop.policykit.exec"
    ];
    if (allowedActions.indexOf(action.id) >= 0 &&
        (action.lookup("program") === "/usr/bin/paccache" ||
         action.lookup("program") === "/usr/bin/pacman") &&
        subject.isInGroup("wheel")) {
        return polkit.Result.YES;
    }
});
POLKIT

# ── Update caches ──────────────────────────────────────────────────────────────
if [ -z "${DESTDIR}" ]; then
    echo "  -> Updating system caches..."
    systemctl daemon-reload 2>/dev/null || true
    gtk-update-icon-cache -f -t "${PREFIX}/share/icons/hicolor" 2>/dev/null || true
    update-desktop-database "${PREFIX}/share/applications" 2>/dev/null || true
    update-mime-database "${PREFIX}/share/mime" 2>/dev/null || true
fi

echo ""
echo "==> Wakka installed successfully!"
echo ""
echo "    Run: wakka"
echo "    To enable updates on shutdown:"
echo "      sudo systemctl enable wakka-shutdown.service"
echo ""
