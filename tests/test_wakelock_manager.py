"""Persistent owner-lease and platform-command tests for Wake Lock management."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import wakelock_manager  # noqa: E402


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str], **kwargs):
        self.calls.append(args)
        class Result:
            returncode = 0
            stdout = ""
            stderr = ""
        return Result()


class WakeLockManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-wakelock-")
        self.state = Path(self.temp.name) / "home/.local/state/ternuxx"
        self.pid = __import__("os").getpid()
        self.runner = FakeRunner()
        self.boot = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def acquire(self, owner: str, persistent: bool = False):
        return wakelock_manager.acquire(
            state_dir=self.state, owner=owner, persistent=persistent,
            caller_pid=self.pid, prefix="/termux", runner=self.runner,
        )

    def release(self, owner: str, persistent: bool = False, pid: int | None = None):
        return wakelock_manager.release(
            state_dir=self.state, owner=owner, persistent=persistent,
            caller_pid=self.pid if pid is None else pid, prefix="/termux", runner=self.runner,
        )

    def test_two_owners_share_one_global_acquire_and_only_last_release_unlocks(self) -> None:
        with patch.object(wakelock_manager, "_boot_id", return_value=self.boot):
            self.acquire("native.desktop")
            self.acquire("native.gateway")
            self.assertEqual(self.runner.calls, [["/termux/bin/termux-wake-lock"]])
            one = self.release("native.desktop")
            self.assertEqual(one["state"], "released_lease_lock_retained")
            self.assertEqual(len(self.runner.calls), 1)
            last = self.release("native.gateway")
            self.assertEqual(last["state"], "released_last_registered_lease")
            self.assertEqual(self.runner.calls[-1], ["/termux/bin/termux-wake-unlock"])

    def test_other_process_cannot_release_a_process_lease(self) -> None:
        with patch.object(wakelock_manager, "_boot_id", return_value=self.boot):
            self.acquire("other-service.desktop")
            with self.assertRaises(wakelock_manager.WakeLockError):
                self.release("other-service.desktop", pid=self.pid + 100000)
            self.assertEqual(len(self.runner.calls), 1)
            self.assertEqual(wakelock_manager.status(state_dir=self.state)["managed_owners"], ["other-service.desktop"])

    def test_persistent_lease_is_limited_to_native_sshd(self) -> None:
        with patch.object(wakelock_manager, "_boot_id", return_value=self.boot):
            with self.assertRaises(wakelock_manager.WakeLockError):
                self.acquire("other-service.desktop", persistent=True)
            acquired = self.acquire("native.sshd", persistent=True)
            self.assertEqual(acquired["owner_count"], 1)
            released = self.release("native.sshd", persistent=True)
            self.assertEqual(released["state"], "released_last_registered_lease")

    def test_changed_boot_discards_stale_leases_without_releasing_old_boot_lock(self) -> None:
        with patch.object(wakelock_manager, "_boot_id", return_value=self.boot):
            self.acquire("native.sshd", persistent=True)
        self.runner.calls.clear()
        new_boot = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        with patch.object(wakelock_manager, "_boot_id", return_value=new_boot):
            status = wakelock_manager.status(state_dir=self.state)
            self.assertEqual(status["stale_owners"], ["native.sshd"])
            self.assertEqual(status["boot_id_relation"], "different")
            self.acquire("other-service.desktop")
            self.assertEqual(self.runner.calls, [["/termux/bin/termux-wake-lock"]])
            record = json.loads((self.state / "wakelock/owners.json").read_text())
            self.assertEqual(record["boot_id"], new_boot)
            self.assertEqual(set(record["owners"]), {"other-service.desktop"})

    def test_acquire_clears_record_only_when_kernel_confirms_pid_absent(self) -> None:
        with patch.object(wakelock_manager, "_boot_id", return_value=self.boot):
            root = self.state / "wakelock"
            root.mkdir(parents=True, mode=0o700)
            record = {"schema_version": 1, "boot_id": self.boot, "last_error": None,
                      "owners": {"native.sshd": {"pid": 99999999, "process_start": "1",
                                                   "persistent": True, "reason": "native_sshd"}}}
            (root / "owners.json").write_text(json.dumps(record))
            (root / "owners.json").chmod(0o600)
            with patch.object(wakelock_manager, "_process_start", side_effect=lambda pid: "caller-start" if pid == self.pid else None), \
                 patch.object(wakelock_manager, "_pid_is_absent", return_value=True):
                result = self.acquire("native.sshd", persistent=True)
            self.assertEqual(result["state"], "acquired")
            self.assertEqual(len(self.runner.calls), 1)

    def test_acquire_fails_closed_if_unavailable_pid_may_exist(self) -> None:
        with patch.object(wakelock_manager, "_boot_id", return_value=self.boot):
            root = self.state / "wakelock"
            root.mkdir(parents=True, mode=0o700)
            record = {"schema_version": 1, "boot_id": self.boot, "last_error": None,
                      "owners": {"native.sshd": {"pid": 99999999, "process_start": "1",
                                                   "persistent": True, "reason": "native_sshd"}}}
            (root / "owners.json").write_text(json.dumps(record))
            (root / "owners.json").chmod(0o600)
            with patch.object(wakelock_manager, "_process_start", side_effect=lambda pid: "caller-start" if pid == self.pid else None), \
                 patch.object(wakelock_manager, "_pid_is_absent", return_value=False):
                with self.assertRaisesRegex(wakelock_manager.WakeLockError, "identity is unavailable"):
                    self.acquire("native.sshd", persistent=True)
            self.assertEqual(self.runner.calls, [])

    def test_status_outcomes_match_strict_response_schema(self) -> None:
        schema = json.loads((ROOT / "schemas/wakelock-status.schema.json").read_text())
        with patch.object(wakelock_manager, "_boot_id", return_value=None):
            reports = [wakelock_manager.status(state_dir=self.state)]
        with patch.object(wakelock_manager, "_boot_id", return_value=self.boot):
            self.acquire("native.sshd", persistent=True)
            reports.append(wakelock_manager.status(state_dir=self.state))
        other_boot = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        with patch.object(wakelock_manager, "_boot_id", return_value=other_boot):
            reports.append(wakelock_manager.status(state_dir=self.state))
        expected = set(schema["properties"])
        for report in reports:
            self.assertEqual(set(report), expected)
            self.assertEqual(report["component"], schema["properties"]["component"]["const"])
            self.assertIn(report["boot_id_relation"], schema["properties"]["boot_id_relation"]["enum"])
            self.assertIn(report["coordinator_state"], schema["properties"]["coordinator_state"]["enum"])
            self.assertEqual(report["safety"]["read_only"], True)
            self.assertEqual(report["safety"]["acquire_or_release_invoked"], False)

    def test_status_reports_matching_boot_id(self) -> None:
        with patch.object(wakelock_manager, "_boot_id", return_value=self.boot):
            self.acquire("native.sshd", persistent=True)
            status = wakelock_manager.status(state_dir=self.state)
            self.assertEqual(status["boot_id_relation"], "match")

    def test_status_is_read_only_and_hides_platform_lock_state(self) -> None:
        with patch.object(wakelock_manager, "_boot_id", return_value=self.boot):
            status = wakelock_manager.status(state_dir=self.state)
            self.assertEqual(status["platform_lock_state"], "unknown")
            self.assertEqual(status["boot_id_relation"], "match")
            self.assertEqual(self.runner.calls, [])

    def test_status_reports_unknown_when_boot_id_unavailable(self) -> None:
        with patch.object(wakelock_manager, "_boot_id", return_value=None):
            status = wakelock_manager.status(state_dir=self.state)
            self.assertEqual(status["boot_id_relation"], "unknown")

    def test_service_policy_defaults_enabled_without_creating_state(self) -> None:
        report = wakelock_manager.service_policy_status(state_dir=self.state)
        self.assertTrue(report["persistent_lease_enabled"])
        self.assertFalse(report["configured"])
        self.assertFalse(self.state.exists())

    def test_service_policy_preview_confirm_apply_and_stale_plan(self) -> None:
        plan = wakelock_manager.service_policy_preview(state_dir=self.state, enabled=False)
        self.assertTrue(plan["changed"])
        unconfirmed = wakelock_manager.service_policy_apply(
            state_dir=self.state, enabled=False, confirmed=False, plan_id=plan["plan_id"])
        self.assertEqual(unconfirmed["status"], "confirmation_required")
        stale = wakelock_manager.service_policy_apply(
            state_dir=self.state, enabled=False, confirmed=True, plan_id="bad")
        self.assertEqual(stale["status"], "stale_plan")
        applied = wakelock_manager.service_policy_apply(
            state_dir=self.state, enabled=False, confirmed=True, plan_id=plan["plan_id"])
        self.assertEqual(applied["status"], "updated")
        report = wakelock_manager.service_policy_status(state_dir=self.state)
        self.assertFalse(report["persistent_lease_enabled"])
        policy = self.state / "wakelock/service-policy.json"
        self.assertEqual(policy.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.runner.calls, [])

    def test_disabled_service_policy_skips_only_future_persistent_acquire(self) -> None:
        plan = wakelock_manager.service_policy_preview(state_dir=self.state, enabled=False)
        wakelock_manager.service_policy_apply(state_dir=self.state, enabled=False,
                                               confirmed=True, plan_id=plan["plan_id"])
        with patch.object(wakelock_manager, "_process_start", return_value="caller-start"):
            result = self.acquire("native.sshd", persistent=True)
        self.assertEqual(result["state"], "policy_disabled")
        self.assertEqual(self.runner.calls, [])

    def test_disabling_policy_preserves_running_lease_until_owner_releases(self) -> None:
        with patch.object(wakelock_manager, "_boot_id", return_value=self.boot):
            self.acquire("native.sshd", persistent=True)
            plan = wakelock_manager.service_policy_preview(state_dir=self.state, enabled=False)
            wakelock_manager.service_policy_apply(state_dir=self.state, enabled=False,
                                                   confirmed=True, plan_id=plan["plan_id"])
            self.assertIn("native.sshd", wakelock_manager.status(state_dir=self.state)["managed_owners"])
            released = self.release("native.sshd", persistent=True)
        self.assertEqual(released["state"], "released_last_registered_lease")
        self.assertEqual(self.runner.calls[-1], ["/termux/bin/termux-wake-unlock"])

    def test_service_policy_rejects_symlink_and_non_private_file(self) -> None:
        self.state.mkdir(parents=True)
        root = self.state / "wakelock"
        root.mkdir(mode=0o700)
        target = self.state / "target"
        target.write_text('{"schema_version":1,"native_sshd_enabled":false}')
        (root / "service-policy.json").symlink_to(target)
        with self.assertRaises(wakelock_manager.WakeLockError):
            wakelock_manager.service_policy_status(state_dir=self.state)
        (root / "service-policy.json").unlink()
        policy = root / "service-policy.json"
        policy.write_text('{"schema_version":1,"native_sshd_enabled":false}')
        policy.chmod(0o644)
        with self.assertRaisesRegex(wakelock_manager.WakeLockError, "identity is not verified"):
            wakelock_manager.service_policy_status(state_dir=self.state)


if __name__ == "__main__":
    unittest.main()
