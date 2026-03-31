# Wakka — Administrador de paquetes para Arch Linux

<div align="center">

**Wakka** es un administrador de paquetes gráfico moderno para Arch Linux, basado en `yay`, inspirado en Pamac.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![PyQt6](https://img.shields.io/badge/PyQt6-6.6%2B-green?style=flat-square&logo=qt)
![Arch Linux](https://img.shields.io/badge/Arch_Linux-compatible-1793d1?style=flat-square&logo=archlinux)
![License](https://img.shields.io/badge/License-GPL--3.0-red?style=flat-square)

</div>

---

## ✨ Características

| Función | Descripción |
|---------|-------------|
| 🔍 **Explorar y buscar** | Búsqueda simultánea en repos oficiales y AUR via `yay` |
| 📦 **Instalar / Desinstalar** | Gestión completa de paquetes con salida en tiempo real |
| ⬆️ **Actualizaciones** | Lista de updates disponibles, actualizar todo o individual |
| 🗓️ **Programación** | Búsqueda automática periódica (horaria/diaria/semanal/mensual) |
| 🧹 **Caché** | Limpieza de caché de pacman y AUR, paquetes huérfanos |
| ⚙️ **pacman.conf** | Edición de `IgnorePkg`, descargas paralelas, repositorios |
| 🔌 **Repositorios** | Añadir/eliminar/habilitar repos adicionales (ej: chaotic-aur) |
| 🛎️ **Bandeja del sistema** | Monitoreo continuo de actualizaciones con badge en el icono |
| ⚡ **Updates al apagar** | Instala actualizaciones antes del apagado via servicio systemd |
| 🌍 **Multi-idioma** | Español e inglés incluidos, traducible por la comunidad |
| 🌙 **Tema oscuro/claro** | Diseño moderno con tema oscuro por defecto |

---

## 📋 Requisitos

### Sistema
- Arch Linux (o derivado)
- `yay` o `paru` (AUR helper)
- `polkit` (operaciones privilegiadas sin ejecutar la app como root)
- `pacman-contrib` (para `paccache`)

### Python
```
python >= 3.10
python-pyqt6 >= 6.6
qt6-svg
```

### Opcionales
```
python-apscheduler   # Actualizaciones programadas
python-dbus          # Inhibit lock al apagar
python-pydbus        # D-Bus alternativo
plymouth             # Pantalla gráfica al apagar
```

---

## 🚀 Instalación

### Desde AUR (recomendado)
```bash
yay -S wakka
```

### Manual (desde source)
```bash
git clone https://github.com/jhon/wakka.git
cd wakka
pip install -e .   # Instalación en modo desarrollo
# O:
sudo bash install/install.sh
```

---

## ▶️ Uso

```bash
# Iniciar la aplicación
wakka

# O como módulo Python
python -m wakka
```

La app arranca en la **bandeja del sistema** automáticamente con el login.

---

## 🔧 Actualizaciones al apagar

Para habilitar la instalación de updates al apagar/reiniciar:

```bash
# Habilitarlo desde Configuración > Actualizaciones al apagar
# O manualmente:
sudo systemctl enable wakka-shutdown.service
```

**Funcionamiento:**
1. Al apagar/reiniciar, systemd lanza `wakka-shutdown.service`
2. El servicio verifica si hay actualizaciones pendientes
3. Si hay updates y se tiene Plymouth instalado → muestra mensaje en Plymouth
4. Si no hay Plymouth → muestra overlay Qt a pantalla completa
5. Instala las actualizaciones con `yay -Syu --noconfirm`
6. El apagado continúa normalmente

---

## 🌍 Traducciones

Las traducciones se encuentran en `wakka/i18n/`. Para agregar un idioma:

```bash
# 1. Copiar la plantilla
cp wakka/i18n/wakka_en.ts wakka/i18n/wakka_fr.ts

# 2. Editar el archivo .ts con Qt Linguist o un editor de texto

# 3. Compilar
lrelease wakka/i18n/wakka_fr.ts

# 4. Colocar el .qm en el mismo directorio
```

---

## 🗂️ Estructura del proyecto

```
wakka/
├── core/              # Backend: package_manager, cache, config, repos, scheduler
├── ui/
│   ├── pages/         # Páginas: actualizaciones, instalados, explorar, caché, config
│   ├── widgets/       # Terminal, PackageCard, ShutdownOverlay
│   └── styles/        # QSS theme + iconos SVG embebidos
├── tray/              # Bandeja del sistema
├── systemd/           # Integración con systemd/Plymouth
└── i18n/              # Archivos de traducción .ts/.qm
install/
├── wakka.desktop
├── wakka-autostart.desktop
├── wakka-shutdown.service
└── install.sh
PKGBUILD
```

---

## 🤝 Contribuir

1. Fork del repositorio
2. Crea una rama: `git checkout -b feature/mi-feature`
3. Haz commit de tus cambios
4. Abre un Pull Request

---

## 📄 Licencia

GPL-3.0 © 2026 jhon
