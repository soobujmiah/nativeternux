"""Fixture coverage for interrupted native desktop journal reconciliation."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import desktop_session_recovery  # noqa: E402
import operation_journal  # noqa: E402
import operation_recovery  # noqa: E402


class DesktopSessionRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-desktop-recovery-")
        self.home = Path(self.temp.name) / "home"
        self.home.mkdir()
        self.state = self.home / ".local/share/ternuxx"
        self.state.mkdir(parents=True, mode=0o700)
        self.state.chmod(0o700)
        self.proc = Path(self.temp.name) / "proc"
        self.proc.mkdir()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def pending(self, kind: str) -> str:
        detail = "display :2" if kind == "desktop.start" else "state running"
        operation_id = operation_journal.begin(str(self.state), kind, detail, home_dir=self.home)
        return operation_id

    def role(self, name: str, pid: int | None, *, live: bool = False) -> dict[str, object]:
        marker = {"supervisor": "desktop-supervisor.sh", "x11": "termux-x11",
                  "desktop": "xfce4-session"}[name]
        if live and pid is not None:
            proc = self.proc / str(pid)
            proc.mkdir()
            fields = ["S", "1", str(pid), str(pid)] + ["0"] * 15 + ["12345"]
            (proc / "stat").write_text(f"{pid} (fixture) {' '.join(fields)}\n", encoding="ascii")
            (proc / "cmdline").write_bytes(f"/fixture/{marker}\0".encode())
        elif pid is not None:
            import shutil
            shutil.rmtree(self.proc / str(pid), ignore_errors=True)
        return {"pid": pid, "start_ticks": "12345" if pid is not None else None,
                "pgid": pid if pid is not None else None, "sid": pid if pid is not None else None,
                "command_marker": marker}

    def write_session(self, status: str, *, live: bool = False) -> None:
        state = {"schema": 2, "owner": "ternuxx", "provider": "native", "display": ":2",
                 "status": status, "supervisor": self.role("supervisor", 101, live=live),
                 "x11": self.role("x11", 102 if live else None, live=live),
                 "desktop": self.role("desktop", 103 if live else None, live=live), "error": None}
        path = self.state / "session.json"
        path.write_text(json.dumps(state), encoding="utf-8")
        path.chmod(0o600)

    def test_start_running_exact_processes_can_be_reconciled_without_signals(self) -> None:
        operation_id = self.pending("desktop.start")
        self.write_session("running", live=True)
        plan = operation_recovery.preview(operation_id, prefix="/unused", home=self.home,
            state_dir=self.state, source="/unused", runner=lambda *_args, **_kwargs: None,
            proc_root=self.proc)
        self.assertEqual(plan["resolution"], "complete")
        schema = json.loads((ROOT / "schemas/desktop-session-recovery.schema.json").read_text())
        preview_schema, applied_schema = schema["oneOf"]
        self.assertEqual(set(plan), set(preview_schema["required"]))
        expected_journal = str(self.state.resolve() / "operations" / f"{operation_id}.json")
        self.assertEqual(plan["affected_paths"], [expected_journal])
        result = operation_recovery.resolve(operation_id, prefix="/unused", home=self.home,
            state_dir=self.state, confirmed=True, plan_id=str(plan["plan_id"]),
            source="/unused", runner=lambda *_args, **_kwargs: None, proc_root=self.proc)
        self.assertEqual(set(result), set(applied_schema["required"]))
        self.assertEqual(result["affected_paths"], [expected_journal])
        self.assertFalse(result["desktop_processes_signaled"])
        self.assertEqual(operation_journal.inspect_record(str(self.state), operation_id, home_dir=self.home)["status"], "complete")

    def test_stop_stopped_and_stop_incomplete_resolve_to_distinct_outcomes(self) -> None:
        operation_id = self.pending("desktop.stop")
        self.write_session("stopped")
        plan = desktop_session_recovery.preview(operation_id, home=self.home, state_dir=self.state, proc_root=self.proc)
        self.assertEqual(plan["resolution"], "complete")
        result = desktop_session_recovery.resolve(operation_id, home=self.home, state_dir=self.state,
            confirmed=True, plan_id=str(plan["plan_id"]), proc_root=self.proc)
        self.assertFalse(result["session_file_changed"])

        operation_id = self.pending("desktop.stop")
        self.write_session("stop_incomplete", live=True)
        state_file = self.state / "session.json"
        state = json.loads(state_file.read_text())
        state["supervisor"] = self.role("supervisor", 101)
        state_file.write_text(json.dumps(state), encoding="utf-8")
        state_file.chmod(0o600)
        plan = desktop_session_recovery.preview(operation_id, home=self.home, state_dir=self.state, proc_root=self.proc)
        self.assertEqual(plan["resolution"], "failed")
        self.assertEqual(plan["process_states"]["desktop"], "live")
        result = desktop_session_recovery.resolve(operation_id, home=self.home, state_dir=self.state,
            confirmed=True, plan_id=str(plan["plan_id"]), proc_root=self.proc)
        self.assertFalse(result["desktop_processes_signaled"])

    def test_live_or_ambiguous_state_and_lifecycle_lock_fail_closed(self) -> None:
        operation_id = self.pending("desktop.stop")
        self.write_session("running", live=True)
        with self.assertRaisesRegex(desktop_session_recovery.DesktopRecoveryError, "ambiguous"):
            desktop_session_recovery.preview(operation_id, home=self.home, state_dir=self.state, proc_root=self.proc)
        (self.state / ".session.lock").mkdir()
        with self.assertRaisesRegex(desktop_session_recovery.DesktopRecoveryError, "lock exists"):
            desktop_session_recovery.preview(operation_id, home=self.home, state_dir=self.state, proc_root=self.proc)

    def test_missing_process_inventory_fails_closed(self) -> None:
        operation_id = self.pending("desktop.stop")
        self.write_session("stopped")
        with self.assertRaisesRegex(desktop_session_recovery.DesktopRecoveryError, "Process inventory"):
            desktop_session_recovery.preview(operation_id, home=self.home, state_dir=self.state,
                proc_root=self.proc / "missing")

    def test_start_recovery_requires_the_journaled_display(self) -> None:
        operation_id = self.pending("desktop.start")
        self.write_session("running", live=True)
        path = self.state / "session.json"
        state = json.loads(path.read_text())
        state["display"] = ":3"
        path.write_text(json.dumps(state), encoding="utf-8")
        path.chmod(0o600)
        with self.assertRaisesRegex(desktop_session_recovery.DesktopRecoveryError, "display does not match"):
            desktop_session_recovery.preview(operation_id, home=self.home, state_dir=self.state, proc_root=self.proc)

    def test_stale_plan_and_unrecognized_or_unsafe_session_are_refused(self) -> None:
        operation_id = self.pending("desktop.stop")
        self.write_session("stopped")
        plan = desktop_session_recovery.preview(operation_id, home=self.home, state_dir=self.state, proc_root=self.proc)
        session_file = self.state / "session.json"
        session_file.write_text(session_file.read_text() + "\n", encoding="utf-8")
        session_file.chmod(0o600)
        with self.assertRaisesRegex(desktop_session_recovery.DesktopRecoveryError, "changed"):
            desktop_session_recovery.resolve(operation_id, home=self.home, state_dir=self.state,
                confirmed=True, plan_id=str(plan["plan_id"]), proc_root=self.proc)
        session_file.chmod(0o644)
        with self.assertRaisesRegex(desktop_session_recovery.DesktopRecoveryError, "ownership or mode"):
            desktop_session_recovery.preview(operation_id, home=self.home, state_dir=self.state, proc_root=self.proc)

    def test_crash_before_supervisor_writes_session_is_failed_without_process_action(self) -> None:
        operation_id = self.pending("desktop.start")
        plan = operation_recovery.preview(operation_id, prefix="/unused", home=self.home,
            state_dir=self.state, source="/unused", runner=lambda *_args, **_kwargs: None,
            proc_root=self.proc)
        self.assertEqual(plan["observed_session_status"], "absent")
        self.assertEqual(plan["resolution"], "failed")
        operation_recovery.resolve(operation_id, prefix="/unused", home=self.home,
            state_dir=self.state, confirmed=True, plan_id=str(plan["plan_id"]),
            source="/unused", runner=lambda *_args, **_kwargs: None, proc_root=self.proc)
        self.assertEqual(operation_journal.inspect_record(str(self.state), operation_id,
            home_dir=self.home)["status"], "failed")


if __name__ == "__main__":
    unittest.main()
