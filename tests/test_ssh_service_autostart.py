from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import ssh_service_autostart as policy


class SshServiceAutostartTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home = self.root / "home"; self.home.mkdir()
        self.state = self.root / "state"; self.state.mkdir(mode=0o700)
        self.prefix = self.root / "prefix"; self.service_parent = self.prefix / "var/service"
        self.service = self.service_parent / "ternuxx-sshd"; self.service.mkdir(parents=True, mode=0o700)
        run = self.service / "run"; run.write_bytes(policy.ssh_diagnostics.service_definition_source().read_bytes()); run.chmod(0o700)
        self.prefix_value = "/data/data/com.termux/files/usr"
        self.uid = os.getuid()
        self.patcher = __import__("unittest.mock", fromlist=["patch"]).patch.object(policy, "_PREFIX", str(self.prefix))
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop(); self.temp.cleanup()

    def call_preview(self, enabled):
        return policy.preview(enabled=enabled, home=self.home, state_dir=self.state,
                              prefix=str(self.prefix), uid=self.uid)

    def call_apply(self, plan, enabled):
        return policy.apply(enabled=enabled, confirmed=True, plan_id=plan["plan_id"],
                            home=self.home, state_dir=self.state, prefix=str(self.prefix), uid=self.uid)

    def test_absent_down_marker_means_autostart_enabled(self):
        result = policy.status(home=self.home, state_dir=self.state, prefix=str(self.prefix), uid=self.uid)
        self.assertTrue(result["enabled"]); self.assertEqual(result["status"], "enabled")

    def test_disable_is_previewed_then_creates_only_exact_down_marker(self):
        plan = self.call_preview(False); self.assertTrue(plan["changed"]); self.assertEqual(plan["target"], str(self.service / "down"))
        result = self.call_apply(plan, False)
        marker = self.service / "down"
        self.assertTrue(marker.is_file()); self.assertEqual(marker.stat().st_size, 0); self.assertEqual(marker.stat().st_mode & 0o777, 0o600)
        self.assertFalse(result["enabled"]); self.assertIn("existing SSH process state was not signalled", result["runtime_effect"])

    def test_enable_removes_only_verified_empty_down_marker(self):
        marker = self.service / "down"; marker.touch(mode=0o600)
        plan = self.call_preview(True); result = self.call_apply(plan, True)
        self.assertFalse(marker.exists()); self.assertTrue(result["enabled"])

    def test_stale_preview_and_unconfirmed_apply_do_not_change_marker(self):
        plan = self.call_preview(False)
        result = policy.apply(enabled=False, confirmed=True, plan_id="bad", home=self.home,
                              state_dir=self.state, prefix=str(self.prefix), uid=self.uid)
        self.assertEqual(result["status"], "stale_plan"); self.assertFalse((self.service / "down").exists())
        result = policy.apply(enabled=False, confirmed=False, plan_id=plan["plan_id"], home=self.home,
                              state_dir=self.state, prefix=str(self.prefix), uid=self.uid)
        self.assertEqual(result["status"], "confirmation_required"); self.assertFalse((self.service / "down").exists())

    def test_symlinked_service_or_marker_and_nonempty_marker_are_refused(self):
        real = self.root / "real-service"; self.service.rename(real); self.service.symlink_to(real)
        with self.assertRaises(policy.AutostartPolicyError): self.call_preview(False)
        self.service.unlink(); real.rename(self.service)
        marker = self.service / "down"; target = self.root / "target"; target.write_text("keep")
        marker.symlink_to(target)
        with self.assertRaises(policy.AutostartPolicyError): self.call_preview(True)
        marker.unlink(); marker.write_text("user data")
        with self.assertRaises(policy.AutostartPolicyError): self.call_preview(True)
        self.assertEqual(target.read_text(), "keep")

    def test_installed_service_source_mismatch_is_refused(self):
        run = self.service / "run"
        run.write_text("#!/bin/sh\nexit 99\n")
        run.chmod(0o700)
        with self.assertRaises(policy.AutostartPolicyError):
            self.call_preview(False)
        self.assertFalse((self.service / "down").exists())

    def test_unrelated_prefix_is_refused(self):
        with self.assertRaises(policy.AutostartPolicyError):
            policy.status(home=self.home, state_dir=self.state, prefix="/usr", uid=self.uid)


if __name__ == "__main__": unittest.main()
