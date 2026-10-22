"""Target-guard tests for the real-browser checker."""
import argparse
import unittest
from pathlib import Path

from tools.check_web_ui import isolated_replay_distro


class WebUICheckerTargetTests(unittest.TestCase):
    def test_only_named_replay_aliases_are_accepted(self):
        self.assertEqual(isolated_replay_distro("ternuxx-replay-p4"), "ternuxx-replay-p4")

    def test_checker_requires_visible_previewed_shortcut_sync_control(self):
        source = (Path(__file__).resolve().parents[1] / "tools" / "check_web_ui.py").read_text()
        self.assertIn("Preview all Debian app shortcuts", source)
        self.assertIn("proot_shortcut_sync_control", source)
        self.assertIn("proot-shortcut-sync-control", source)

    def test_default_and_non_replay_guests_are_refused(self):
        for value in ("debian", "ubuntu", "ternuxx-replay", "../ternuxx-replay-p4", ""):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                isolated_replay_distro(value)
