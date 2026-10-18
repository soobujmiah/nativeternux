"""Fixture tests for preview-first Runit definition reconciliation."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import operation_journal  # noqa: E402
import operation_recovery  # noqa: E402
import runit_deployment  # noqa: E402


class FixtureRunner:
    def __init__(self):
        self.calls: list[list[str]] = []

    def __call__(self, args, **kwargs):
        self.calls.append(args)
        if args[1:2] == ["status"]:
            return subprocess.CompletedProcess(args, 0, "run: ternuxx-sshd: (pid 123) 2s\n", "")
        if args[0] == "bash":
            return subprocess.run(args, capture_output=True, text=True)
        if "-t" in args and "bad" in Path(args[-1]).read_text():
            return subprocess.CompletedProcess(args, 1, "", "invalid fixture config")
        return subprocess.CompletedProcess(args, 0, "", "")


class RunitDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-deploy-fixture-")
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.state = self.home / ".local/share/ternuxx"
        self.prefix = self.root / "prefix"
        service = self.prefix / "var/service/ternuxx-sshd"
        service.mkdir(parents=True)
        (self.prefix / "bin").mkdir()
        self.sv = self.prefix / "bin/sv"
        self.sv.write_text("fixture sv", encoding="utf-8"); self.sv.chmod(0o700)
        sshd = self.prefix / "bin/sshd"
        sshd.write_text("fixture sshd", encoding="utf-8"); sshd.chmod(0o700)
        config = self.home / ".config/ternuxx/sshd_recovery.conf"
        config.parent.mkdir(parents=True)
        config.write_text("Port 8023\n", encoding="utf-8"); config.chmod(0o600)
        self.source = self.root / "source-run"
        self.source.write_text("#!/bin/sh\nexec sshd -f config\n", encoding="utf-8")
        self.source.chmod(0o700)
        self.target = service / "run"
        self.target.write_text("#!/bin/sh\nexec sshd -f old-config\n", encoding="utf-8")
        self.target.chmod(0o700)
        self.runner = FixtureRunner()

    def tearDown(self):
        self.temp.cleanup()

    def preview(self):
        return runit_deployment.preview(prefix=self.prefix, home=self.home, state_dir=self.state,
                                        source=self.source, runner=self.runner)

    def apply(self, plan, writer=runit_deployment._atomic_write):
        return runit_deployment.apply(prefix=self.prefix, home=self.home, state_dir=self.state,
                                      source=self.source, runner=self.runner, confirmed=True,
                                      plan_id=plan["plan_id"], writer=writer)

    def test_preview_is_read_only_and_contains_explicit_diff(self):
        before = self.target.read_bytes()
        plan = self.preview()
        self.assertTrue(plan["read_only"])
        self.assertTrue(plan["requires_confirmation"])
        self.assertTrue(plan["diff"])
        self.assertEqual(self.target.read_bytes(), before)
        self.assertFalse(any(call[1:2] in (["up"], ["down"], ["restart"]) for call in self.runner.calls))

    def test_apply_requires_exact_plan_and_never_restarts_service(self):
        plan = self.preview()
        with self.assertRaises(runit_deployment.DeploymentError):
            runit_deployment.apply(prefix=self.prefix, home=self.home, state_dir=self.state,
                                   source=self.source, runner=self.runner, confirmed=True,
                                   plan_id="wrong")
        result = self.apply(plan)
        self.assertEqual(self.target.read_bytes(), self.source.read_bytes())
        self.assertEqual(result["service_status"], "running")
        self.assertFalse(result["service_restarted"])
        self.assertFalse(any(call[1:2] in (["up"], ["down"], ["restart"]) for call in self.runner.calls))
        rollback = runit_deployment.preview_rollback(result["operation_id"], prefix=self.prefix,
                    home=self.home, state_dir=self.state, runner=self.runner)
        restored = runit_deployment.apply_rollback(result["operation_id"], prefix=self.prefix,
                    home=self.home, state_dir=self.state, confirmed=True, plan_id=rollback["plan_id"],
                    runner=self.runner)
        self.assertEqual(restored["status"], "rolled_back")
        self.assertEqual(self.target.read_text(), "#!/bin/sh\nexec sshd -f old-config\n")

    def test_partial_apply_failure_restores_original(self):
        plan = self.preview(); calls = 0
        def failing_writer(path, data, mode):
            nonlocal calls
            calls += 1
            if calls == 1:
                path.write_bytes(data[:8])
                raise OSError("fixture partial write")
            runit_deployment._atomic_write(path, data, mode)
        with self.assertRaisesRegex(runit_deployment.DeploymentError, "restored the prior definition"):
            self.apply(plan, writer=failing_writer)
        self.assertEqual(self.target.read_text(), "#!/bin/sh\nexec sshd -f old-config\n")
        records = operation_journal.list_records(str(self.state), home_dir=self.home)
        self.assertEqual(records[0]["status"], "failed")

    def test_failed_automatic_rollback_keeps_snapshot_for_recovery(self):
        plan = self.preview(); calls = 0
        def failing_writer(path, data, mode):
            nonlocal calls
            calls += 1
            if calls == 1:
                path.write_bytes(data[:8]); raise OSError("partial deployment")
            raise OSError("rollback write failure")
        with self.assertRaisesRegex(runit_deployment.DeploymentError, "needs recovery") as ctx:
            self.apply(plan, writer=failing_writer)
        operation_id = str(ctx.exception).split("operation=")[-1]
        record = operation_journal.inspect_record(str(self.state), operation_id, home_dir=self.home)
        self.assertEqual(record["status"], "needs_recovery")
        current = operation_recovery.preview(operation_id, prefix=self.prefix,
                    home=self.home, state_dir=self.state, runner=self.runner)
        operation_recovery.resolve(operation_id, prefix=self.prefix, home=self.home,
                    state_dir=self.state, confirmed=True, plan_id=current["plan_id"], runner=self.runner)
        self.assertEqual(self.target.read_text(), "#!/bin/sh\nexec sshd -f old-config\n")

    def test_partial_explicit_rollback_failure_can_be_recovered(self):
        deployment = self.apply(self.preview())
        rollback_plan = runit_deployment.preview_rollback(deployment["operation_id"],
                    prefix=self.prefix, home=self.home, state_dir=self.state, runner=self.runner)
        def fail_once(path, data, mode):
            path.write_bytes(data[:8])
            raise OSError("fixture partial rollback")
        with self.assertRaises(runit_deployment.DeploymentError):
            runit_deployment.apply_rollback(deployment["operation_id"], prefix=self.prefix,
                    home=self.home, state_dir=self.state, confirmed=True,
                    plan_id=rollback_plan["plan_id"], runner=self.runner, writer=fail_once)
        pending = [r for r in operation_journal.list_records(str(self.state), home_dir=self.home)
                   if r["kind"] == "service.deploy.rollback" and r["status"] == "needs_recovery"]
        self.assertEqual(len(pending), 1)
        recovery_id = pending[0]["operation_id"]
        plan = operation_recovery.preview(recovery_id, prefix=self.prefix, home=self.home,
                    state_dir=self.state, runner=self.runner)
        operation_recovery.resolve(recovery_id, prefix=self.prefix, home=self.home,
                    state_dir=self.state, confirmed=True, plan_id=plan["plan_id"], runner=self.runner)
        self.assertEqual(self.target.read_text(), "#!/bin/sh\nexec sshd -f old-config\n")
        self.assertEqual(operation_journal.inspect_record(str(self.state), recovery_id,
                    home_dir=self.home)["status"], "complete")

    def test_symlinked_recovery_snapshot_is_refused(self):
        result = self.apply(self.preview())
        backup_dir = self.state / "service-deployments"
        snapshot = backup_dir / f"{result['operation_id']}.json"
        snapshot.unlink()
        outside = self.root / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        snapshot.symlink_to(outside)
        with self.assertRaises(runit_deployment.DeploymentError):
            runit_deployment.preview_rollback(result["operation_id"], prefix=self.prefix,
                    home=self.home, state_dir=self.state, runner=self.runner)

    def test_invalid_config_or_source_fails_closed(self):
        (self.home / ".config/ternuxx/sshd_recovery.conf").write_text("bad\n")
        with self.assertRaises(runit_deployment.DeploymentError): self.preview()
        (self.home / ".config/ternuxx/sshd_recovery.conf").write_text("Port 8023\n")
        self.source.write_text("#!/bin/sh\n}\n")
        with self.assertRaises(runit_deployment.DeploymentError): self.preview()


if __name__ == "__main__":
    unittest.main()
