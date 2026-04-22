"""Parsing helpers for pacman/yay textual output (no GUI imports)."""
from __future__ import annotations

import re

_UPDATE_ARROW_RE = re.compile(r"(\S+)\s+(\S+)\s+->\s+(\S+)")


def parse_upgrade_line(line: str) -> tuple[str, str, str] | None:
    """Parse one non-empty line from checkupdates, pacman -Qu, or yay -Qua."""
    s = line.strip()
    if not s:
        return None
    m = _UPDATE_ARROW_RE.match(s)
    if not m:
        return None
    return m.group(1), m.group(2), m.group(3)
