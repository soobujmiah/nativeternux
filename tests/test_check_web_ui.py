"""Target-guard tests for the real-browser checker."""
import argparse
import unittest

from tools.check_web_ui import isolated_replay_distro


class WebUICheckerTargetTests(unittest.TestCase):
    def test_only_named_replay_aliases_are_accepted(self):
        self.assertEqual(isolated_replay_distro("ternuxx-replay-p4"), "ternuxx-replay-p4")

    def test_default_and_non_replay_guests_are_refused(self):
        for value in ("debian", "ubuntu", "ternuxx-replay", "../ternuxx-replay-p4", ""):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                isolated_replay_distro(value)
