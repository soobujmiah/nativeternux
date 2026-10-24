"""Native launch command and retired-route contract tests."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LaunchCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-launch-")
        self.root = Path(self.temp.name)
        self.prefix = self.root / "prefix"
        self.prefix.mkdir()
        self.env = {
            **os.environ,
            "HOME": str(self.root),
            "PREFIX": str(self.prefix),
            "PATH": os.environ["PATH"],
            "TERNUXX_STATE_DIR": str(self.root / "state"),
            "TERNUXX_LOG_DIR": str(self.root / "log"),
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [shutil.which("bash"), str(ROOT / "tx"), *args],
            capture_output=True, text=True, env=self.env, timeout=15,
        )

    def test_removed_guest_routes_fail_closed_without_starting_processes(self):
        for command in ("proot", "db", "pgui", "virgl", "terminal"):
            with self.subTest(command=command):
                result = self.cli(command)
                self.assertEqual(result.returncode, 2)
                self.assertIn("retired", result.stdout + result.stderr)

    def test_native_app_command_is_live_not_a_retired_guest_alias(self):
        result = self.cli("app")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Native Termux", result.stderr)
        self.assertNotIn("retired", result.stdout + result.stderr)

    def test_help_lists_only_native_supported_commands(self):
        result = self.cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("tx gui", result.stdout)
        self.assertIn("tx guides", result.stdout)
        self.assertNotRegex(result.stdout.lower(), r"proot|debian|hybrid")

    def test_native_management_alias_and_guided_menu(self):
        result = self.cli("mng", "--help")
        self.assertIn("tx mng cron", result.stdout)
        guide = self.cli("guides")
        self.assertIn("Ternuxx Native Termux guide", guide.stdout)
        self.assertIn("Preview Native package setup", guide.stdout)
        self.assertIn("Open terminal management (TUI)", guide.stdout)
        self.assertIn("Open authenticated Web management", guide.stdout)
        self.assertIn("Open GTK management center", guide.stdout)
        self.assertIn("`tx tui`, `tx web`, or `tx gui`", guide.stdout)

    def test_unknown_install_guest_target_is_rejected_before_package_checks(self):
        result = self.cli("install", "debian", "preview")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Unknown install option", result.stderr)


if __name__ == "__main__":
    unittest.main()
