"""Centralized logging configuration for Wakka."""
from __future__ import annotations

import logging
import os


def configure_logging() -> None:
    level = logging.DEBUG if os.environ.get("WAKKA_DEBUG") else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")
