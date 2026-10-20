from __future__ import annotations

import datetime as dt
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import cron_execution
import cron_registry
import cron_scheduler


NOW = dt.datetime(2026, 1, 1, 0, 15, tzinfo=dt.timezone.utc)


class CronSchedulerLeaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-scheduler-")
        self.state = Path(self.temp.name) / "state"
        self.state.mkdir(mode=0o700)
        self.job = cron_registry.new_job(
            name="fixture", action_id="diagnostics.doctor", schedule_type="cron",
            schedule={"expression": "*/15 * * * *", "timezone": "UTC"},
            enabled=True, output_policy="bounded_redacted", now=NOW - dt.timedelta(days=1))
        cron_registry.create_job(self.state, self.job)

    def tearDown(self):
        self.temp.cleanup()

    def test_lease_is_singleton_and_status_uses_process_identity(self):
        first = cron_scheduler.SchedulerLease(self.state)
        first.acquire()
        self.assertEqual(cron_scheduler.status(self.state)["status"], "running")
        second = cron_scheduler.SchedulerLease(self.state)
        with self.assertRaisesRegex(cron_scheduler.SchedulerError, "another scheduler"):
            second.acquire()
        first.heartbeat()
        first.close()
        self.assertFalse((self.state / "cron" / "scheduler.json").exists())

    def test_claimed_event_is_dispatched_once_through_controlled_executor(self):
        event_id = cron_scheduler.stable_schedule_event_id(
            self.job["job_id"], "2026-01-01T00:15:00+00:00")
        self.assertEqual(event_id, cron_scheduler.stable_schedule_event_id(
            self.job["job_id"], "2026-01-01T00:15:00Z"))
        with cron_scheduler.SchedulerLease(self.state) as lease:
            calls = []
            executor = lambda action, timeout: (
                calls.append((action, timeout)) or
                {"exit_code": 0, "stdout": "fixture", "stderr": "", "duration_ms": 2})
            first = cron_scheduler.dispatch_claimed_event(
                self.state, lease, job_id=self.job["job_id"], event_id=event_id,
                scheduled_at="2026-01-01T00:15:00Z", now=NOW, executor=executor)
            duplicate = cron_scheduler.dispatch_claimed_event(
                self.state, lease, job_id=self.job["job_id"], event_id=event_id,
                scheduled_at="2026-01-01T00:15:00Z", now=NOW, executor=executor)
        self.assertEqual(first["record"]["status"], "succeeded")
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(cron_execution.list_executions(self.state)[0]["scheduler_instance_id"],
                         first["record"]["scheduler_instance_id"])

    def test_dispatch_requires_lease_and_corrupt_scheduler_state_fails_closed(self):
        lease = cron_scheduler.SchedulerLease(self.state)
        with self.assertRaisesRegex(cron_scheduler.SchedulerError, "held"):
            cron_scheduler.dispatch_claimed_event(
                self.state, lease, job_id=self.job["job_id"], event_id="evt",
                scheduled_at="2026-01-01T00:15:00Z", now=NOW,
                executor=lambda *_: {"exit_code": 0, "stdout": "", "stderr": ""})
        with cron_scheduler.SchedulerLease(self.state):
            state_file = self.state / "cron" / "scheduler.json"
            state_file.write_text("{", encoding="utf-8")
            with self.assertRaisesRegex(cron_scheduler.SchedulerError, "malformed"):
                cron_scheduler.status(self.state)

    def test_registered_no_side_effect_action_uses_real_subprocess_runner(self):
        cron_registry.update_job(self.state, self.job["job_id"], {"action_id": "scheduler.self_test"})
        with cron_scheduler.SchedulerLease(self.state) as lease:
            result = cron_scheduler.dispatch_claimed_event(
                self.state, lease, job_id=self.job["job_id"], event_id="real-subprocess-check",
                scheduled_at="2026-01-01T00:15:00Z", now=NOW)
        self.assertEqual(result["record"]["status"], "succeeded")
        self.assertIn("scheduler.self_test", result["record"]["output_summary"])
        self.assertIn('"side_effects": false', result["record"]["output_summary"])

    def test_disabled_job_is_recorded_skipped_without_executor_call(self):
        cron_registry.update_job(self.state, self.job["job_id"], {"enabled": False})
        with cron_scheduler.SchedulerLease(self.state) as lease:
            result = cron_scheduler.dispatch_claimed_event(
                self.state, lease, job_id=self.job["job_id"], event_id="disabled-event",
                scheduled_at="2026-01-01T00:15:00Z", now=NOW,
                executor=lambda *_: self.fail("disabled action executed"))
        self.assertEqual(result["record"]["status"], "skipped")

    def test_missing_scheduler_directory_is_reported_not_installed_without_creation(self):
        state = Path(self.temp.name) / "empty-state"
        state.mkdir(mode=0o700)
        self.assertEqual(cron_scheduler.status(state)["status"], "stopped")
        self.assertFalse((state / "cron").exists())
        self.assertFalse((state / "cron").exists())

    def test_scheduler_state_is_private_and_symlink_is_rejected(self):
        with cron_scheduler.SchedulerLease(self.state):
            path = self.state / "cron" / "scheduler.json"
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        path = self.state / "cron" / "scheduler.json"
        path.symlink_to(self.state / "missing")
        with self.assertRaisesRegex(cron_scheduler.SchedulerError, "identity"):
            cron_scheduler.status(self.state)


if __name__ == "__main__":
    unittest.main()
