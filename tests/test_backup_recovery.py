"""Fixture coverage for interrupted backup creation reconciliation."""
from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import config_recovery  # noqa: E402
import backup_recovery  # noqa: E402
import management_service  # noqa: E402
import operation_journal  # noqa: E402
import operation_recovery  # noqa: E402


class BackupRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-backup-recovery-")
        self.home = Path(self.temp.name) / "home"
        self.home.mkdir()
        self.state = self.home / ".local/share/ternuxx"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def pending(self, name: str = "snapshot") -> str:
        return operation_journal.begin(str(self.state), "recovery.backup.create",
                                      f"create backup {name}", home_dir=self.home)

    def make_archive(self, name: str = "snapshot") -> None:
        plan = config_recovery.create_backup(home=str(self.home), state_dir=str(self.state), name=name)
        config_recovery.create_backup(home=str(self.home), state_dir=str(self.state), name=name,
                                      confirmed=True, plan_id=plan["plan_id"])

    def test_valid_archive_resolves_complete_and_only_updates_journal(self) -> None:
        self.make_archive()
        operation_id = self.pending()
        plan = operation_recovery.preview(operation_id, prefix="/unused", home=self.home, state_dir=self.state)
        self.assertEqual(plan["resolution"], "complete")
        self.assertEqual(plan["archive_integrity"], "valid")
        self.assertEqual(plan["affected_paths"], [str(self.state.resolve() / "operations" / f"{operation_id}.json")])
        result = operation_recovery.resolve(operation_id, prefix="/unused", home=self.home, state_dir=self.state,
                                            confirmed=True, plan_id=str(plan["plan_id"]))
        self.assertFalse(result["archive_changed"])
        self.assertEqual(operation_journal.inspect_record(str(self.state), operation_id, home_dir=self.home)["status"], "complete")

    def test_absent_archive_resolves_failed_after_exact_preview(self) -> None:
        operation_id = self.pending()
        record = operation_journal.inspect_record(str(self.state), operation_id, home_dir=self.home)
        plan = operation_recovery.preview(operation_id, prefix="/unused", home=self.home, state_dir=self.state)
        self.assertEqual(plan["resolution"], "failed")
        self.assertEqual(plan["archive_integrity"], "absent")
        with self.assertRaisesRegex(ValueError, "invalid backup recovery"):
            operation_journal.resolve_backup_record(
                str(self.state), operation_id, expected_updated_at=str(record["updated_at"]),
                backup_id="snapshot", archive_integrity="unknown", home_dir=self.home,
            )
        self.assertEqual(operation_journal.inspect_record(str(self.state), operation_id, home_dir=self.home)["status"], "starting")
        operation_recovery.resolve(operation_id, prefix="/unused", home=self.home, state_dir=self.state,
                                   confirmed=True, plan_id=str(plan["plan_id"]))
        self.assertEqual(operation_journal.inspect_record(str(self.state), operation_id, home_dir=self.home)["status"], "failed")

    def test_corrupt_archive_and_stale_preview_fail_closed(self) -> None:
        self.make_archive()
        operation_id = self.pending()
        plan = operation_recovery.preview(operation_id, prefix="/unused", home=self.home, state_dir=self.state)
        archive = self.state / "backups/snapshot.json"
        archive.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(backup_recovery.BackupRecoveryError, "cannot be verified"):
            operation_recovery.preview(operation_id, prefix="/unused", home=self.home, state_dir=self.state)
        archive.unlink()
        current = operation_recovery.preview(operation_id, prefix="/unused", home=self.home, state_dir=self.state)
        with self.assertRaisesRegex(backup_recovery.BackupRecoveryError, "changed"):
            operation_recovery.resolve(operation_id, prefix="/unused", home=self.home, state_dir=self.state,
                                       confirmed=True, plan_id=str(plan["plan_id"]))
        self.assertEqual(current["resolution"], "failed")
        self.assertEqual(operation_journal.inspect_record(str(self.state), operation_id, home_dir=self.home)["status"], "starting")

    def test_management_api_preview_and_confirmation_cover_backup_recovery(self) -> None:
        operation_id = self.pending()
        env = {
            "HOME": str(self.home),
            "NATIVERNUX_STATE_DIR": str(self.state),
            "TERMUX_VERSION": "fixture",
            "PREFIX": "/data/data/com.termux/files/usr",
        }
        preview_response = management_service.dispatch({
            "api_version": 1, "request_id": "backup-recovery-preview",
            "operation": "recovery.resolve", "args": {"operation_id": operation_id},
        }, env=env)
        self.assertTrue(preview_response["ok"], preview_response)
        plan = preview_response["data"]
        self.assertEqual(plan["archive_integrity"], "absent")
        applied_response = management_service.dispatch({
            "api_version": 1, "request_id": "backup-recovery-confirm",
            "operation": "recovery.resolve",
            "args": {"operation_id": operation_id, "confirmed": True, "plan_id": plan["plan_id"]},
        }, env=env)
        self.assertTrue(applied_response["ok"], applied_response)
        self.assertEqual(applied_response["data"]["resolution"], "failed")
        self.assertEqual(operation_journal.inspect_record(str(self.state), operation_id, home_dir=self.home)["status"], "failed")


if __name__ == "__main__":
    unittest.main()
