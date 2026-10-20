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
import management_authorization
import management_service
import management_sessions


NOW = dt.datetime(2026, 1, 1, 0, 15, tzinfo=dt.timezone.utc)


class CronExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-execution-")
        self.state = Path(self.temp.name) / "state"
        self.state.mkdir(mode=0o700)
        self.job = cron_registry.new_job(
            name="fixture", action_id="diagnostics.doctor", schedule_type="cron",
            schedule={"expression": "*/15 * * * *", "timezone": "UTC"},
            enabled=True, output_policy="bounded_redacted", now=NOW - dt.timedelta(days=1))
        cron_registry.create_job(self.state, self.job)

    def tearDown(self):
        self.temp.cleanup()

    def claim(self, event="tick-20260101T0015Z", job_id=None, trigger="schedule"):
        return cron_execution.claim_event(
            self.state, job_id=job_id or self.job["job_id"], event_id=event,
            scheduled_at="2026-01-01T00:15:00Z", scheduler_instance_id="sched-fixture",
            trigger_source=trigger, now=NOW)

    def test_claim_is_atomic_idempotent_and_persisted(self):
        first = self.claim()
        duplicate = self.claim()
        self.assertTrue(first["claimed"])
        self.assertFalse(duplicate["claimed"])
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(first["record"]["execution_id"], duplicate["record"]["execution_id"])
        self.assertEqual(cron_execution.list_executions(self.state)[0]["status"], "claimed")
        self.assertEqual((self.state / "cron" / "executions.json").stat().st_mode & 0o777, 0o600)

    def test_disabled_job_is_durably_skipped(self):
        cron_registry.update_job(self.state, self.job["job_id"], {"enabled": False})
        result = self.claim("disabled-event")
        self.assertFalse(result["claimed"])
        self.assertEqual(result["record"]["status"], "skipped")

    def test_future_due_time_and_unregistered_identity_rejected(self):
        with self.assertRaises(cron_execution.ExecutionError):
            cron_execution.claim_event(self.state, job_id=self.job["job_id"], event_id="future",
                scheduled_at="2026-01-01T00:16:00Z", scheduler_instance_id="sched",
                now=NOW)
        with self.assertRaises(cron_execution.ExecutionError):
            cron_execution.claim_event(self.state, job_id=self.job["job_id"], event_id="future",
                scheduled_at="bad", scheduler_instance_id="sched", now=NOW)

    def test_active_overlap_skips_and_queue_one_is_explicitly_unsupported(self):
        first = self.claim()
        second = self.claim("tick-2")
        self.assertEqual(second["record"]["status"], "skipped")
        with self.assertRaisesRegex(cron_registry.CronError, "concurrency policy 'skip_overlap'"):
            cron_registry.update_job(self.state, self.job["job_id"], {"concurrency_policy": "queue_one"})

    def test_executor_result_persists_bounded_redacted_success(self):
        claimed = self.claim()
        observed = []
        def executor(action, timeout):
            observed.append((action, timeout))
            return {"exit_code": 0, "stdout": "ok token=secret-value", "stderr": ""}
        result = cron_execution.execute_claimed(self.state, claimed["record"]["execution_id"],
            executor=executor, now=NOW)
        self.assertEqual(observed, [(self.job["action_id"], self.job["timeout_seconds"])])
        self.assertEqual(result["status"], "succeeded")
        self.assertIn("token=[REDACTED]", result["output_summary"])
        self.assertNotIn("secret-value", result["output_summary"])
        self.assertEqual(cron_execution.show_execution(self.state, result["execution_id"]), result)

    def test_executor_failure_and_timeout_are_distinct(self):
        failed_claim = self.claim("failed-event")
        failed = cron_execution.execute_claimed(self.state, failed_claim["record"]["execution_id"],
            executor=lambda action, timeout: {"exit_code": 7, "stdout": "", "stderr": "failed"})
        self.assertEqual((failed["status"], failed["failure_category"], failed["exit_code"]),
                         ("failed", "action_failed", 7))
        # A separate job is needed because skip_overlap correctly sees the first record terminal now.
        timeout_claim = self.claim("timeout-event")
        timed_out = cron_execution.execute_claimed(self.state, timeout_claim["record"]["execution_id"],
            executor=lambda action, timeout: (_ for _ in ()).throw(TimeoutError()))
        self.assertEqual((timed_out["status"], timed_out["failure_category"]), ("timed_out", "timeout"))


    def test_legacy_unsupported_retry_policy_fails_before_claim_or_launch(self):
        root = cron_registry._store_root(self.state)
        legacy = dict(self.job)
        legacy["retry_policy"] = {"max_attempts": 2, "delay_seconds": 1, "backoff": "fixed"}
        cron_registry._write(root, {"schema_version": 1, "jobs": [legacy]})
        with self.assertRaisesRegex(cron_execution.ExecutionError, "policy is unsupported"):
            self.claim("retry-event")
        self.assertFalse((self.state / "cron" / "executions.json").exists())

    def test_crash_after_claim_remains_unresolved_and_blocks_duplicate_work(self):
        first = self.claim("crash-window")
        self.assertEqual(first["record"]["status"], "claimed")
        duplicate = self.claim("crash-window")
        self.assertTrue(duplicate["duplicate"])
        other = self.claim("later-slot")
        self.assertEqual(other["record"]["status"], "skipped")
        self.assertEqual(cron_execution.status(self.state)["unresolved_count"], 1)

    def test_bounded_output_summary(self):
        claimed = self.claim()
        result = cron_execution.execute_claimed(self.state, claimed["record"]["execution_id"],
            executor=lambda action, timeout: {"exit_code": 0, "stdout": "a" * 5000, "stderr": ""})
        self.assertLessEqual(len(result["output_summary"]), cron_execution.MAX_SUMMARY)


    def test_retention_keeps_unresolved_records_and_drops_oldest_terminal(self):
        claimed = self.claim("active")
        active = claimed["record"]
        terminal_a = dict(active, execution_id="exec-" + "a" * 32, event_id="terminal-a",
                          status="succeeded", completed_at="2026-01-01T00:16:00Z",
                          started_at="2026-01-01T00:15:00Z", exit_code=0, duration_ms=1)
        terminal_b = dict(terminal_a, execution_id="exec-" + "b" * 32, event_id="terminal-b")
        import unittest.mock
        with unittest.mock.patch.object(cron_execution, "MAX_RECORDS", 2):
            root = cron_registry._store_root(self.state)
            ledger = cron_execution._ledger(root)
            ledger["records"].extend([terminal_a, terminal_b])
            cron_execution._write(root, ledger)
            kept = cron_execution._ledger(root)["records"]
        self.assertEqual(len(kept), 2)
        self.assertIn(active["execution_id"], {x["execution_id"] for x in kept})
        self.assertIn(terminal_b["execution_id"], {x["execution_id"] for x in kept})

    def test_malformed_and_dangling_symlink_ledger_fail_closed(self):
        self.claim()
        path = self.state / "cron" / "executions.json"
        path.write_text("{", encoding="utf-8")
        with self.assertRaises(cron_execution.ExecutionError):
            cron_execution.list_executions(self.state)
        path.unlink()
        path.symlink_to(path.parent / "missing-ledger")
        with self.assertRaises(cron_execution.ExecutionError):
            cron_execution.claim_event(self.state, job_id=self.job["job_id"], event_id="after-symlink",
                scheduled_at="2026-01-01T00:15:00Z", scheduler_instance_id="sched-fixture", now=NOW)

    def test_api_history_is_read_only_authorized_and_cli_status_shared(self):
        env = {"TERMUX_VERSION": "test", "PREFIX": "/data/data/com.termux/files/usr",
               "HOME": self.temp.name, "TERNUXX_STATE_DIR": str(self.state)}
        request = lambda op, args: {"api_version": 1, "request_id": "cron-history-001",
                                    "operation": op, "args": args}
        self.assertEqual(management_authorization.required_capability("cron.executions.list"), "diagnostics.read")
        self.assertIn("cron.executions.list", management_sessions.READ_ONLY_OPERATIONS)
        self.assertNotIn("cron.executions.list", management_sessions.MUTATING_OPERATIONS)
        claim = self.claim()
        status = management_service.dispatch(request("cron.status", {}), env=env)
        self.assertTrue(status["ok"])
        self.assertEqual(status["data"]["execution_ledger"]["execution_core"], "typed_action_executor_available")
        response = management_service.dispatch(request("cron.executions.list", {"limit": 10}), env=env)
        self.assertTrue(response["ok"], response)
        self.assertEqual(response["data"]["executions"][0]["execution_id"], claim["record"]["execution_id"])
        bad = management_service.dispatch(request("cron.executions.show", {"execution_id": "bad"}), env=env)
        self.assertFalse(bad["ok"])


if __name__ == "__main__":
    unittest.main()
