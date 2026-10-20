"""Fixture tests for the opt-in Android Activity monitoring policy."""
from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import gui_monitoring  # noqa: E402


class GuiMonitoringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="gui-monitor-policy-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "state"
        self.root.mkdir(mode=0o700)
        self.root.chmod(0o700)

    def test_policy_schema_matches_safe_disabled_default_and_bounds(self) -> None:
        import json
        schema = json.loads((ROOT / "schemas/gui-monitoring-policy.schema.json").read_text())
        default = gui_monitoring._default()
        self.assertEqual(schema["properties"]["schema_version"]["const"], gui_monitoring.SCHEMA_VERSION)
        self.assertEqual(set(schema["required"]), set(default))
        self.assertFalse(default["enabled"])
        self.assertFalse(default["activity_launch"])
        self.assertFalse(default["focus_check"])
        self.assertEqual(schema["properties"]["interval_seconds"]["minimum"], gui_monitoring.MIN_INTERVAL_SECONDS)
        self.assertEqual(schema["properties"]["interval_seconds"]["maximum"], gui_monitoring.MAX_INTERVAL_SECONDS)

    def test_status_is_read_only_and_defaults_to_disabled(self) -> None:
        result = gui_monitoring.status(self.root)
        self.assertTrue(result["read_only"])
        self.assertFalse(result["enabled"])
        self.assertEqual(result["interval_seconds"], 300)
        self.assertFalse(result["activity_requests_performed"])
        self.assertFalse(result["focus_probe_performed"])
        self.assertFalse((self.root / "gui-monitoring.json").exists())
        self.assertFalse((self.root / "log").exists())

    def test_configuration_is_atomic_private_and_units_are_normalized(self) -> None:
        result = gui_monitoring.configure(self.root, enabled=True, interval_value=2, unit="minutes")
        self.assertTrue(result["enabled"])
        self.assertEqual(result["interval_seconds"], 120)
        self.assertEqual((self.root / "gui-monitoring.json").stat().st_mode & 0o777, 0o600)
        saved = gui_monitoring.status(self.root)
        self.assertEqual(saved["interval_seconds"], 120)
        self.assertEqual(saved["scheduler"], "not_running")

    def test_interval_bounds_and_activity_requires_focus_check(self) -> None:
        for value, unit in ((29, "seconds"), (25, "hours"), (True, "seconds")):
            with self.subTest(value=value, unit=unit), self.assertRaises(gui_monitoring.MonitoringError):
                gui_monitoring.configure(self.root, interval_value=value, unit=unit)
        with self.assertRaises(gui_monitoring.MonitoringError):
            gui_monitoring.configure(self.root, activity_launch=True)

    def test_symlink_policy_is_rejected_without_following(self) -> None:
        outside = Path(self.temp.name) / "outside.json"
        outside.write_text('{"schema_version": 1}', encoding="utf-8")
        (self.root / "gui-monitoring.json").symlink_to(outside)
        with self.assertRaises(gui_monitoring.MonitoringError):
            gui_monitoring.status(self.root)
        self.assertEqual(outside.read_text(encoding="utf-8"), '{"schema_version": 1}')

    def test_monitor_once_disabled_does_not_probe_android_or_write_logs(self) -> None:
        with patch.object(gui_monitoring.subprocess, "run", side_effect=AssertionError("unexpected Android probe")):
            result = gui_monitoring.monitor_once(str(self.root), str(self.root), env={"PREFIX": "/missing"})
        self.assertEqual(result, {"result": "disabled", "android_probes_performed": False})
        self.assertFalse((self.root / "gui-monitoring.json").exists())
        self.assertFalse((self.root / "log").exists())

    def test_enabled_linux_only_monitoring_does_not_query_activity_or_focus(self) -> None:
        gui_monitoring.configure(self.root, enabled=True)
        with patch.object(gui_monitoring, "_linux_gui_state", return_value="running"), \
             patch.object(gui_monitoring.subprocess, "run", side_effect=AssertionError("unexpected Android probe")):
            result = gui_monitoring.monitor_once(str(self.root), str(self.root), env={"PREFIX": "/missing"})
        self.assertEqual(result["linux_gui_health"], "running")
        self.assertEqual(result["activity_availability"], "not_requested")
        self.assertEqual(result["activity_request_status"], "not_requested")
        self.assertFalse(result["android_probes_performed"])
        status = gui_monitoring.status(self.root)
        self.assertEqual(status["last_result"], "ok")
        self.assertEqual(status["activity_focus_status"], "not_requested")
        self.assertEqual(status["android_activity_availability"], "not_requested")
        self.assertTrue((self.root / "log/gui-monitoring.log").is_file())

    def test_activity_launch_requires_verified_background_focus_and_healthy_linux_session(self) -> None:
        prefix = Path(self.temp.name) / "prefix"
        (prefix / "bin").mkdir(parents=True)
        for name in ("pm", "dumpsys", "am"):
            path = prefix / "bin" / name
            path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            path.chmod(0o700)
        env = {"PREFIX": str(prefix)}
        responses = [
            SimpleNamespace(returncode=0, stdout="package:/system/app/TermuxX11.apk", stderr=""),
            SimpleNamespace(returncode=0, stdout="mResumedActivity: ActivityRecord{ x other.app/.Main}", stderr=""),
            SimpleNamespace(returncode=0, stdout="", stderr=""),
        ]
        with patch.object(gui_monitoring.subprocess, "run", side_effect=responses) as run:
            available, focus, request, error = gui_monitoring._activity_and_focus(
                env, do_focus=True, do_launch=True, linux_state="running")
        self.assertEqual((available, focus, request, error), ("available", "background", "requested", None))
        self.assertEqual(run.call_count, 3)
        self.assertIn("com.termux.x11/com.termux.x11.MainActivity", run.call_args.args[0])

    def test_activity_is_not_relaunched_when_already_foreground_or_linux_session_unhealthy(self) -> None:
        prefix = Path(self.temp.name) / "prefix"
        (prefix / "bin").mkdir(parents=True)
        for name in ("pm", "dumpsys", "am"):
            path = prefix / "bin" / name
            path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            path.chmod(0o700)
        env = {"PREFIX": str(prefix)}
        responses = [
            SimpleNamespace(returncode=0, stdout="package:/termux-x11.apk", stderr=""),
            SimpleNamespace(returncode=0, stdout="topResumedActivity=ActivityRecord{ x com.termux.x11/.MainActivity}", stderr=""),
        ]
        with patch.object(gui_monitoring.subprocess, "run", side_effect=responses) as run:
            _available, focus, request, _error = gui_monitoring._activity_and_focus(
                env, do_focus=True, do_launch=True, linux_state="running")
        self.assertEqual(focus, "foreground")
        self.assertEqual(request, "not_needed")
        self.assertEqual(run.call_count, 2)
        responses = [
            SimpleNamespace(returncode=0, stdout="package:/termux-x11.apk", stderr=""),
            SimpleNamespace(returncode=0, stdout="mResumedActivity: ActivityRecord{ x other.app/.Main}", stderr=""),
        ]
        with patch.object(gui_monitoring.subprocess, "run", side_effect=responses) as run:
            _available, focus, request, _error = gui_monitoring._activity_and_focus(
                env, do_focus=True, do_launch=True, linux_state="stale")
        self.assertEqual((focus, request), ("background", "not_requested"))
        self.assertEqual(run.call_count, 2)

    def test_next_check_uses_configured_interval(self) -> None:
        gui_monitoring.configure(self.root, enabled=True, interval_value=1, unit="hours")
        gui_monitoring.configure(self.root, enabled=True)
        data = gui_monitoring._read(self.root, self.root / "gui-monitoring.json")
        data["last_check_at"] = "2026-10-19T00:00:00+00:00"
        gui_monitoring._atomic_save(self.root, gui_monitoring._validate(data))
        result = gui_monitoring.status(self.root, now=datetime(2026, 10, 19, 0, 30, tzinfo=timezone.utc))
        self.assertEqual(result["next_check_at"], "2026-10-19T01:00:00+00:00")
        self.assertEqual(result["freshness"], "fresh")

    def test_scheduler_lock_reports_existing_singleton(self) -> None:
        gui_monitoring.configure(self.root, enabled=True)
        path = self.root / ".gui-monitor-scheduler.lock"
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(gui_monitoring.status(self.root)["scheduler"], "running")
        finally:
            os.close(fd)


if __name__ == "__main__":
    unittest.main()
