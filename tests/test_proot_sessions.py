from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import proot_sessions


class PRootSessionRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-proot-registry-")
        self.base = Path(self.temp.name)
        self.state = self.base / "state"
        self.state.mkdir(mode=0o700)
        self.rootfs = self.base / "rootfs"
        self.rootfs.mkdir(mode=0o700)
        self.launcher = self.base / "proot-distro"
        self.launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        self.launcher.chmod(0o700)

    def tearDown(self):
        self.temp.cleanup()

    def make_record(self, *, pid=1234567, process_start="old-start", state="running",
                    profile="isolated-probe", process_group=None):
        marker = "TERNUXX_PROOT_SESSION=" + "a" * 32
        if process_group is None:
            process_group = pid
        argv = [str(self.launcher), "login", "--minimal", "debian", "--",
                "/usr/bin/env", marker, "/bin/sleep", "300"]
        return {
            "schema_version": proot_sessions.SCHEMA,
            "session_id": "proot-" + "a" * 32,
            "profile": profile,
            "profile_version": 1,
            "purpose": proot_sessions.PROFILES[profile]["purpose"],
            "mode": proot_sessions.PROFILES[profile]["mode"],
            "rootfs": str(self.rootfs), "rootfs_device": self.rootfs.stat().st_dev,
            "rootfs_inode": self.rootfs.stat().st_ino,
            "launcher": str(self.launcher), "launcher_device": self.launcher.stat().st_dev,
            "launcher_inode": self.launcher.stat().st_ino,
            "pid": pid, "process_start": process_start, "process_group": process_group,
            "marker": marker, "expected_argv": argv,
            "working_directory": "guest-default", "environment_profile": "isolated-no-host-home-or-display",
            "created_at": "2026-10-20T00:00:00+00:00", "state": state,
            "last_verified_at": None, "last_exit_code": None, "transitions": [],
        }

    def make_record(self, *, pid=1234567, process_start="old-start", state="running",
                    profile="isolated-probe", process_group=None):
        marker = "TERNUXX_PROOT_SESSION=" + "a" * 32
        if process_group is None:
            process_group = pid
        argv = [str(self.launcher), "login", "--minimal", "debian", "--",
                "/usr/bin/env", marker, "/bin/sleep", "300"]
        return {
            "schema_version": proot_sessions.SCHEMA,
            "session_id": "proot-" + "a" * 32,
            "profile": profile,
            "profile_version": 1,
            "purpose": proot_sessions.PROFILES[profile]["purpose"],
            "mode": proot_sessions.PROFILES[profile]["mode"],
            "rootfs": str(self.rootfs), "rootfs_device": self.rootfs.stat().st_dev,
            "rootfs_inode": self.rootfs.stat().st_ino,
            "launcher": str(self.launcher), "launcher_device": self.launcher.stat().st_dev,
            "launcher_inode": self.launcher.stat().st_ino,
            "pid": pid, "process_start": process_start, "process_group": process_group,
            "marker": marker, "expected_argv": argv,
            "working_directory": "guest-default", "environment_profile": "isolated-no-host-home-or-display",
            "created_at": "2026-10-20T00:00:00+00:00", "state": state,
            "last_verified_at": None, "last_exit_code": None, "transitions": [],
        }

    def test_discovery_uses_validated_configured_rootfs_and_launcher(self):
        prefix = self.base / "prefix"
        root = prefix / "var/lib/proot-distro/containers/debian/rootfs"
        root.mkdir(parents=True)
        found = proot_sessions.discover_debian(
            prefix=str(prefix), which=lambda _name, path=None: str(self.launcher))
        self.assertEqual(found["rootfs"], str(root))
        self.assertEqual(found["rootfs_inode"], root.stat().st_ino)

    def test_symlinked_rootfs_is_rejected(self):
        prefix = self.base / "prefix"
        container = prefix / "var/lib/proot-distro/containers/debian"
        container.mkdir(parents=True)
        (container / "rootfs").symlink_to(self.rootfs)
        with self.assertRaisesRegex(proot_sessions.SessionError, "symlinked"):
            proot_sessions.discover_debian(
                prefix=str(prefix), which=lambda _name, path=None: str(self.launcher))

    def test_unowned_process_record_is_visible_but_stop_fails_closed(self):
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"],
                                start_new_session=True, close_fds=True)
        try:
            identity = proot_sessions._proc(proc.pid)
            self.assertIsNotNone(identity)
            root, path, _lock = proot_sessions._paths(self.state, create=True)
            session_id = "proot-" + "a" * 32
            record = {
                "schema_version": 1, "session_id": session_id, "profile": "isolated-probe",
                "rootfs": str(self.rootfs), "rootfs_device": self.rootfs.stat().st_dev,
                "rootfs_inode": self.rootfs.stat().st_ino, "launcher": str(self.launcher),
                "launcher_device": self.launcher.stat().st_dev, "launcher_inode": self.launcher.stat().st_ino,
                "pid": proc.pid, "process_start": identity["start"], "process_group": proc.pid,
                "marker": "TERNUXX_PROOT_SESSION=not-present", "expected_argv": ["/bin/sleep", "300"],
                "created_at": "2026-10-19T00:00:00+00:00", "state": "running",
                "last_verified_at": None,
            }
            proot_sessions._write_registry(root, path, [record])
            self.assertEqual(proot_sessions.list_sessions(self.state)[0]["ownership"], "unverified")
            with mock.patch.object(proot_sessions.os, "killpg") as signal_group:
                with self.assertRaisesRegex(proot_sessions.SessionError, "ownership is unknown"):
                    proot_sessions.stop_session(
                        self.state, session_id, confirmed=True, plan_id="plan-" + "0" * 64)
                signal_group.assert_not_called()
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_reconciliation_marks_only_proven_absent_process_as_exited_without_signal(self):
        root, path, _lock = proot_sessions._paths(self.state, create=True)
        session_id = "proot-" + "c" * 32
        record = {
            "schema_version": 1, "session_id": session_id, "profile": "isolated-probe",
            "rootfs": str(self.rootfs), "rootfs_device": self.rootfs.stat().st_dev,
            "rootfs_inode": self.rootfs.stat().st_ino, "launcher": str(self.launcher),
            "launcher_device": self.launcher.stat().st_dev, "launcher_inode": self.launcher.stat().st_ino,
            "pid": 2_000_000_000, "process_start": "old-start", "process_group": 2_000_000_000,
            "marker": "TERNUXX_PROOT_SESSION=" + "d" * 32, "expected_argv": ["/bin/sleep", "300"],
            "created_at": "2026-10-19T00:00:00+00:00", "state": "running",
            "last_verified_at": None,
        }
        proot_sessions._write_registry(root, path, [record])
        preview = proot_sessions.preview_reconcile(self.state, session_id)
        self.assertEqual(preview["evidence"], "process_absent")
        self.assertEqual(preview["action"], "mark_exited_without_signal")
        self.assertTrue(preview["confirmation_required"])
        with mock.patch.object(proot_sessions.os, "killpg") as signal_group:
            result = proot_sessions.reconcile_session(
                self.state, session_id, confirmed=True, plan_id=preview["plan_id"])
            signal_group.assert_not_called()
        self.assertEqual(result["state"], "stopped")
        self.assertFalse(result["signal_sent"])
        shown = proot_sessions.show_session(self.state, session_id)
        self.assertEqual(shown["state"], "stopped")
        self.assertTrue(shown["transitions"][-1]["source"].startswith("reconciled-"))
        self.assertIsNone(shown["last_exit_code"])

    def test_reconcile_refuses_live_process_with_lost_marker(self):
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"],
                                start_new_session=True, close_fds=True)
        try:
            identity = proot_sessions._proc(proc.pid)
            root, path, _lock = proot_sessions._paths(self.state, create=True)
            session_id = "proot-" + "e" * 32
            record = {
                "schema_version": 1, "session_id": session_id, "profile": "isolated-probe",
                "rootfs": str(self.rootfs), "rootfs_device": self.rootfs.stat().st_dev,
                "rootfs_inode": self.rootfs.stat().st_ino, "launcher": str(self.launcher),
                "launcher_device": self.launcher.stat().st_dev, "launcher_inode": self.launcher.stat().st_ino,
                "pid": proc.pid, "process_start": identity["start"], "process_group": proc.pid,
                "marker": "TERNUXX_PROOT_SESSION=" + "f" * 32, "expected_argv": ["/bin/sleep", "300"],
                "created_at": "2026-10-19T00:00:00+00:00", "state": "running",
                "last_verified_at": None,
            }
            proot_sessions._write_registry(root, path, [record])
            preview = proot_sessions.preview_reconcile(self.state, session_id)
            self.assertEqual(preview["evidence"], "same_process_live")
            self.assertFalse(preview["confirmation_required"])
            diagnosis = proot_sessions.inspect_recovery(self.state, session_id)
            self.assertFalse(diagnosis["evidence"]["marker_visible"])
            self.assertIn("marker_visible", diagnosis["uncertainty_reasons"])
            self.assertFalse(diagnosis["signal_allowed"])
            diagnosis = proot_sessions.inspect_recovery(self.state, session_id)
            self.assertFalse(diagnosis["evidence"]["marker_visible"])
            self.assertIn("marker_visible", diagnosis["uncertainty_reasons"])
            self.assertFalse(diagnosis["signal_allowed"])
            with self.assertRaisesRegex(proot_sessions.SessionError, "not positively established"):
                proot_sessions.reconcile_session(
                    self.state, session_id, confirmed=True, plan_id="plan-" + "0" * 64)
            self.assertEqual(proot_sessions.show_session(self.state, session_id)["recorded_state"], "running")
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_missing_process_identity_is_not_reconciled_or_replaced(self):
        root, path, _lock = proot_sessions._paths(self.state, create=True)
        record = self.make_record(pid=0, process_start="", state="starting", process_group=0)
        proot_sessions._write_registry(root, path, [record])
        preview = proot_sessions.preview_reconcile(self.state, record["session_id"])
        self.assertEqual(preview["evidence"], "recorded_process_identity_missing")
        self.assertFalse(preview["confirmation_required"])
        self.assertEqual(preview["action"], "retain_record_no_signal")
        with mock.patch.object(proot_sessions.os, "fork") as fork:
            with mock.patch.object(proot_sessions, "discover_debian", return_value={
                    "rootfs": str(self.rootfs), "rootfs_device": self.rootfs.stat().st_dev,
                    "rootfs_inode": self.rootfs.stat().st_ino, "launcher": str(self.launcher),
                    "launcher_device": self.launcher.stat().st_dev, "launcher_inode": self.launcher.stat().st_ino}):
                with self.assertRaisesRegex(proot_sessions.SessionError, "incomplete identity"):
                    proot_sessions.start_probe(self.state, prefix=str(self.base))
            fork.assert_not_called()
        self.assertEqual(proot_sessions.show_session(self.state, record["session_id"])["recorded_state"], "starting")

    def test_pid_reuse_can_reconcile_original_without_signaling_replacement(self):
        root, path, _lock = proot_sessions._paths(self.state, create=True)
        record = self.make_record()
        proot_sessions._write_registry(root, path, [record])
        replacement = {"start": "new-start", "state": "S", "pgrp": record["pid"], "session": record["pid"]}
        with mock.patch.object(proot_sessions, "_proc", return_value=replacement), \
             mock.patch.object(proot_sessions.os, "kill") as kill:
            preview = proot_sessions.preview_reconcile(self.state, record["session_id"])
            self.assertEqual(preview["evidence"], "pid_reused_original_exited")
            self.assertTrue(preview["confirmation_required"])
            result = proot_sessions.reconcile_session(
                self.state, record["session_id"], confirmed=True, plan_id=preview["plan_id"])
            self.assertEqual(result["evidence"], "pid_reused_original_exited")
            self.assertFalse(result["signal_sent"])
            kill.assert_not_called()

    def test_start_preview_rejects_changed_rootfs_identity_before_fork(self):
        original = {"rootfs": str(self.rootfs), "rootfs_device": self.rootfs.stat().st_dev,
                    "rootfs_inode": self.rootfs.stat().st_ino, "launcher": str(self.launcher),
                    "launcher_device": self.launcher.stat().st_dev, "launcher_inode": self.launcher.stat().st_ino}
        changed = dict(original)
        changed["rootfs_inode"] += 1
        plan_id = proot_sessions._start_plan("isolated-probe", original)
        with mock.patch.object(proot_sessions, "discover_debian", return_value=changed), \
             mock.patch.object(proot_sessions.os, "fork") as fork:
            with self.assertRaisesRegex(proot_sessions.SessionError, "preview is stale"):
                proot_sessions.start_probe(self.state, prefix=str(self.base), expected_plan_id=plan_id)
            fork.assert_not_called()
        self.assertFalse((self.state / "proot").exists())

    def test_permission_hidden_process_is_not_treated_as_absent(self):
        root, path, _lock = proot_sessions._paths(self.state, create=True)
        record = self.make_record()
        proot_sessions._write_registry(root, path, [record])
        with mock.patch.object(proot_sessions, "_proc", return_value=None), \
             mock.patch.object(proot_sessions.os, "kill", side_effect=PermissionError):
            preview = proot_sessions.preview_reconcile(self.state, record["session_id"])
        self.assertEqual(preview["evidence"], "identity_unreadable")
        self.assertFalse(preview["confirmation_required"])
        self.assertFalse(preview["signal_allowed"])

    def test_same_process_with_changed_session_group_is_not_reconciled(self):
        root, path, _lock = proot_sessions._paths(self.state, create=True)
        record = self.make_record()
        proot_sessions._write_registry(root, path, [record])
        changed = {"start": record["process_start"], "state": "S",
                   "pgrp": record["process_group"] + 1, "session": record["process_group"] + 1}
        with mock.patch.object(proot_sessions, "_proc", return_value=changed):
            preview = proot_sessions.preview_reconcile(self.state, record["session_id"])
        self.assertEqual(preview["evidence"], "same_process_identity_changed")
        self.assertFalse(preview["confirmation_required"])

    def test_recovery_retains_sanitized_historical_start_failure_evidence(self):
        root, path, _lock = proot_sessions._paths(self.state, create=True)
        record = self.make_record(state="unverified")
        record["transitions"] = [{"state": "unverified", "at": "2026-10-20T00:00:00+00:00",
                                  "source": "login-start-failed-evidence:entry=same-process-live;grp=1;mark=0;sig=0;cwd=u;fs=1;bin=1"}]
        proot_sessions._write_registry(root, path, [record])
        diagnosis = proot_sessions.inspect_recovery(self.state, record["session_id"])
        self.assertEqual(diagnosis["historical_start_failure_evidence"]["mark"], False)
        self.assertEqual(diagnosis["historical_start_failure_evidence"]["sig"], False)
        self.assertEqual(diagnosis["historical_start_failure_evidence"]["grp"], True)
        self.assertEqual(diagnosis["historical_start_failure_evidence"]["cwd"], None)

    def test_health_reports_exit_and_explicitly_disclaims_reattach(self):
        root, path, _lock = proot_sessions._paths(self.state, create=True)
        record = self.make_record(state="stopped")
        record["last_exit_code"] = 0
        proot_sessions._write_registry(root, path, [record])
        health = proot_sessions.session_health(self.state, record["session_id"])
        self.assertEqual(health["exit_code"], 0)
        self.assertFalse(health["reattach_supported"])
        self.assertEqual(health["attachment"], "none")
        self.assertTrue(health["read_only"])
        self.assertLessEqual(len(health["diagnostics"]), 16)

    def test_malformed_record_types_and_symlinked_registry_fail_closed(self):
        root, path, _lock = proot_sessions._paths(self.state, create=True)
        record = self.make_record()
        record["profile"] = []
        proot_sessions._write_registry(root, path, [record])
        with self.assertRaises(proot_sessions.SessionError):
            proot_sessions.list_sessions(self.state)
        path.unlink()
        valid = self.make_record()
        target = self.base / "outside-registry.json"
        target.write_text(json.dumps({"schema_version": proot_sessions.SCHEMA, "sessions": [valid]}), encoding="utf-8")
        target.chmod(0o600)
        path.symlink_to(target)
        with self.assertRaisesRegex(proot_sessions.SessionError, "identity or permissions are unsafe"):
            proot_sessions.list_sessions(self.state)

    def test_missing_process_identity_is_not_reconciled_or_replaced(self):
        root, path, _lock = proot_sessions._paths(self.state, create=True)
        record = self.make_record(pid=0, process_start="", state="starting", process_group=0)
        proot_sessions._write_registry(root, path, [record])
        preview = proot_sessions.preview_reconcile(self.state, record["session_id"])
        self.assertEqual(preview["evidence"], "recorded_process_identity_missing")
        self.assertFalse(preview["confirmation_required"])
        self.assertEqual(preview["action"], "retain_record_no_signal")
        with mock.patch.object(proot_sessions.os, "fork") as fork:
            with mock.patch.object(proot_sessions, "discover_debian", return_value={
                    "rootfs": str(self.rootfs), "rootfs_device": self.rootfs.stat().st_dev,
                    "rootfs_inode": self.rootfs.stat().st_ino, "launcher": str(self.launcher),
                    "launcher_device": self.launcher.stat().st_dev, "launcher_inode": self.launcher.stat().st_ino}):
                with self.assertRaisesRegex(proot_sessions.SessionError, "incomplete identity"):
                    proot_sessions.start_probe(self.state, prefix=str(self.base))
            fork.assert_not_called()
        self.assertEqual(proot_sessions.show_session(self.state, record["session_id"])["recorded_state"], "starting")

    def test_pid_reuse_can_reconcile_original_without_signaling_replacement(self):
        root, path, _lock = proot_sessions._paths(self.state, create=True)
        record = self.make_record()
        proot_sessions._write_registry(root, path, [record])
        replacement = {"start": "new-start", "state": "S", "pgrp": record["pid"], "session": record["pid"]}
        with mock.patch.object(proot_sessions, "_proc", return_value=replacement), \
             mock.patch.object(proot_sessions.os, "kill") as kill:
            preview = proot_sessions.preview_reconcile(self.state, record["session_id"])
            self.assertEqual(preview["evidence"], "pid_reused_original_exited")
            self.assertTrue(preview["confirmation_required"])
            result = proot_sessions.reconcile_session(
                self.state, record["session_id"], confirmed=True, plan_id=preview["plan_id"])
            self.assertEqual(result["evidence"], "pid_reused_original_exited")
            self.assertFalse(result["signal_sent"])
            kill.assert_not_called()

    def test_start_preview_rejects_changed_rootfs_identity_before_fork(self):
        original = {"rootfs": str(self.rootfs), "rootfs_device": self.rootfs.stat().st_dev,
                    "rootfs_inode": self.rootfs.stat().st_ino, "launcher": str(self.launcher),
                    "launcher_device": self.launcher.stat().st_dev, "launcher_inode": self.launcher.stat().st_ino}
        changed = dict(original)
        changed["rootfs_inode"] += 1
        plan_id = proot_sessions._start_plan("isolated-probe", original)
        with mock.patch.object(proot_sessions, "discover_debian", return_value=changed), \
             mock.patch.object(proot_sessions.os, "fork") as fork:
            with self.assertRaisesRegex(proot_sessions.SessionError, "preview is stale"):
                proot_sessions.start_probe(self.state, prefix=str(self.base), expected_plan_id=plan_id)
            fork.assert_not_called()
        self.assertFalse((self.state / "proot").exists())

    def test_permission_hidden_process_is_not_treated_as_absent(self):
        root, path, _lock = proot_sessions._paths(self.state, create=True)
        record = self.make_record()
        proot_sessions._write_registry(root, path, [record])
        with mock.patch.object(proot_sessions, "_proc", return_value=None), \
             mock.patch.object(proot_sessions.os, "kill", side_effect=PermissionError):
            preview = proot_sessions.preview_reconcile(self.state, record["session_id"])
        self.assertEqual(preview["evidence"], "identity_unreadable")
        self.assertFalse(preview["confirmation_required"])
        self.assertFalse(preview["signal_allowed"])

    def test_same_process_with_changed_session_group_is_not_reconciled(self):
        root, path, _lock = proot_sessions._paths(self.state, create=True)
        record = self.make_record()
        proot_sessions._write_registry(root, path, [record])
        changed = {"start": record["process_start"], "state": "S",
                   "pgrp": record["process_group"] + 1, "session": record["process_group"] + 1}
        with mock.patch.object(proot_sessions, "_proc", return_value=changed):
            preview = proot_sessions.preview_reconcile(self.state, record["session_id"])
        self.assertEqual(preview["evidence"], "same_process_identity_changed")
        self.assertFalse(preview["confirmation_required"])

    def test_recovery_retains_sanitized_historical_start_failure_evidence(self):
        root, path, _lock = proot_sessions._paths(self.state, create=True)
        record = self.make_record(state="unverified")
        record["transitions"] = [{"state": "unverified", "at": "2026-10-20T00:00:00+00:00",
                                  "source": "login-start-failed-evidence:entry=same-process-live;grp=1;mark=0;sig=0;cwd=u;fs=1;bin=1"}]
        proot_sessions._write_registry(root, path, [record])
        diagnosis = proot_sessions.inspect_recovery(self.state, record["session_id"])
        self.assertEqual(diagnosis["historical_start_failure_evidence"]["mark"], False)
        self.assertEqual(diagnosis["historical_start_failure_evidence"]["sig"], False)
        self.assertEqual(diagnosis["historical_start_failure_evidence"]["grp"], True)
        self.assertEqual(diagnosis["historical_start_failure_evidence"]["cwd"], None)

    def test_health_reports_exit_and_explicitly_disclaims_reattach(self):
        root, path, _lock = proot_sessions._paths(self.state, create=True)
        record = self.make_record(state="stopped")
        record["last_exit_code"] = 0
        proot_sessions._write_registry(root, path, [record])
        health = proot_sessions.session_health(self.state, record["session_id"])
        self.assertEqual(health["exit_code"], 0)
        self.assertFalse(health["reattach_supported"])
        self.assertEqual(health["attachment"], "none")
        self.assertTrue(health["read_only"])
        self.assertLessEqual(len(health["diagnostics"]), 16)

    def test_malformed_record_types_and_symlinked_registry_fail_closed(self):
        root, path, _lock = proot_sessions._paths(self.state, create=True)
        record = self.make_record()
        record["profile"] = []
        proot_sessions._write_registry(root, path, [record])
        with self.assertRaises(proot_sessions.SessionError):
            proot_sessions.list_sessions(self.state)
        path.unlink()
        valid = self.make_record()
        target = self.base / "outside-registry.json"
        target.write_text(json.dumps({"schema_version": proot_sessions.SCHEMA, "sessions": [valid]}), encoding="utf-8")
        target.chmod(0o600)
        path.symlink_to(target)
        with self.assertRaisesRegex(proot_sessions.SessionError, "identity or permissions are unsafe"):
            proot_sessions.list_sessions(self.state)

    def test_malformed_registry_fails_closed(self):
        root, path, _lock = proot_sessions._paths(self.state, create=True)
        path.write_text("{", encoding="utf-8")
        path.chmod(0o600)
        with self.assertRaisesRegex(proot_sessions.SessionError, "corrupt"):
            proot_sessions.list_sessions(self.state)


    def test_profile_inventory_exposes_validated_headless_and_interactive_profiles(self):
        prefix = self.base / "prefix"
        root = prefix / "var/lib/proot-distro/containers/debian/rootfs"
        (root / "usr/bin").mkdir(parents=True)
        (root / "bin").mkdir()
        (root / "etc").mkdir()
        for name in ("env", "bash", "sleep"):
            target = root / ("usr/bin/" + name if name == "env" else "bin/" + name)
            target.write_text("#!/bin/sh\n", encoding="utf-8")
            target.chmod(0o700)
        (root / "etc/passwd").write_text("sbj:x:1000:1000::/home/sbj:/bin/bash\n", encoding="utf-8")
        with mock.patch("shutil.which", return_value=str(self.launcher)):
            result = proot_sessions.profile_inventory(prefix=str(prefix))
        self.assertEqual({item["id"] for item in result["profiles"]},
                         {"isolated-probe", "debian-interactive"})
        self.assertTrue(all(item["available"] for item in result["profiles"]))
        self.assertEqual(next(x for x in result["profiles"] if x["id"] == "debian-interactive")["mode"],
                         "foreground-tty")

    def test_profile_preview_binds_plan_to_rootfs_launcher_and_profile(self):
        prefix = self.base / "prefix"
        root = prefix / "var/lib/proot-distro/containers/debian/rootfs"
        (root / "usr/bin").mkdir(parents=True)
        (root / "bin").mkdir()
        (root / "etc").mkdir()
        for executable in (root / "usr/bin/env", root / "bin/sleep", root / "bin/bash"):
            executable.write_text("#!/bin/sh\\n", encoding="utf-8")
            executable.chmod(0o700)
        (root / "etc/passwd").write_text("sbj:x:1000:1000::/home/sbj:/bin/bash\\n", encoding="utf-8")
        with mock.patch("shutil.which", return_value=str(self.launcher)):
            first = proot_sessions.preview_start("isolated-probe", prefix=str(prefix))
            second = proot_sessions.preview_start("debian-interactive", prefix=str(prefix))
        self.assertNotEqual(first["plan_id"], second["plan_id"])
        self.assertTrue(first["confirmation_required"])
        with self.assertRaisesRegex(proot_sessions.SessionError, "unsupported"):
            proot_sessions.preview_start("arbitrary-shell", prefix=str(prefix))

    def test_interactive_profile_refuses_non_tty_before_creating_state(self):
        with mock.patch.object(proot_sessions.os, "isatty", return_value=False):
            with self.assertRaisesRegex(proot_sessions.SessionError, "attached terminal"):
                proot_sessions.login_interactive(
                    self.state, prefix=str(self.base), confirmed=True, plan_id="plan-x")
        self.assertFalse((self.state / "proot").exists())

    def test_v1_session_records_are_read_as_v2_without_claiming_unowned_process(self):
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"],
                                start_new_session=True, close_fds=True)
        try:
            identity = proot_sessions._proc(proc.pid)
            root, path, _lock = proot_sessions._paths(self.state, create=True)
            old = {
                "schema_version": 1, "session_id": "proot-" + "b" * 32, "profile": "isolated-probe",
                "rootfs": str(self.rootfs), "rootfs_device": self.rootfs.stat().st_dev,
                "rootfs_inode": self.rootfs.stat().st_ino, "launcher": str(self.launcher),
                "launcher_device": self.launcher.stat().st_dev, "launcher_inode": self.launcher.stat().st_ino,
                "pid": proc.pid, "process_start": identity["start"], "process_group": proc.pid,
                "marker": "TERNUXX_PROOT_SESSION=not-present", "expected_argv": ["/bin/sleep", "300"],
                "created_at": "2026-10-19T00:00:00+00:00", "state": "running", "last_verified_at": None,
            }
            (root / "sessions.json").write_text(json.dumps({"schema_version": 1, "sessions": [old]}), encoding="utf-8")
            (root / "sessions.json").chmod(0o600)
            shown = proot_sessions.show_session(self.state, old["session_id"], include_private=True)
            self.assertEqual(shown["schema_version"], 3)
            self.assertEqual(shown["profile_version"], 1)
            self.assertEqual(shown["ownership"], "unverified")
            self.assertEqual(shown["state"], "unverified")
            self.assertEqual(shown["recorded_state"], "running")
            self.assertIsNone(shown["last_exit_code"])
        finally:
            proc.terminate()
            proc.wait(timeout=5)



