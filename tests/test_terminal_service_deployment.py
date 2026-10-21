from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import terminal_service_deployment  # noqa: E402


class FixtureRunner:
    def __init__(self):
        self.calls = []

    def __call__(self, args, **kwargs):
        self.calls.append(args)
        if args[1:2] == ["status"]:
            target = Path(args[2])
            run_file = target / "run"
            if run_file.is_file():
                return subprocess.CompletedProcess(
                    args, 0, f"run: {target}: (pid 123) 2s\\n", "")
            return subprocess.CompletedProcess(
                args, 1, f"down: {target}: 1s, normally up, want up\\n", "")
        return subprocess.CompletedProcess(args, 0, "", "")


class TerminalServiceDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-terminal-service-")
        self.root = Path(self.temp.name)
        self.prefix = self.root / "prefix"
        service_root = self.prefix / "var/service"
        service_root.mkdir(parents=True)
        bin_dir = self.prefix / "bin"
        bin_dir.mkdir()
        self.sv = bin_dir / "sv"
        self.sv.write_text("#!/bin/sh\\nexit 0\\n", encoding="utf-8")
        self.sv.chmod(0o700)
        self.source = self.root / "run"
        self.source.write_text("#!/bin/sh\\nexec python3 broker.py serve\\n", encoding="utf-8")
        self.source.chmod(0o700)
        self.target = service_root / terminal_service_deployment.SERVICE_ID
        self.runner = FixtureRunner()

    def tearDown(self):
        self.temp.cleanup()

    def preview(self):
        return terminal_service_deployment.preview_install(
            prefix=self.prefix, source=self.source)

    def test_preview_is_read_only_and_requires_exact_confirmation(self):
        plan = self.preview()
        self.assertTrue(plan["read_only"])
        self.assertTrue(plan["requires_confirmation"])
        self.assertEqual(plan["target_state"], "absent")
        self.assertFalse(self.target.exists())
        with self.assertRaises(terminal_service_deployment.ServiceInstallError):
            terminal_service_deployment.install(
                prefix=self.prefix, source=self.source, confirmed=False,
                plan_id=plan["plan_id"], runner=self.runner)
        self.assertFalse(self.target.exists())
        with self.assertRaisesRegex(terminal_service_deployment.ServiceInstallError, "fresh exact"):
            terminal_service_deployment.install(
                prefix=self.prefix, source=self.source, confirmed=True,
                plan_id="wrong", runner=self.runner)
        self.assertFalse(self.target.exists())

    def test_install_creates_only_fixed_service_and_verifies_running(self):
        plan = self.preview()
        result = terminal_service_deployment.install(
            prefix=self.prefix, source=self.source, confirmed=True,
            plan_id=plan["plan_id"], runner=self.runner)
        self.assertEqual(result["status"], "installed")
        self.assertTrue(result["service_started"])
        self.assertFalse(result["guest_started"])
        self.assertFalse(result["wakeup_enabled"])
        self.assertEqual((self.target / "run").read_bytes(), self.source.read_bytes())
        self.assertEqual(terminal_service_deployment.status(
            prefix=self.prefix, runner=self.runner)["status"], "running")

    def test_existing_non_supervisor_target_is_never_adopted(self):
        self.target.mkdir()
        (self.target / "user-data").write_text("preserve", encoding="utf-8")
        before = (self.target / "user-data").read_bytes()
        with self.assertRaisesRegex(terminal_service_deployment.ServiceInstallError, "not an empty Runit supervisor"):
            self.preview()
        self.assertEqual((self.target / "user-data").read_bytes(), before)
        self.assertFalse((self.target / "run").exists())


if __name__ == "__main__":
    unittest.main()\n