# Maintainer: Wakka Team <https://github.com/jhon/wakka>

pkgname=wakka
pkgver=1.0.0
pkgrel=2
install=src/wakka.install
pkgdesc="Modern graphical package manager for Arch Linux with AI integration"
arch=('any')
url="https://github.com/jhon/wakka"
license=('GPL')
depends=('appimage-thumbnailer'
         'binutils'
         'python-beautifulsoup4' 
         'python-lxml' 
         'python-pyqt6' 
         'python-requests' 
         'yay' 
         'polkit' 
         'pacman-contrib'
         'squashfs-tools')
makedepends=()
source=("wakka"
        "wakka.desktop")
sha256sums=('SKIP'
            'SKIP')

package() {
  # 1. Código del programa en /opt
  install -d "${pkgdir}/opt/wakka"
  cp -r "${srcdir}/core" "${srcdir}/gui" "${srcdir}/i18n" "${srcdir}/main.py" "${srcdir}/resources" "${pkgdir}/opt/wakka/"
  find "${pkgdir}/opt/wakka" -name "__pycache__" -type d -exec rm -rf {} +

  # 2. Scripts ejecutables
  install -Dm755 "${srcdir}/wakka" "${pkgdir}/usr/bin/wakka"
  install -Dm755 "${srcdir}/resources/wakka-helper" "${pkgdir}/usr/bin/wakka-helper"
  install -Dm755 "${srcdir}/resources/wakka-background-helper" "${pkgdir}/usr/bin/wakka-background-helper"
  install -Dm755 "${srcdir}/resources/wakka-cache-helper" "${pkgdir}/usr/bin/wakka-cache-helper"
  install -Dm755 "${srcdir}/resources/wakka-service-helper" "${pkgdir}/usr/bin/wakka-service-helper"
  install -Dm755 "${srcdir}/resources/wakka-shutdown-helper" "${pkgdir}/usr/bin/wakka-shutdown-helper"


  # 3. Integración con el escritorio
  install -Dm644 "${srcdir}/wakka.desktop" "${pkgdir}/usr/share/applications/wakka.desktop"
  install -Dm644 "${srcdir}/resources/wakka.svg" "${pkgdir}/usr/share/icons/hicolor/scalable/apps/wakka.svg"

  # 4. Políticas de Polkit
  install -Dm644 "${srcdir}/resources/com.wakka.package-manager.policy" \
    "${pkgdir}/usr/share/polkit-1/actions/com.wakka.package-manager.policy"
  install -Dm644 "${srcdir}/resources/com.wakka.package-background.policy" \
    "${pkgdir}/usr/share/polkit-1/actions/com.wakka.package-background.policy"
  install -Dm644 "${srcdir}/resources/com.wakka.package-cleaner.policy" \
    "${pkgdir}/usr/share/polkit-1/actions/com.wakka.package-cleaner.policy"
  install -Dm644 "${srcdir}/resources/com.wakka.service-manager.policy" \
    "${pkgdir}/usr/share/polkit-1/actions/com.wakka.service-manager.policy"

  # 5. Instalador al apagar
  install -Dm644 "${srcdir}/resources/wakka-shutdown.service" \
    "${pkgdir}/etc/systemd/system/wakka-shutdown.service"
}
