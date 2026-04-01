"""
Wakka — Visual Theme (QSS)
Dark and light themes with design tokens.
Provides centralized styling functions for consistent UI appearance.
"""
from __future__ import annotations

from typing import Literal

ThemeMode = Literal["dark", "light"]

# ─── Current Theme State ──────────────────────────────────────────────────────
_current_theme: ThemeMode = "dark"


def get_current_theme() -> ThemeMode:
    """Get the currently active theme mode."""
    return _current_theme


def set_current_theme(theme: ThemeMode) -> None:
    """Set the current theme mode."""
    global _current_theme
    _current_theme = theme if theme in COLORS else "dark"


def get_color(key: str, theme: ThemeMode | None = None) -> str:
    """
    Get a color value from the theme palette.

    Args:
        key: Color token name (e.g., 'text_primary', 'accent', 'bg_card')
        theme: Theme mode, defaults to current theme if None

    Returns:
        Color value as a string (hex or rgba)
    """
    t = theme or _current_theme
    colors = COLORS.get(t, COLORS["dark"])
    return colors.get(key, colors.get("text_primary", "#ffffff"))


def get_colors(theme: ThemeMode | None = None) -> dict[str, str]:
    """Get the full color palette for a theme."""
    t = theme or _current_theme
    return COLORS.get(t, COLORS["dark"])


# ─── Style Helper Functions ───────────────────────────────────────────────────

def style_text(
    color_key: str = "text_primary",
    size: int | None = None,
    weight: str | None = None,
    extra: str = "",
    theme: ThemeMode | None = None,
) -> str:
    """
    Generate a stylesheet string for text styling.

    Args:
        color_key: Color token name
        size: Font size in pixels
        weight: Font weight (e.g., '500', '600', 'bold')
        extra: Additional CSS properties
        theme: Theme mode, defaults to current theme
    """
    parts = [f"color: {get_color(color_key, theme)};"]
    if size:
        parts.append(f"font-size: {size}px;")
    if weight:
        parts.append(f"font-weight: {weight};")
    if extra:
        parts.append(extra)
    return " ".join(parts)


def style_status(status: str = "success", size: int = 11, theme: ThemeMode | None = None) -> str:
    """
    Generate stylesheet for status indicators.

    Args:
        status: One of 'success', 'warning', 'danger', 'info'
        size: Font size in pixels
        theme: Theme mode
    """
    color_key = {
        "success": "success",
        "warning": "warning",
        "danger": "danger",
        "error": "danger",
        "info": "info",
    }.get(status, "text_secondary")
    return f"color: {get_color(color_key, theme)}; font-size: {size}px;"


def style_card(theme: ThemeMode | None = None) -> str:
    """Generate stylesheet for card-like containers."""
    c = get_colors(theme)
    return f"""
        background-color: {c['bg_card']};
        border: 1px solid {c['border']};
        border-radius: 12px;
        padding: 14px 16px;
    """


def style_transparent_bg() -> str:
    """Generate stylesheet for transparent backgrounds."""
    return "background: transparent;"


def style_separator(theme: ThemeMode | None = None) -> str:
    """Generate stylesheet for separators/dividers."""
    return f"color: {get_color('border', theme)};"


def style_icon_text(size: int = 48, theme: ThemeMode | None = None) -> str:
    """Generate stylesheet for icon-sized text (emoji icons, etc.)."""
    return f"font-size: {size}px;"


def style_title(size: int = 18, theme: ThemeMode | None = None) -> str:
    """Generate stylesheet for titles."""
    return style_text("text_primary", size=size, weight="600", theme=theme)


def style_subtitle(size: int = 13, theme: ThemeMode | None = None) -> str:
    """Generate stylesheet for subtitles/secondary text."""
    return style_text("text_secondary", size=size, theme=theme)


def style_label(size: int = 11, uppercase: bool = False, theme: ThemeMode | None = None) -> str:
    """Generate stylesheet for small labels."""
    base = style_text("text_secondary", size=size, weight="600", theme=theme)
    if uppercase:
        base += " text-transform: uppercase; letter-spacing: 0.5px;"
    return base


def style_accent_label(size: int = 10, theme: ThemeMode | None = None) -> str:
    """Generate stylesheet for accent-colored labels."""
    return style_text("accent", size=size, weight="600", theme=theme)


def style_loading(theme: ThemeMode | None = None) -> str:
    """Generate stylesheet for loading indicators."""
    return style_text("text_secondary", size=14, extra="padding: 40px;", theme=theme)