class PRootVerificationFixtureTests(unittest.TestCase):
    def setUp(self):
        import os
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-proot-verify-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.proc_root = self.base / "proc"
        self.pid = 4217
        self.proc = self.proc_root / str(self.pid)
        self.proc.mkdir(parents=True)
        self.rootfs = self.base / "rootfs"
        self.rootfs.mkdir()
        (self.rootfs / "etc").mkdir()
        (self.rootfs / "etc/passwd").write_text("sbj:x:1000:1000::/home/sbj:/bin/bash\n")
        self.launcher = self.base / "proot-distro"
        self.launcher.write_text("# fixture launcher\n")
        self.other_cwd = self.base / "other"
        self.other_cwd.mkdir()
        (self.proc / "cwd").symlink_to(self.rootfs, target_is_directory=True)
        self.marker = "TERNUXX_PROOT_SESSION=" + "a" * 32
        self.record = {
            "pid": self.pid, "process_start": "77", "process_group": self.pid,
            "profile": "debian-interactive", "rootfs": str(self.rootfs),
            "rootfs_device": self.rootfs.stat().st_dev, "rootfs_inode": self.rootfs.stat().st_ino,
            "launcher": str(self.launcher), "launcher_device": self.launcher.stat().st_dev,
            "launcher_inode": self.launcher.stat().st_ino, "marker": self.marker,
            "expected_argv": [str(self.launcher), "login", "debian", "--shared-tmp",
                "--user", "sbj", "--", "/usr/bin/env", self.marker,
                "/bin/bash", "--login"],
        }
        cmd = ("proot --rootfs=. --change-id=1000:1000 --cwd=. /usr/bin/env "
               + self.marker + " /bin/bash --login").encode()
        (self.proc / "cmdline").write_bytes(cmd.replace(b" ", b"\0") + b"\0")
        (self.proc / "environ").write_bytes(self.marker.encode() + b"\0")
        (self.proc / "status").write_text("Name:\tproot\nUid:\t%d\t%d\t%d\t%d\n" %
                                          (os.getuid(), os.getuid(), os.getuid(), os.getuid()))
        self.identity = {"state": "S", "start": "77", "pgrp": self.pid, "session": self.pid}

    def verified(self):
        from unittest.mock import patch
        with patch.object(proot_sessions, "_proc", return_value=dict(self.identity)):
            return proot_sessions._verified(self.record, proc_root=self.proc_root)

    def test_synthetic_complete_identity_is_verified(self):
        self.assertTrue(self.verified())

    def test_identity_mismatches_fail_closed(self):
        from unittest.mock import patch
        cases = []
        cases.append(("stale", None, None, None))
        changed = dict(self.identity, start="78")
        cases.append(("pid reuse", changed, None, None))
        changed = dict(self.identity, pgrp=self.pid + 1)
        cases.append(("group mismatch", changed, None, None))
        for name, identity, marker, cmd in cases:
            with self.subTest(name=name):
                if marker is not None:
                    (self.proc / "environ").write_bytes(marker)
                if cmd is not None:
                    (self.proc / "cmdline").write_bytes(cmd)
                with patch.object(proot_sessions, "_proc", return_value=identity):
                    self.assertFalse(proot_sessions._verified(self.record, proc_root=self.proc_root))
                # Restore valid fixture bytes for the next case.
                (self.proc / "environ").write_bytes(self.marker.encode() + b"\0")
                (self.proc / "cmdline").write_bytes(
                    ("proot --rootfs=. --change-id=1000:1000 --cwd=. /usr/bin/env "
                     + self.marker + " /bin/bash --login").encode().replace(b" ", b"\0") + b"\0")

    def test_marker_launcher_rootfs_and_working_directory_mismatches_fail(self):
        from unittest.mock import patch
        original = (self.proc / "environ").read_bytes()
        (self.proc / "environ").write_bytes(b"")
        saved_cmd = (self.proc / "cmdline").read_bytes()
        (self.proc / "cmdline").write_bytes(b"proot\\0/bin/bash\\0--login\\0")
        self.assertFalse(self.verified())
        (self.proc / "environ").write_bytes(original)
        (self.proc / "cmdline").write_bytes(saved_cmd)
        original_cmd = (self.proc / "cmdline").read_bytes()
        (self.proc / "cmdline").write_bytes(b"proot\0wrong-command\0")
        self.assertFalse(self.verified())
        (self.proc / "cmdline").write_bytes(original_cmd)
        self.record["launcher_inode"] += 1
        self.assertFalse(self.verified())
        self.record["launcher_inode"] -= 1
        self.record["rootfs_inode"] += 1
        self.assertFalse(self.verified())
        self.record["rootfs_inode"] -= 1
        (self.proc / "cwd").unlink()
        (self.proc / "cwd").symlink_to(self.other_cwd, target_is_directory=True)
        self.assertFalse(self.verified())
        (self.proc / "cwd").unlink()
        (self.proc / "cwd").symlink_to(self.rootfs, target_is_directory=True)
        # Malformed and partially created ownership records are refused.
        self.record["marker"] = "malformed"
        self.assertFalse(self.verified())
        self.record["marker"] = self.marker
        partial = dict(self.record)
        partial.pop("process_start")
        # Registry validator rejects the partial record before ownership inspection.
        with self.assertRaises(proot_sessions.SessionError):
            proot_sessions._validate_record(partial)

    def test_unexpected_host_uid_and_unreadable_process_evidence_fail(self):
        from unittest.mock import patch
        (self.proc / "status").write_text("Uid:\t99999\t99999\t99999\t99999\n")
        self.assertFalse(self.verified())
        (self.proc / "status").write_text("Uid:\t%d\t%d\t%d\t%d\n" %
            (os.getuid(), os.getuid(), os.getuid(), os.getuid()))
        (self.proc / "cmdline").unlink()
        self.assertFalse(self.verified())

    def test_ambiguous_process_recovery_never_signals_or_adopts(self):
        from unittest.mock import patch
        with patch.object(proot_sessions, "_proc", return_value=None):
            with patch.object(proot_sessions.os, "kill", side_effect=ProcessLookupError) as signal_pid:
                self.assertEqual(proot_sessions._reconcile_observation({
                    "pid": self.pid, "process_start": "77", "process_group": self.pid}), "process_absent")
                signal_pid.assert_called_once_with(self.pid, 0)
        with patch.object(proot_sessions, "_proc", return_value={
                "state": "S", "start": "77", "pgrp": self.pid, "session": self.pid + 1}):
            self.assertEqual(proot_sessions._reconcile_observation({
                "pid": self.pid, "process_start": "77", "process_group": self.pid}),
                "same_process_identity_changed")

    def test_proot_launch_environment_strips_loader_overrides_and_keeps_runtime(self):
        source = {"LD_PRELOAD": "/tmp/hostile-sentinel.so",
                  "LD_LIBRARY_PATH": "/tmp/hostile-libs",
                  "LD_AUDIT": "/tmp/audit-sentinel.so",
                  "PREFIX": "/termux/prefix", "PATH": "/termux/prefix/bin",
                  "TERM": "xterm-256color", "LANG": "C.UTF-8", "DISPLAY": ":9",
                  "MESA_LOADER_DRIVER_OVERRIDE": "fixture-driver"}
        host = proot_sessions._proot_host_environment(source)
        guest = proot_sessions._login_environment(self.marker, "a" * 32, source)
        for env in (host, guest):
            self.assertFalse(any(key.startswith("LD_") for key in env))
            self.assertEqual(env["PREFIX"], "/termux/prefix")
            self.assertEqual(env["PATH"], "/termux/prefix/bin")
        self.assertEqual(guest["TERM"], "xterm-256color")
        self.assertNotIn("DISPLAY", guest)
        self.assertNotIn("MESA_LOADER_DRIVER_OVERRIDE", guest)
        self.assertNotIn("VK_ICD_FILENAMES", guest)
        self.assertNotIn("PULSE_SERVER", guest)
        self.assertNotIn("XDG_RUNTIME_DIR", guest)
        self.assertEqual(guest[self.marker.split("=", 1)[0]], "a" * 32)

    def test_native_debian_sessions_receive_scoped_native_audio_endpoint(self):
        source = {"PREFIX": "/data/data/com.termux/files/usr", "TERMUX_VERSION": "test",
                  "HOME": "/data/data/com.termux/files/home", "PATH": "/termux/bin"}
        guest = proot_sessions._login_environment(self.marker, "b" * 32, source)
        self.assertEqual(guest["PULSE_SERVER"], "tcp:127.0.0.1:4713")
        self.assertEqual(guest["DISPLAY"], ":1")
        self.assertNotIn("VK_ICD_FILENAMES", guest)
        with tempfile.TemporaryDirectory(prefix="ternuxx-pulse-cookie-") as home:
            cookie = Path(home) / ".config/pulse/cookie"
            cookie.parent.mkdir(parents=True, mode=0o700)
            cookie.write_bytes(b"c" * 256)
            cookie.chmod(0o600)
            source["HOME"] = home
            args = proot_sessions._native_pulse_login_args(source)
        self.assertIn("PULSE_SERVER=tcp:127.0.0.1:4713", args)
        self.assertIn("DISPLAY=:1", args)
        self.assertIn("GALLIUM_DRIVER=zink", args)
        self.assertIn("MESA_LOADER_DRIVER_OVERRIDE=zink", args)
        self.assertIn("PULSE_COOKIE=/tmp/.ternuxx-pulse-cookie", args)
if __name__ == "__main__":
    unittest.main()
