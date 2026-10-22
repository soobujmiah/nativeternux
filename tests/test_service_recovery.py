"""Fixture coverage for explicit recovery of SSH service journal records."""
from __future__ import annotations

from pathlib import Path
import subprocess
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import operation_journal  # noqa: E402
import operation_recovery  # noqa: E402
import service_recovery  # noqa: E402


class FakeRunit:
    def __init__(self, state: str):
        self.state = state
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        if args[1] == "status":
            tag = "run" if self.state == "running" else "down"
            return subprocess.CompletedProcess(args, 0, f"{tag}: ternuxx-sshd: fixture\n", "")
        raise AssertionError("recovery must never invoke Runit up/down")


class ServiceRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-service-recovery-")
        root = Path(self.temp.name)
        self.home = root / "home"
        self.home.mkdir()
        self.state = self.home / ".local/share/ternuxx"
        self.prefix = root / "prefix"
        (self.prefix / "var/service/ternuxx-sshd").mkdir(parents=True)
        (self.prefix / "bin").mkdir()
        manager = self.prefix / "bin/sv"
        manager.write_text("fixture sv\n", encoding="utf-8")
        manager.chmod(0o700)
        self.source = root / "run"
        self.source.write_text("#!/bin/sh\nexec sshd\n", encoding="utf-8")
        installed = self.prefix / "var/service/ternuxx-sshd/run"
        installed.write_bytes(self.source.read_bytes())
        installed.chmod(0o700)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def pending(self, kind: str = "service.stop") -> str:
        operation_id = operation_journal.begin(str(self.state), kind, "fixture service action", home_dir=self.home)
        operation_journal.update(str(self.state), operation_id, "needs_recovery", "fixture timeout", home_dir=self.home)
        return operation_id

    def test_preview_then_resolve_marks_observed_target_complete_without_service_action(self) -> None:
        operation_id = self.pending("service.stop")
        runner = FakeRunit("stopped")
        plan = operation_recovery.preview(operation_id, prefix=self.prefix, state_dir=self.state,
                                          home=self.home, source=self.source, runner=runner)
        self.assertEqual(plan["resolution"], "complete")
        schema = json.loads((ROOT / "schemas/native-ssh-service-recovery.schema.json").read_text())
        preview_schema, applied_schema = schema["oneOf"]
        self.assertEqual(set(plan), set(preview_schema["required"]))
        expected_journal = str(self.state.resolve() / "operations" / f"{operation_id}.json")
        self.assertEqual(plan["affected_paths"], [expected_journal])
        self.assertTrue(plan["requires_confirmation"])
        self.assertTrue(plan["read_only"])
        self.assertTrue(all(call[1] == "status" for call in runner.calls))
        result = operation_recovery.resolve(operation_id, prefix=self.prefix, state_dir=self.state,
                                            home=self.home, confirmed=True, plan_id=str(plan["plan_id"]),
                                            source=self.source, runner=runner)
        self.assertFalse(result["service_action_performed"])
        self.assertEqual(set(result), set(applied_schema["required"]))
        self.assertEqual(result["affected_paths"], [expected_journal])
        self.assertEqual(operation_journal.inspect_record(str(self.state), operation_id, home_dir=self.home)["status"], "complete")
        self.assertTrue(all(call[1] == "status" for call in runner.calls))

    def test_explicit_failed_resolution_when_target_state_is_absent(self) -> None:
        operation_id = self.pending("service.stop")
        runner = FakeRunit("running")
        plan = service_recovery.preview(operation_id, prefix=self.prefix, state_dir=self.state,
                                        home=self.home, source=self.source, runner=runner)
        self.assertEqual(plan["resolution"], "failed")
        service_recovery.resolve(operation_id, prefix=self.prefix, state_dir=self.state,
                                 home=self.home, confirmed=True, plan_id=str(plan["plan_id"]),
                                 source=self.source, runner=runner)
        self.assertEqual(operation_journal.inspect_record(str(self.state), operation_id, home_dir=self.home)["status"], "failed")

    def test_stale_plan_and_non_service_or_terminal_records_are_refused(self) -> None:
        operation_id = self.pending()
        runner = FakeRunit("stopped")
        plan = service_recovery.preview(operation_id, prefix=self.prefix, state_dir=self.state,
                                        home=self.home, source=self.source, runner=runner)
        runner.state = "running"
        with self.assertRaisesRegex(service_recovery.ServiceRecoveryError, "changed"):
            service_recovery.resolve(operation_id, prefix=self.prefix, state_dir=self.state,
                                     home=self.home, confirmed=True, plan_id=str(plan["plan_id"]),
                                     source=self.source, runner=runner)
        with self.assertRaisesRegex(service_recovery.ServiceRecoveryError, "unavailable or unsafe"):
            service_recovery.preview("0" * 32, prefix=self.prefix, state_dir=self.state,
                                     home=self.home, source=self.source, runner=runner)

    def test_crash_left_starting_service_action_can_be_reconciled(self) -> None:
        operation_id = operation_journal.begin(str(self.state), "service.start", "start fixed SSH unit", home_dir=self.home)
        runner = FakeRunit("running")
        plan = service_recovery.preview(operation_id, prefix=self.prefix, state_dir=self.state, home=self.home, source=self.source, runner=runner)
        self.assertEqual(plan["resolution"], "complete")
        result = service_recovery.resolve(operation_id, prefix=self.prefix, state_dir=self.state,
            home=self.home, confirmed=True, plan_id=str(plan["plan_id"]), source=self.source, runner=runner)
        self.assertFalse(result["service_action_performed"])
        self.assertEqual(operation_journal.inspect_record(str(self.state), operation_id, home_dir=self.home)["status"], "complete")

    def test_interrupted_restart_recovery_observes_running_without_restarting(self) -> None:
        operation_id = self.pending("service.restart")
        runner = FakeRunit("running")
        plan = operation_recovery.preview(operation_id, prefix=self.prefix, state_dir=self.state,
                                          home=self.home, source=self.source, runner=runner)
        self.assertEqual(plan["record_kind"], "service.restart")
        self.assertEqual(plan["expected_service_status"], "running")
        self.assertEqual(plan["resolution"], "complete")
        result = operation_recovery.resolve(operation_id, prefix=self.prefix, state_dir=self.state,
                                            home=self.home, confirmed=True, plan_id=str(plan["plan_id"]),
                                            source=self.source, runner=runner)
        self.assertFalse(result["service_action_performed"])
        self.assertTrue(all(call[1] == "status" for call in runner.calls))
        record = operation_journal.inspect_record(str(self.state), operation_id, home_dir=self.home)
        self.assertEqual(record["status"], "complete")

    def test_journal_resolution_checks_timestamp_and_result_consistency(self) -> None:
        operation_id = self.pending("service.start")
        record = operation_journal.inspect_record(str(self.state), operation_id, home_dir=self.home)
        with self.assertRaisesRegex(ValueError, "target state"):
            operation_journal.resolve_service_record(str(self.state), operation_id,
                expected_kind="service.start", expected_updated_at=str(record["updated_at"]),
                result="complete", observed_status="stopped", home_dir=self.home)
        with self.assertRaisesRegex(RuntimeError, "state changed"):
            operation_journal.resolve_service_record(str(self.state), operation_id,
                expected_kind="service.start", expected_updated_at="stale", result="failed",
                observed_status="stopped", home_dir=self.home)
        self.assertEqual(operation_journal.inspect_record(str(self.state), operation_id, home_dir=self.home)["status"], "needs_recovery")


if __name__ == "__main__":
    unittest.main()
