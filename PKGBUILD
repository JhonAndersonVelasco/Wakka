# Maintainer: Jhon Velasco <jhandervelbux@gmail.com>

pkgname='wakka'
pkgver='0.1.0'
pkgrel=1
pkgdesc='Administrador de paquetes para Arch Linux'
arch=('any')
url='https://github.com/JhonAndersonVelasco/Wakka'
license=('GPL-3.0-or-later')
depends=(
    'python>=3.13'
    'python-pyqt6>=6.6.0'
    'python-apscheduler>=3.10.4'
    'python-dbus>=1.3.2'
    'python-pydbus>=0.6.0'
    'python-requests>=2.31.0'
    'python-packaging>=24.0'
    'python-psutil>=5.9.0'
)
makedepends=()
optdepends=(
    'xdg-utils: integración MIME'
)
source=('.')
sha256sums=('SKIP')

build() {
    : # No requiere compilación
}

package() {
    cd "${srcdir}/${pkgname}-${pkgver}"

    # ── Python ────────────────────────────────────────────────────────────
    _sitepkg="${pkgdir}$(python -c 'import site; print(site.getsitepackages()[0])')"
    install -dm755 "$_sitepkg/Wakka"

    # Solo módulos Python; excluir herramientas de desarrollo y artifacts
    cp -r core ui __init__.py __main__.py main.py "$_sitepkg/Wakka/"
    find "$_sitepkg/Wakka" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
    find "$_sitepkg/Wakka" -name '*.pyc' -delete 2>/dev/null || true

    # ── Ejecutable ────────────────────────────────────────────────────────
    install -dm755 "${pkgdir}/usr/bin"
    cat > "${pkgdir}/usr/bin/wakka" << 'LAUNCHER'
#!/bin/bash
exec python -m Wakka "$@"
LAUNCHER
    chmod 755 "${pkgdir}/usr/bin/wakka"

    # ── Icono ─────────────────────────────────────────────────────────────
    install -Dm644 ui/assets/wakka.svg \
        "${pkgdir}/usr/share/icons/hicolor/scalable/apps/wakka.svg"

    # ── .desktop ──────────────────────────────────────────────────────────
    install -Dm644 install/wakka.desktop \
        "${pkgdir}/usr/share/applications/wakka.desktop"
    install -Dm644 install/wakka-autostart.desktop \
        "${pkgdir}/etc/xdg/autostart/wakka-autostart.desktop"

    # ── MIME ──────────────────────────────────────────────────────────────
    install -Dm644 install/wakka-mime.xml \
        "${pkgdir}/usr/share/mime/packages/wakka-mime.xml"

    # ── Polkit ────────────────────────────────────────────────────────────
    # /usr/share/ para reglas empaquetadas; /etc/ queda para overrides del admin
    install -Dm644 install/10-wakka.rules \
        "${pkgdir}/usr/share/polkit-1/rules.d/10-wakka.rules"

    # ── Systemd ───────────────────────────────────────────────────────────
    install -Dm644 install/wakka-shutdown.service \
        "${pkgdir}/usr/lib/systemd/system/wakka-shutdown.service"

    # ── Traducciones Qt ───────────────────────────────────────────────────
    install -dm755 "${pkgdir}/usr/share/wakka/i18n"
    install -m644 ui/i18n/*.qm "${pkgdir}/usr/share/wakka/i18n/"

    # ── Docs y licencia ───────────────────────────────────────────────────
    install -Dm644 LICENSE \
        "${pkgdir}/usr/share/licenses/${pkgname}/LICENSE"
    install -Dm644 README.md \
        "${pkgdir}/usr/share/doc/${pkgname}/README.md"
}
