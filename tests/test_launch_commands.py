"""Fixtures for short launch commands and canonical PRoot routing."""
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
        self.bin = self.root / "bin"
        self.bin.mkdir()
        stub = self.bin / "proot-distro"
        stub.write_text('#!/bin/sh\nif [ -n \"${PROOT_ENV_CAPTURE:-}\" ]; then env > \"$PROOT_ENV_CAPTURE\"; fi\nprintf \"%s\\n\" \"$@\"\n')
        stub.chmod(0o755)
        self.env = {**os.environ, "HOME": str(self.root), "PREFIX": str(self.root),
                    "PATH": f"{self.bin}:{os.environ['PATH']}",
                    "TERNUXX_STATE_DIR": str(self.root / "state"),
                    "TERNUXX_LOG_DIR": str(self.root / "log")}

    def tearDown(self) -> None:
        self.temp.cleanup()

    def tx(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([shutil.which("bash"), str(ROOT / "tx"), *args],
                              capture_output=True, text=True, env=self.env, timeout=30)

    def cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([shutil.which("bash"), str(ROOT / "tx"), *args],
                              capture_output=True, text=True, env=self.env, timeout=30)

    def test_shell_explicit_user_runs_proot_distro_login(self) -> None:
        result = self.tx("db", "--user", "dev")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.split(), ["login", "debian", "--shared-tmp", "--user", "dev"])

    def test_native_android_runtime_variables_do_not_leak_to_guest_profile(self) -> None:
        capture = self.root / "proot-env"
        env = {**self.env, "PROOT_ENV_CAPTURE": str(capture),
               "ANDROID_ART_ROOT": "/apex/com.android.art", "ANDROID_DATA": "/data",
               "ANDROID_ROOT": "/system", "BOOTCLASSPATH": "sentinel-classpath",
               "EXTERNAL_STORAGE": "/sdcard", "TERM": "xterm-256color"}
        result = subprocess.run([shutil.which("bash"), str(ROOT / "tx"), "db", "--user", "dev"],
                                capture_output=True, text=True, env=env, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        observed = capture.read_text()
        observed_keys = {line.split("=", 1)[0] for line in observed.splitlines() if "=" in line}
        for name in ("ANDROID_ART_ROOT", "ANDROID_DATA", "ANDROID_ROOT", "BOOTCLASSPATH", "EXTERNAL_STORAGE"):
            self.assertNotIn(name, observed_keys)
        self.assertIn("TERM", observed_keys)

    def test_legacy_tx_shell_command_is_removed(self) -> None:
        result = self.tx("shell")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unknown command", result.stderr)

    def test_shell_root_and_command_passthrough(self) -> None:
        result = self.tx("db", "--root", "--", "echo", "a b")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(),
                         ["login", "debian", "--shared-tmp", "--", "echo", "a b"])

    def test_shell_refuses_unresolvable_user_and_bad_names(self) -> None:
        self.assertNotEqual(self.tx("db").returncode, 0)
        self.assertEqual(self.tx("db", "--user", "a;b").returncode, 2)
        self.assertEqual(self.tx("db", "--root", "--distro", "../x").returncode, 2)

    def test_gui_and_canonical_proot_gui_reject_unknown_actions(self) -> None:
        self.assertEqual(self.tx("gui", "bogus").returncode, 2)
        self.assertEqual(self.cli("proot", "gui", "bogus").returncode, 2)

    def test_gui_reports_missing_display_without_starting_desktop(self) -> None:
        env = dict(self.env)
        env["PREFIX"] = "/data/data/com.termux/files/usr"
        env["TERMUX_VERSION"] = "fixture"
        env.pop("DISPLAY", None)
        result = subprocess.run([shutil.which("bash"), str(ROOT / "tx"), "gui"],
                                capture_output=True, text=True, env=env, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn("The Ternuxx Native desktop is not verified running", result.stderr)
        self.assertIn("Run 'tx start', then retry 'tx gui'", result.stderr)

    def test_non_contract_app_and_pgui_shortcuts_are_not_registered(self) -> None:
        for command in ("app", "apps", "pgui"):
            result = self.tx(command)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Unknown command", result.stderr)

    def test_help_lists_short_form_and_commands(self) -> None:
        result = self.tx("--help")
        self.assertIn("tx <command> [options]", result.stdout)
        for name in ("tx db", "tx gui"):
            self.assertIn(name, result.stdout)
        self.assertNotIn("tx pgui", result.stdout)
        self.assertIn("tx proot gui", self.cli("proot", "--help").stdout)
        self.assertIn("--root", self.tx("db", "--help").stdout)

    def test_mng_is_canonical_and_long_management_route_is_deprecated_alias(self) -> None:
        canonical = self.cli("mng", "bogus")
        self.assertNotEqual(canonical.returncode, 0)
        self.assertNotIn("deprecated", canonical.stderr)
        legacy = self.cli("management", "bogus")
        self.assertNotEqual(legacy.returncode, 0)
        self.assertIn("tx management is deprecated; use tx mng", legacy.stderr)
        help_text = self.cli("mng", "--help")
        self.assertIn("tx mng cron status", help_text.stdout)
        self.assertIn("tx mng proot status", help_text.stdout)
        self.assertNotIn("tx management", help_text.stdout)
        bad_proot = self.cli("mng", "proot", "stop")
        self.assertEqual(bad_proot.returncode, 2)
        self.assertIn("Usage: tx mng proot stop SESSION_ID", bad_proot.stderr)
        proot_bad_action = self.cli("mng", "proot", "stop")
        self.assertEqual(proot_bad_action.returncode, 2)
        self.assertIn("Usage: tx mng proot stop SESSION_ID", proot_bad_action.stderr)

    def test_short_slugs_dispatch_to_the_same_canonical_commands(self) -> None:
        self.assertEqual(self.cli("st", "--json").returncode, 0)
        self.assertIn("Start the native Termux XFCE session", self.cli("up", "--help").stdout)
        self.assertIn("tx mng app launch", self.cli("--help").stdout)
        self.assertNotEqual(self.cli("zz").returncode, 0)


if __name__ == "__main__":
    unittest.main()
