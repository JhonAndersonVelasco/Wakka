"""
Wakka — Global Constants
Centralized configuration values, app metadata, and shared constants.
"""
from __future__ import annotations

# ─── Application Metadata ─────────────────────────────────────────────────────
APP_NAME = "Wakka"
APP_ID = "io.github.wakka"
APP_VERSION = "1.0.0"
APP_DOMAIN = "io.github.wakka"

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
