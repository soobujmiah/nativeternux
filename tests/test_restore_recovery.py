"""Fixture coverage for interrupted profile restore journal reconciliation."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import config_recovery  # noqa: E402
import operation_journal  # noqa: E402
import operation_recovery  # noqa: E402
import restore_recovery  # noqa: E402


def profile(mode: str) -> bytes:
    return json.dumps({"schema_version": 1, "owner": "ternuxx", "provider": "native", "profile": mode}).encode() + b"\n"


class RestoreRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-restore-recovery-")
        self.home = Path(self.temp.name) / "home"
        self.home.mkdir()
        self.state = self.home / ".local/share/ternuxx"
        self.source = self.state / "boot/profile.json"
        self.source.parent.mkdir(parents=True)
        self.source.write_bytes(profile("native"))
        self.source.chmod(0o600)
        self.backups = self.state / "backups"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def make_archive(self, name: str, content: bytes | None = None) -> None:
        if content is not None:
            self.source.write_bytes(content)
        plan = config_recovery.create_backup(home=str(self.home), state_dir=str(self.state), name=name)
        config_recovery.create_backup(home=str(self.home), state_dir=str(self.state), name=name,
                                      confirmed=True, plan_id=plan["plan_id"])

    def make_snapshot(self, operation_id: str) -> None:
        backup_id = f"rollback-{operation_id}"
        entries = config_recovery._target_entries(self.source)
        config_recovery._save_archive(self.backups / f"{backup_id}.json", backup_id, entries)

    def test_completed_restore_is_reconciled_from_exact_target_archive(self) -> None:
        self.make_archive("target-native")
        self.source.write_bytes(profile("cli-only"))
        operation_id = operation_journal.begin(str(self.state), "recovery.restore.apply",
                                               "restore backup target-native", home_dir=self.home)
        self.make_snapshot(operation_id)
        self.source.write_bytes(profile("native"))

        plan = operation_recovery.preview(operation_id, prefix="/unused", home=self.home, state_dir=self.state)
        self.assertEqual(plan["resolution"], "complete")
        self.assertEqual(plan["observed_outcome"], "archive_target")
        self.assertEqual(plan["affected_paths"], [str(self.state.resolve() / "operations" / f"{operation_id}.json")])
        schema = json.loads((ROOT / "schemas/profile-restore-recovery.schema.json").read_text())
        self.assertEqual(set(plan), set(schema["oneOf"][0]["required"]))
        result = operation_recovery.resolve(operation_id, prefix="/unused", home=self.home, state_dir=self.state,
                                            confirmed=True, plan_id=str(plan["plan_id"]))
        self.assertEqual(set(result), set(schema["oneOf"][1]["required"]))
        self.assertFalse(result["profile_file_changed"])
        self.assertEqual(self.source.read_bytes(), profile("native"))
        self.assertEqual(operation_journal.inspect_record(str(self.state), operation_id, home_dir=self.home)["status"], "complete")

    def test_unapplied_restore_is_reconciled_failed_from_pre_restore_snapshot(self) -> None:
        self.make_archive("target-native")
        self.source.write_bytes(profile("cli-only"))
        operation_id = operation_journal.begin(str(self.state), "recovery.restore.apply",
                                               "restore backup target-native", home_dir=self.home)
        self.make_snapshot(operation_id)
        plan = restore_recovery.preview(operation_id, home=self.home, state_dir=self.state)
        self.assertEqual(plan["resolution"], "failed")
        self.assertEqual(plan["observed_outcome"], "pre_restore_state")
        result = restore_recovery.resolve(operation_id, home=self.home, state_dir=self.state,
                                          confirmed=True, plan_id=str(plan["plan_id"]))
        self.assertEqual(result["resolution"], "failed")
        self.assertEqual(self.source.read_bytes(), profile("cli-only"))

    def test_ambiguous_or_corrupt_state_remains_unresolved(self) -> None:
        self.make_archive("target-native")
        self.source.write_bytes(profile("cli-only"))
        operation_id = operation_journal.begin(str(self.state), "recovery.restore.apply",
                                               "restore backup target-native", home_dir=self.home)
        with self.assertRaisesRegex(restore_recovery.RestoreRecoveryError, "ambiguous"):
            restore_recovery.preview(operation_id, home=self.home, state_dir=self.state)
        self.make_snapshot(operation_id)
        (self.backups / "target-native.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(restore_recovery.RestoreRecoveryError, "unavailable or unsafe"):
            restore_recovery.preview(operation_id, home=self.home, state_dir=self.state)
        self.assertEqual(operation_journal.inspect_record(str(self.state), operation_id, home_dir=self.home)["status"], "starting")

    def test_unsafe_profile_mode_is_not_reconciled(self) -> None:
        self.make_archive("target-native")
        self.source.chmod(0o644)
        operation_id = operation_journal.begin(str(self.state), "recovery.restore.apply",
                                               "restore backup target-native", home_dir=self.home)
        with self.assertRaisesRegex(restore_recovery.RestoreRecoveryError, "ownership or mode is unsafe"):
            restore_recovery.preview(operation_id, home=self.home, state_dir=self.state)
        self.assertEqual(operation_journal.inspect_record(str(self.state), operation_id, home_dir=self.home)["status"], "starting")

    def test_stale_preview_does_not_resolve_changed_restore_outcome(self) -> None:
        self.make_archive("target-cli", profile("cli-only"))
        self.source.write_bytes(profile("native"))
        operation_id = operation_journal.begin(str(self.state), "recovery.restore.apply",
                                               "restore backup target-cli", home_dir=self.home)
        self.make_snapshot(operation_id)
        self.source.write_bytes(profile("cli-only"))
        plan = restore_recovery.preview(operation_id, home=self.home, state_dir=self.state)
        self.assertEqual(plan["resolution"], "complete")

        self.source.write_bytes(profile("native"))
        with self.assertRaisesRegex(restore_recovery.RestoreRecoveryError, "changed"):
            restore_recovery.resolve(operation_id, home=self.home, state_dir=self.state,
                                     confirmed=True, plan_id=str(plan["plan_id"]))
        self.assertEqual(operation_journal.inspect_record(str(self.state), operation_id, home_dir=self.home)["status"], "starting")
        self.assertEqual(self.source.read_bytes(), profile("native"))

    def test_completed_rollback_reconciles_child_and_parent_journals(self) -> None:
        self.source.write_bytes(profile("cli-only"))
        self.make_archive("original-target", profile("native"))
        self.source.write_bytes(profile("cli-only"))
        parent = operation_journal.begin(str(self.state), "recovery.restore.apply",
                                         "restore backup original-target", home_dir=self.home)
        self.make_snapshot(parent)
        operation_journal.update(str(self.state), parent, "needs_recovery", "restore original-target needs review; rollback=none", home_dir=self.home)
        self.source.write_bytes(profile("native"))
        parent_snapshot_id = f"rollback-{parent}"
        child = operation_journal.begin(str(self.state), "recovery.restore.rollback",
                                        f"restore backup {parent_snapshot_id}", home_dir=self.home,
                                        parent_operation_id=parent)
        self.make_snapshot(child)
        self.source.write_bytes(profile("cli-only"))

        plan = operation_recovery.preview(child, prefix="/unused", home=self.home, state_dir=self.state)
        self.assertEqual(plan["resolution"], "complete")
        self.assertEqual(len(plan["affected_paths"]), 2)
        operation_recovery.resolve(child, prefix="/unused", home=self.home, state_dir=self.state,
                                   confirmed=True, plan_id=str(plan["plan_id"]))
        self.assertEqual(operation_journal.inspect_record(str(self.state), child, home_dir=self.home)["status"], "complete")
        self.assertEqual(operation_journal.inspect_record(str(self.state), parent, home_dir=self.home)["status"], "failed")
        self.assertEqual(self.source.read_bytes(), profile("cli-only"))


if __name__ == "__main__":
    unittest.main()