def style_overlay_logo(theme: ThemeMode | None = None) -> str:
    """Generate stylesheet for overlay logo text."""
    return style_text("accent_light", size=28, weight="700", extra="letter-spacing: 2px;", theme=theme)


def style_overlay_status(theme: ThemeMode | None = None) -> str:
    """Generate stylesheet for overlay status text."""
    return style_text("text_primary", size=16, weight="500", theme=theme)


def style_overlay_package(theme: ThemeMode | None = None) -> str:
    """Generate stylesheet for overlay package label."""
    return style_text("text_secondary", size=12, theme=theme)


def style_browser(theme: ThemeMode | None = None) -> str:
    """Generate stylesheet for text browsers (info dialogs)."""
    c = get_colors(theme)
    return f"""
        QTextBrowser {{
            background-color: {c['bg_input']};
            border: 1px solid {c['border']};
            border-radius: 8px;
            padding: 12px;
            color: {c['text_primary']};
            font-size: 13px;
        }}
        QTextBrowser a {{
            color: {c['accent_light']};
        }}
    """


def style_progress_bar(theme: ThemeMode | None = None) -> str:
    """Generate stylesheet for progress bars in overlays."""
    c = get_colors(theme)
    return f"""
        QProgressBar {{
            background-color: {c['bg_card']};
            border: none;
            border-radius: 6px;
            height: 8px;
            text-align: center;
            color: transparent;
        }}
        QProgressBar::chunk {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {c['accent_dark']}, stop:1 {c['accent_light']});
            border-radius: 6px;
        }}
    """


def style_ai_card(theme: ThemeMode | None = None) -> str:
    """Generate stylesheet for AI feature cards."""
    c = get_colors(theme)
    return f"""
        background-color: {c['accent_glow']};
        border: 1px solid {c['accent']};
        border-radius: 8px;
        padding: 10px;
    """


def style_terminal_header(theme: ThemeMode | None = None) -> str:
    """Generate stylesheet for terminal header elements."""
    return style_text("text_secondary", size=12, weight="600", theme=theme)


def style_terminal_status(color: str | None = None, theme: ThemeMode | None = None) -> str:
    """Generate stylesheet for terminal status labels."""
    if color:
        return f"color: {color}; font-size: 11px;"
    return style_text("accent", size=11, theme=theme)


def style_filter_border(theme: ThemeMode | None = None) -> str:
    """Generate stylesheet for filter row borders."""
    return f"border-bottom: 1px solid {get_color('border', theme)};"


def style_menu(theme: ThemeMode | None = None) -> str:
    """Generate stylesheet for context menus (tray, etc.)."""
    c = get_colors(theme)
    return f"""
        QMenu {{
            background-color: {c['bg_card']};
            border: 1px solid {c['border']};
            border-radius: 8px;
            padding: 6px 0;
            color: {c['text_primary']};
        }}
        QMenu::item {{
            padding: 8px 24px;
        }}
        QMenu::item:selected {{
            background-color: {c['accent_glow']};
            color: {c['accent_light']};
        }}
        QMenu::separator {{
            height: 1px;
            background: {c['border']};
            margin: 4px 12px;
        }}
    """


def style_askpass_dialog(theme: ThemeMode | None = None) -> str:
    """Generate stylesheet for password dialog."""
    c = get_colors(theme)
    return f"""
        QDialog {{
            background-color: {c['bg_surface']};
        }}
        QLineEdit {{
            background-color: {c['bg_input']};
            border: 1px solid {c['border']};
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 14px;
            color: {c['text_primary']};
        }}
        QLineEdit:focus {{
            border-color: {c['accent']};
        }}
        QPushButton {{
            background-color: {c['accent']};
            border: none;
            border-radius: 8px;
            color: white;
            padding: 10px 24px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {c['accent_light']};
        }}
        QPushButton:pressed {{
            background-color: {c['accent_dark']};
        }}
    """


# ─── Color Tokens ─────────────────────────────────────────────────────────────

