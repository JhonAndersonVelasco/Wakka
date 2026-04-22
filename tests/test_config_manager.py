"""Tests for configuration merge and pacman repo section helpers."""
from __future__ import annotations

import unittest

from core.config_manager import OFFICIAL_PACMAN_SECTIONS, _deep_merge


class TestDeepMerge(unittest.TestCase):
    def test_nested_merge_preserves_defaults(self):
        base = {"a": 1, "cache": {"enabled": True, "keep": 1}}
        override = {"cache": {"keep": 3}}
        out = _deep_merge(base, override)
        self.assertEqual(out["a"], 1)
        self.assertEqual(out["cache"]["enabled"], True)
        self.assertEqual(out["cache"]["keep"], 3)

    def test_override_replaces_leaf(self):
        base = {"theme": "system"}
        out = _deep_merge(base, {"theme": "dark"})
        self.assertEqual(out["theme"], "dark")


class TestOfficialSections(unittest.TestCase):
    def test_expected_core_set(self):
        self.assertIn("[core]", OFFICIAL_PACMAN_SECTIONS)
        self.assertIn("[community-testing]", OFFICIAL_PACMAN_SECTIONS)
        self.assertIn("[kde-unstable]", OFFICIAL_PACMAN_SECTIONS)


if __name__ == "__main__":
    unittest.main()
