"""Fixtures for the preview-first Native Termux CLI entrypoint installer."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cli_entrypoint as installer


class CliEntrypointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-cli-entrypoint-")
        self.root = Path(self.temp.name)
        self.prefix = self.root / "prefix"
        self.home = self.root / "home"
        (self.prefix / "bin").mkdir(parents=True)
        self.home.mkdir()
        self.target = self.prefix / "bin/tx"
        (self.prefix / "bin/bash").symlink_to(shutil.which("bash"))
        self.old = b"#!/bin/sh\necho old-cli\n"
        self.target.write_bytes(self.old)
        self.target.chmod(0o755)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_preview_is_read_only_and_exact_apply_then_rollback(self) -> None:
        plan = installer.preview(prefix=self.prefix)
        self.assertTrue(plan["read_only"])
        self.assertTrue(plan["requires_confirmation"])
        self.assertEqual(self.target.read_bytes(), self.old)
        self.assertFalse((self.home / ".local/share/ternuxx/cli-entrypoint-recovery").exists())
        with self.assertRaises(installer.InstallError):
            installer.apply(prefix=self.prefix, home=self.home, confirmed=True, plan_id="wrong")
        deployed = installer.apply(prefix=self.prefix, home=self.home, confirmed=True, plan_id=plan["plan_id"])
        self.assertEqual(deployed["status"], "installed")
        self.assertEqual(self.target.read_bytes(), installer.SOURCE.read_bytes())
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o755)
        rollback_plan = installer.rollback_preview(operation_id=deployed["operation_id"],
                                                   prefix=self.prefix, home=self.home)
        with self.assertRaises(installer.InstallError):
            installer.rollback(operation_id=deployed["operation_id"], prefix=self.prefix,
                                home=self.home, confirmed=True, plan_id="wrong")
        rolled = installer.rollback(operation_id=deployed["operation_id"], prefix=self.prefix,
                                    home=self.home, confirmed=True, plan_id=rollback_plan["plan_id"])
        self.assertEqual(rolled["status"], "rolled_back")
        self.assertEqual(self.target.read_bytes(), self.old)
        self.assertTrue(rolled["snapshot_retained"])

    def test_first_install_can_be_rolled_back_to_absent_target(self) -> None:
        self.target.unlink()
        plan = installer.preview(prefix=self.prefix)
        deployed = installer.apply(prefix=self.prefix, home=self.home,
                                   confirmed=True, plan_id=plan["plan_id"])
        rollback_plan = installer.rollback_preview(operation_id=deployed["operation_id"],
                                                   prefix=self.prefix, home=self.home)
        installer.rollback(operation_id=deployed["operation_id"], prefix=self.prefix,
                           home=self.home, confirmed=True, plan_id=rollback_plan["plan_id"])
        self.assertFalse(self.target.exists())

    def test_partial_write_failure_restores_original_entrypoint(self) -> None:
        plan = installer.preview(prefix=self.prefix)
        real_write = installer._atomic_write
        injected = False

        def failing_write(path: Path, data: bytes, mode: int) -> None:
            nonlocal injected
            if path == self.target and data == installer.SOURCE.read_bytes() and not injected:
                injected = True
                path.write_bytes(b"partial")
                raise OSError("fixture partial write")
            real_write(path, data, mode)

        with mock.patch.object(installer, "_atomic_write", side_effect=failing_write):
            with self.assertRaisesRegex(installer.InstallError, "previous entrypoint restored"):
                installer.apply(prefix=self.prefix, home=self.home,
                                confirmed=True, plan_id=plan["plan_id"])
        self.assertEqual(self.target.read_bytes(), self.old)
        snapshots = list((self.home / ".local/share/ternuxx/cli-entrypoint-recovery").glob("*.json"))
        self.assertEqual(len(snapshots), 1)

    def test_symlink_target_is_refused_without_touching_referent(self) -> None:
        self.target.unlink()
        outside = self.root / "outside"
        outside.write_bytes(self.old)
        self.target.symlink_to(outside)
        with self.assertRaisesRegex(installer.InstallError, "regular file"):
            installer.preview(prefix=self.prefix)
        self.assertEqual(outside.read_bytes(), self.old)

    def test_stale_plan_is_refused(self) -> None:
        plan = installer.preview(prefix=self.prefix)
        self.target.write_bytes(b"changed after preview")
        with self.assertRaises(installer.InstallError):
            installer.apply(prefix=self.prefix, home=self.home,
                            confirmed=True, plan_id=plan["plan_id"])
        self.assertEqual(self.target.read_bytes(), b"changed after preview")

    def test_source_checkout_entrypoint_runs_directly_in_native_termux(self) -> None:
        checkout = Path(__file__).resolve().parents[1]
        result = subprocess.run([str(checkout / "tx"), "--version"], cwd=checkout,
                                capture_output=True, text=True, check=False, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Ternuxx v", result.stdout)

    def test_installed_shim_uses_android_native_shell_interpreter(self) -> None:
        self.assertTrue(installer.SOURCE.read_text(encoding="utf-8").startswith("#!/system/bin/sh\n"))

    def test_installed_shim_forwards_arguments_to_selected_checkout(self) -> None:
        checkout = self.root / "checkout"
        checkout.mkdir()
        command = checkout / "tx"
        command.write_text("#!/bin/sh\nprintf '<%s>\\n' \"$@\"\n", encoding="utf-8")
        command.chmod(0o755)
        result = subprocess.run(["bash", str(installer.SOURCE), "status", "--json"],
                                env={**os.environ, "TERNUXX_CHECKOUT": str(checkout), "PREFIX": str(self.prefix)},
                                capture_output=True, text=True, check=False, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "<status>\n<--json>\n")


if __name__ == "__main__":
    unittest.main()
