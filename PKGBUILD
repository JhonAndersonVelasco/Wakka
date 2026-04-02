# Maintainer: Jhon Velasco <jhandervelbux@gmail.com>
# PKGBUILD for the Wakka system packages management tool.

pkgname=wakka
pkgver=0.1
pkgrel=1
pkgdesc="Wakka – a system packages management utility"
arch=('x86_64')
url="https://github.com/JhonAndersonVelasco/Wakka"
license=('GPL3')
depends=('python-pyqt6'
         'python-apscheduler'
         'python-dbus'
         'python-pydbus'
         'python-requests'
         'python-packaging'
         'python-psutil')

makedepends=()

source=("wakka-${pkgver}.tar.gz::https://github.com/JhonAndersonVelasco/Wakka/archive/refs/tags/v${pkgver}.tar.gz")

sha256sums=('SKIP')

install=(wakka.install)

package() {
  local _src="$srcdir/Wakka-${pkgver}/main"

  # Crear directorios necesarios
  install -d "$pkgdir/usr/lib/wakka"
  install -d "$pkgdir/usr/lib/wakka/core"
  install -d "$pkgdir/usr/lib/wakka/core/systemd"
  install -d "$pkgdir/usr/lib/wakka/ui"
  install -d "$pkgdir/usr/lib/wakka/ui/i18n"
  install -d "$pkgdir/usr/lib/wakka/ui/pages"
  install -d "$pkgdir/usr/lib/wakka/ui/styles"
  install -d "$pkgdir/usr/lib/wakka/ui/tray"
  install -d "$pkgdir/usr/lib/wakka/ui/widgets"
  install -d "$pkgdir/usr/share/icons/hicolor/scalable/apps/"

  # Instalar el script principal
  install -m644 "$_src/__init__.py" "$pkgdir/usr/lib/wakka/__init__.py"
  install -m755 "$_src/main.py" "$pkgdir/usr/lib/wakka/main.py"

  # Instalar scripts
  install -m644 "$_src/core/__init__.py" "$pkgdir/usr/lib/wakka/core"
  install -m644 "$_src/core/askpass.py" "$pkgdir/usr/lib/wakka/core"
  install -m644 "$_src/core/cache_manager.py" "$pkgdir/usr/lib/wakka/core"
  install -m644 "$_src/core/config_manager.py" "$pkgdir/usr/lib/wakka/core"
  install -m644 "$_src/core/constants.py" "$pkgdir/usr/lib/wakka/core"
  install -m644 "$_src/core/package_manager.py" "$pkgdir/usr/lib/wakka/core"
  install -m644 "$_src/core/privilege_helper.py" "$pkgdir/usr/lib/wakka/core"
  install -m644 "$_src/core/repo_manager.py" "$pkgdir/usr/lib/wakka/core"
  install -m644 "$_src/core/scheduler.py" "$pkgdir/usr/lib/wakka/core"
  install -m644 "$_src/core/systemd/__init__.py" "$pkgdir/usr/lib/wakka/core/systemd"
  install -m644 "$_src/core/systemd/shutdown_handler.py" "$pkgdir/usr/lib/wakka/core/systemd"

  install -m644 "$_src/ui/__init__.py" "$pkgdir/usr/lib/wakka/ui"
  install -m644 "$_src/ui/main_window.py" "$pkgdir/usr/lib/wakka/ui"
  install -m644 "$_src/ui/i18n/wakka_en.qm" "$pkgdir/usr/lib/wakka/ui/i18n"
  install -m644 "$_src/ui/i18n/wakka_en.ts" "$pkgdir/usr/lib/wakka/ui/i18n"
  install -m644 "$_src/ui/i18n/wakka_es.qm" "$pkgdir/usr/lib/wakka/ui/i18n"
  install -m644 "$_src/ui/i18n/wakka_es.ts" "$pkgdir/usr/lib/wakka/ui/i18n"
  install -m644 "$_src/ui/pages/__init__.py" "$pkgdir/usr/lib/wakka/ui/pages"
  install -m644 "$_src/ui/pages/browse_page.py" "$pkgdir/usr/lib/wakka/ui/pages"
  install -m644 "$_src/ui/pages/cache_page.py" "$pkgdir/usr/lib/wakka/ui/pages"
  install -m644 "$_src/ui/pages/help_page.py" "$pkgdir/usr/lib/wakka/ui/pages"
  install -m644 "$_src/ui/pages/installed_page.py" "$pkgdir/usr/lib/wakka/ui/pages"
  install -m644 "$_src/ui/pages/settings_page.py" "$pkgdir/usr/lib/wakka/ui/pages"
  install -m644 "$_src/ui/pages/updates_page.py" "$pkgdir/usr/lib/wakka/ui/pages"
  install -m644 "$_src/ui/styles/__init__.py" "$pkgdir/usr/lib/wakka/ui/styles"
  install -m644 "$_src/ui/styles/icons.py" "$pkgdir/usr/lib/wakka/ui/styles"
  install -m644 "$_src/ui/styles/theme.py" "$pkgdir/usr/lib/wakka/ui/styles"
  install -m644 "$_src/ui/tray/__init__.py" "$pkgdir/usr/lib/wakka/ui/tray"
  install -m644 "$_src/ui/tray/tray_icon.py" "$pkgdir/usr/lib/wakka/ui/tray"
  install -m644 "$_src/ui/widgets/__init__.py" "$pkgdir/usr/lib/wakka/ui/widgets"
  install -m644 "$_src/ui/widgets/package_card.py" "$pkgdir/usr/lib/wakka/ui/widgets"
  install -m644 "$_src/ui/widgets/package_info_dialog.py" "$pkgdir/usr/lib/wakka/ui/widgets"
  install -m644 "$_src/ui/widgets/progress_overlay.py" "$pkgdir/usr/lib/wakka/ui/widgets"
  install -m644 "$_src/ui/widgets/terminal_widget.py" "$pkgdir/usr/lib/wakka/ui/widgets"

  # Crear script ejecutable en /usr/bin
  install -d "$pkgdir/usr/bin"
  cat > "$pkgdir/usr/bin/wakka" << 'EOF'
#!/bin/bash
exec /usr/bin/python /usr/lib/wakka/main.py "$@"
EOF
  chmod +x "$pkgdir/usr/bin/wakka"

  # Instalar iconos
  install -Dm644 "$_src/ui/assets/wakka.svg" "$pkgdir/usr/share/icons/hicolor/scalable/apps/"

  # Instalar archivo .desktop
  install -Dm644 "$_src/install/wakka.desktop" "$pkgdir/usr/share/applications/"

  # Instalar archivo autostart .desktop
  install -Dm644 "$_src/install/wakka-autostart.desktop" "$pkgdir/etc/skel/.config/autostart/"

  # Instalar tipos mime
  install -Dm644 "$_src/install/wakka-mime.xml" "$pkgdir/usr/share/mime/packages/"

  # Reglas Polkit
  install -Dm644 "$_src/install/10-wakka.rules" "$pkgdir/usr/share/polkit-1/rules.d/"

  # Servicio de instalación al apagar
  install -Dm644 "$_src/install/wakka-shutdown.service" "$pkgdir/usr/lib/systemd/system/"

}
