from __future__ import annotations
import datetime as dt
from pathlib import Path
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import cron_daemon
import cron_execution
import cron_registry


class CronDaemonRuntimeTests(unittest.TestCase):
    def test_isolated_daemon_dispatches_due_registered_action_once_and_stops_owned_process(self):
        with tempfile.TemporaryDirectory(prefix="ternuxx-cron-daemon-") as tmp:
            state = Path(tmp) / "state"
            state.mkdir(mode=0o700)
            now = dt.datetime.now(dt.timezone.utc)
            due = now + dt.timedelta(seconds=3)
            job = cron_registry.new_job(
                name="isolated daemon test", action_id="scheduler.self_test",
                schedule_type="one_time", schedule={"at": due.isoformat()},
                enabled=True, now=now)
            cron_registry.create_job(state, job)
            started = cron_daemon.start(str(state), poll_seconds=1, startup_timeout=5)
            pid = started["pid"]
            try:
                self.assertTrue(started["started"])
                self.assertEqual(started["status"]["lease_held"], True)
                deadline = time.monotonic() + 12
                records = []
                while time.monotonic() < deadline:
                    records = cron_execution.list_executions(state)
                    if records and records[0]["status"] in {"succeeded", "failed", "timed_out"}:
                        break
                    time.sleep(0.1)
                self.assertEqual(len(records), 1, records)
                self.assertEqual(records[0]["status"], "succeeded", records)
                self.assertEqual(records[0]["trigger_source"], "schedule")
                self.assertEqual(records[0]["attempt"], 1)
                # Repeated polling cannot create another ledger claim for the event.
                time.sleep(1.2)
                self.assertEqual(len(cron_execution.list_executions(state)), 1)
                stopped = cron_daemon.stop(str(state), confirmed=True, timeout=5)
                self.assertTrue(stopped["stopped"], stopped)
                self.assertEqual(cron_daemon.status(str(state))["status"], "stopped")
            finally:
                if cron_scheduler_process_alive(state):
                    try:
                        cron_daemon.stop(str(state), confirmed=True, timeout=2)
                    except Exception:
                        pass


def cron_scheduler_process_alive(state: Path) -> bool:
    try:
        record = cron_daemon._runtime_context(str(state))[1]
        return cron_daemon.cron_scheduler._proc_alive(record["pid"], record["process_start"])
    except Exception:
        return False


if __name__ == "__main__":
    unittest.main()
