"""Tests for pacman/yay output line parsing."""
from __future__ import annotations

import unittest

from core.pacman_text import parse_upgrade_line


class TestParseUpgradeLine(unittest.TestCase):
    def test_repo_style_line(self):
        r = parse_upgrade_line("firefox 140.0-1 -> 141.0-1")
        self.assertEqual(r, ("firefox", "140.0-1", "141.0-1"))

    def test_empty_returns_none(self):
        self.assertIsNone(parse_upgrade_line(""))
        self.assertIsNone(parse_upgrade_line("   "))

    def test_malformed_returns_none(self):
        self.assertIsNone(parse_upgrade_line("no arrow here"))


if __name__ == "__main__":
    unittest.main()