COLORS = {
    "dark": {
        # Backgrounds
        "bg_base":        "#0f1117",
        "bg_surface":     "#161b27",
        "bg_card":        "#1c2333",
        "bg_card_hover":  "#212840",
        "bg_sidebar":     "#111520",
        "bg_input":       "#1a2035",
        "bg_header":      "#12161f",

        # Accents
        "accent":         "#7c6af7",
        "accent_light":   "#9d8fff",
        "accent_dark":    "#5c4ed6",
        "accent_glow":    "rgba(124,106,247,0.20)",

        # State colors
        "success":        "#2dd98a",
        "warning":        "#f5a623",
        "danger":         "#f05252",
        "info":           "#38bdf8",
        "aur_badge":      "#e8a849",

        # Text
        "text_primary":   "#e8ecf4",
        "text_secondary": "#8892a4",
        "text_disabled":  "#4a5568",
        "text_on_accent": "#ffffff",

        # Borders
        "border":         "rgba(255,255,255,0.07)",
        "border_focus":   "#7c6af7",

        # Scrollbar
        "scroll_track":   "#161b27",
        "scroll_thumb":   "#2d3651",
    },
    "light": {
        "bg_base":        "#f0f4ff",
        "bg_surface":     "#ffffff",
        "bg_card":        "#f8f9ff",
        "bg_card_hover":  "#eef1ff",
        "bg_sidebar":     "#e8ecff",
        "bg_input":       "#ffffff",
        "bg_header":      "#f0f4ff",

        "accent":         "#7c6af7",
        "accent_light":   "#9d8fff",
        "accent_dark":    "#5c4ed6",
        "accent_glow":    "rgba(124,106,247,0.15)",

        "success":        "#16a34a",
        "warning":        "#d97706",
        "danger":         "#dc2626",
        "info":           "#0284c7",
        "aur_badge":      "#b45309",

        "text_primary":   "#1a1f36",
        "text_secondary": "#4b5563",
        "text_disabled":  "#9ca3af",
        "text_on_accent": "#ffffff",

        "border":         "rgba(0,0,0,0.08)",
        "border_focus":   "#7c6af7",

        "scroll_track":   "#f0f4ff",
        "scroll_thumb":   "#c7d0e8",
    },
}


