"""
Wakka — Global Constants
Centralized configuration values, app metadata, and shared constants.
"""
from __future__ import annotations

import os
from pathlib import Path

# ─── Application Metadata ─────────────────────────────────────────────────────
APP_NAME = "Wakka"
APP_ID = "io.github.wakka"
APP_VERSION = "1.0.0"
APP_DOMAIN = "io.github.wakka"

# ─── System Paths (Configurable via environment variables) ───────────────────
PACMAN_CONF_PATH = Path(os.getenv("WAKKA_PACMAN_CONF", "/etc/pacman.conf"))
SETTINGS_DIR = Path(os.getenv("WAKKA_SETTINGS_DIR", Path.home() / ".config" / "wakka"))
SETTINGS_FILE = SETTINGS_DIR / "settings.json"
STATE_FILE = Path(os.getenv("WAKKA_STATE_FILE", "/tmp/wakka_sudo_attempt"))
LOCKFILE_PATH = Path.home() / ".local" / "share" / "wakka" / ".first_run"

# ─── Cache Paths ──────────────────────────────────────────────────────────────
PACMAN_CACHE_PATH = Path("/var/cache/pacman/pkg/")
YAY_CACHE_PATH = Path.home() / ".cache" / "yay"
PARU_CACHE_PATH = Path.home() / ".cache" / "paru"

# ─── Navigation Items ─────────────────────────────────────────────────────────
# Format: (key, icon_key, default_label)
NAV_ITEMS = [
    ("updates",   "updates",   "Actualizaciones"),
    ("installed", "installed", "Instalados"),
    ("browse",    "browse",    "Explorar"),
    ("cache",     "cache",     "Caché"),
    ("settings",  "settings",  "Configuración"),
    ("help",      "info",      "Ayuda"),
]

# ─── Page Indices (for QStackedWidget) ────────────────────────────────────────
PAGE_INDEX = {
    "updates":   0,
    "installed": 1,
    "browse":    2,
    "cache":     3,
    "settings":  4,
    "help":      5,
}

# ─── Window Defaults ──────────────────────────────────────────────────────────
DEFAULT_WINDOW_SIZE = (1200, 750)
MIN_WINDOW_SIZE = (960, 660)
SIDEBAR_WIDTH = 220

# ─── Icon Sizes ───────────────────────────────────────────────────────────────
ICON_SIZE_SMALL = 16
ICON_SIZE_MEDIUM = 20
ICON_SIZE_LARGE = 24
ICON_SIZE_LOGO = 36
ICON_SIZE_LOGO_LARGE = 48

# ─── AUR Helpers ──────────────────────────────────────────────────────────────
SUPPORTED_AUR_HELPERS = ["yay", "paru"]

# ─── Security Constants ───────────────────────────────────────────────────────
MAX_SUDO_ATTEMPTS = 3
SUDO_STATE_TIMEOUT = 300  # 5 minutes in seconds