def build_qss(theme: str = "dark") -> str:
    c = COLORS.get(theme, COLORS["dark"])

    return f"""
/* ═══ Global ══════════════════════════════════════════════════════════════ */
* {{
    font-family: 'Inter', 'Noto Sans', 'Segoe UI', sans-serif;
    font-size: 13px;
    outline: none;
}}

QApplication, QMainWindow, QDialog {{
    background-color: {c['bg_base']};
    color: {c['text_primary']};
}}

/* ═══ Main Window ══════════════════════════════════════════════════════════ */
#MainWindow {{
    background-color: {c['bg_base']};
}}

/* ═══ Sidebar ══════════════════════════════════════════════════════════════ */
#Sidebar {{
    background-color: {c['bg_sidebar']};
    border-right: 1px solid {c['border']};
    min-width: 220px;
    max-width: 220px;
}}

#SidebarLogo {{
    font-size: 22px;
    font-weight: 700;
    color: {c['accent']};
    padding: 24px 20px 16px 20px;
    letter-spacing: 1px;
}}

#SidebarVersion {{
    font-size: 10px;
    color: {c['text_disabled']};
    padding: 0 20px 20px 20px;
}}

/* Nav buttons */
#NavButton {{
    background: transparent;
    border: none;
    border-radius: 10px;
    color: {c['text_secondary']};
    font-size: 13px;
    font-weight: 500;
    padding: 10px 14px;
    margin: 2px 10px;
    text-align: left;
    qproperty-iconSize: 18px 18px;
}}

#NavButton:hover {{
    background-color: {c['bg_card']};
    color: {c['text_primary']};
}}

#NavButton[active="true"] {{
    background-color: {c['accent_glow']};
    color: {c['accent_light']};
    border-left: 3px solid {c['accent']};
}}

/* ═══ Header ════════════════════════════════════════════════════════════════ */
#Header {{
    background-color: {c['bg_header']};
    border-bottom: 1px solid {c['border']};
    padding: 12px 20px;
    min-height: 60px;
    max-height: 60px;
}}

#PageTitle {{
    font-size: 18px;
    font-weight: 700;
    color: {c['text_primary']};
}}

/* ═══ Search Bar ════════════════════════════════════════════════════════════ */
#SearchBar {{
    background-color: {c['bg_input']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    color: {c['text_primary']};
    padding: 8px 14px 8px 36px;
    font-size: 13px;
    min-width: 200px;
}}

#SearchBar:focus {{
    border-color: {c['border_focus']};
    background-color: {c['bg_card']};
}}

#SearchBar::placeholder {{
    color: {c['text_disabled']};
}}

/* ═══ Package Cards ═════════════════════════════════════════════════════════ */
#PackageCard {{
    background-color: {c['bg_card']};
    border: 1px solid {c['border']};
    border-radius: 12px;
    padding: 14px 16px;
    margin: 3px 0;
}}

#PackageCard:hover {{
    background-color: {c['bg_card_hover']};
    border-color: {c['accent_glow']};
}}

#PackageCard[selected="true"] {{
    border-color: {c['accent']};
    background-color: {c['accent_glow']};
}}

#PkgName {{
    font-size: 14px;
    font-weight: 600;
    color: {c['text_primary']};
}}

#PkgVersion {{
    font-size: 11px;
    color: {c['text_secondary']};
}}

#PkgDesc {{
    font-size: 12px;
    color: {c['text_secondary']};
    margin-top: 2px;
}}

/* Source badges */
#BadgeAUR {{
    background-color: rgba(232,168,73,0.20);
    color: {c['aur_badge']};
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 10px;
    font-weight: 700;
}}

#BadgeOfficial {{
    background-color: rgba(124,106,247,0.20);
    color: {c['accent_light']};
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 10px;
    font-weight: 700;
}}

#BadgeInstalled {{
    background-color: rgba(45,217,138,0.18);
    color: {c['success']};
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 10px;
    font-weight: 700;
}}

/* ═══ Buttons ═══════════════════════════════════════════════════════════════ */
QPushButton {{
    background-color: {c['bg_card']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    color: {c['text_primary']};
    padding: 8px 16px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {c['bg_card_hover']};
    border-color: {c['accent']};
    color: {c['accent_light']};
}}

QPushButton:pressed {{
    background-color: {c['accent_dark']};
    color: white;
}}

QPushButton:disabled {{
    color: {c['text_disabled']};
    border-color: {c['border']};
}}

#PrimaryButton {{
    background-color: {c['accent']};
    border: none;
    color: white;
    font-weight: 600;
    border-radius: 8px;
    padding: 9px 20px;
}}

#PrimaryButton:hover {{
    background-color: {c['accent_light']};
    color: white;
}}

#PrimaryButton:pressed {{
    background-color: {c['accent_dark']};
}}

#DangerButton {{
    background-color: transparent;
    border: 1px solid {c['danger']};
    color: {c['danger']};
    border-radius: 8px;
    padding: 8px 16px;
}}

#DangerButton:hover {{
    background-color: {c['danger']};
    color: white;
}}

#SuccessButton {{
    background-color: {c['success']};
    border: none;
    color: white;
    font-weight: 600;
    border-radius: 8px;
    padding: 9px 20px;
}}

#SuccessButton:hover {{
    background-color: #4ae89a;
    color: white;
}}

/* ═══ Terminal Widget ═══════════════════════════════════════════════════════ */
#TerminalWidget {{
    background-color: #0a0d14;
    border-top: 1px solid {c['border']};
    border-radius: 0;
}}

#TerminalOutput {{
    background-color: #0a0d14;
    color: #c8d0e0;
    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
    font-size: 12px;
    border: none;
    padding: 10px;
}}

/* ═══ Tabs / Filters ═══════════════════════════════════════════════════════ */
#FilterTab {{
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    color: {c['text_secondary']};
    padding: 8px 16px;
    font-weight: 500;
}}

#FilterTab:hover {{
    color: {c['text_primary']};
}}

#FilterTab[active="true"] {{
    color: {c['accent_light']};
    border-bottom: 2px solid {c['accent']};
}}

/* ═══ Inputs & Combos ══════════════════════════════════════════════════════ */
QLineEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {c['bg_input']};
    border: 1px solid {c['border']};
    border-radius: 7px;
    color: {c['text_primary']};
    padding: 7px 12px;
    selection-background-color: {c['accent']};
}}

QLineEdit:focus, QSpinBox:focus {{
    border-color: {c['border_focus']};
}}

QComboBox {{
    background-color: {c['bg_input']};
    border: 1px solid {c['border']};
    border-radius: 7px;
    color: {c['text_primary']};
    padding: 7px 12px;
    min-width: 150px;
}}

QComboBox:focus {{
    border-color: {c['border_focus']};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {c['bg_input']};
    border: 1px solid {c['border']};
    color: {c['text_primary']};
    selection-background-color: {c['accent']};
    outline: none;
    border-radius: 8px;
    padding: 4px 0;
}}

/* ═══ Checkboxes and Toggles ═══════════════════════════════════════════════ */
QCheckBox {{
    color: {c['text_primary']};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid {c['border']};
    background-color: {c['bg_input']};
}}

QCheckBox::indicator:checked {{
    background-color: {c['accent']};
    border-color: {c['accent']};
    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMiA2TDUgOUwxMCAzIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPjwvc3ZnPg==);
}}

QCheckBox::indicator:hover {{
    border-color: {c['accent']};
}}

QRadioButton {{
    color: {c['text_primary']};
    spacing: 10px;
}}

QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 1px solid {c['border']};
    background-color: {c['bg_input']};
}}

QRadioButton::indicator:checked {{
    background-color: {c['accent']};
    border-color: {c['accent']};
}}

QRadioButton::indicator:hover {{
    border-color: {c['accent']};
}}

/* ═══ Scrollbars ════════════════════════════════════════════════════════════ */
QScrollBar:vertical {{
    background: {c['scroll_track']};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {c['scroll_thumb']};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {c['accent']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background: {c['scroll_track']};
    height: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal {{
    background: {c['scroll_thumb']};
    border-radius: 4px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {c['accent']};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ═══ List Views ════════════════════════════════════════════════════════════ */
QListWidget, QTreeWidget, QTableWidget {{
    background-color: transparent;
    border: none;
    color: {c['text_primary']};
    outline: none;
}}

QListWidget::item {{
    border-radius: 8px;
    padding: 4px;
}}

QListWidget::item:selected {{
    background-color: {c['accent_glow']};
    color: {c['accent_light']};
}}

QHeaderView::section {{
    background-color: {c['bg_surface']};
    color: {c['text_secondary']};
    border: none;
    border-bottom: 1px solid {c['border']};
    padding: 8px;
    font-weight: 600;
    font-size: 11px;
}}

/* ═══ Progress Bar ══════════════════════════════════════════════════════════ */
QProgressBar {{
    background-color: {c['bg_card']};
    border: none;
    border-radius: 6px;
    height: 8px;
    text-align: center;
    color: transparent;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {c['accent_dark']}, stop:1 {c['accent_light']});
    border-radius: 6px;
}}

/* ═══ Tooltips ═══════════════════════════════════════════════════════════════ */
QToolTip {{
    background-color: {c['bg_input']};
    border: 1px solid {c['bg_card_hover']};
    color: {c['text_primary']};
    padding: 6px 10px;
}}

/* ═══ Splitter ═══════════════════════════════════════════════════════════════ */
QSplitter::handle {{
    background-color: {c['border']};
}}

QSplitter::handle:horizontal {{
    width: 1px;
}}

QSplitter::handle:vertical {{
    height: 1px;
}}

/* ═══ Group Box ══════════════════════════════════════════════════════════════ */
QGroupBox {{
    border: 1px solid {c['border']};
    border-radius: 10px;
    margin-top: 16px;
    padding: 12px 10px 10px 10px;
    color: {c['text_secondary']};
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: {c['text_secondary']};
}}

/* ═══ Dialogs ════════════════════════════════════════════════════════════════ */
QDialog {{
    background-color: {c['bg_surface']};
}}

QMessageBox {{
    background-color: {c['bg_surface']};
    color: {c['text_primary']};
}}

/* ═══ Status Labels ══════════════════════════════════════════════════════════ */
#StatusSuccess {{
    color: {c['success']};
    font-weight: 600;
}}

#StatusError {{
    color: {c['danger']};
    font-weight: 600;
}}

#StatusWarning {{
    color: {c['warning']};
    font-weight: 600;
}}

#StatusInfo {{
    color: {c['info']};
}}

/* ═══ Section Headers ════════════════════════════════════════════════════════ */
#SectionHeader {{
    font-size: 12px;
    font-weight: 700;
    color: {c['text_disabled']};
    text-transform: uppercase;
    letter-spacing: 1px;
    padding: 8px 0 4px 0;
}}

/* ═══ Cache Page Specific ════════════════════════════════════════════════════ */
#CacheSizeLabel {{
    font-size: 32px;
    font-weight: 700;
    color: {c['accent']};
}}

#CacheSizeSub {{
    font-size: 12px;
    color: {c['text_secondary']};
}}

/* ═══ Update Badge ═══════════════════════════════════════════════════════════ */
#UpdateBadge {{
    background-color: {c['danger']};
    color: white;
    border-radius: 9px;
    padding: 0 5px;
    font-size: 10px;
    font-weight: 800;
    min-width: 18px;
    height: 18px;
}}
"""
