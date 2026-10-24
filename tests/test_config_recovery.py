"""Fixture tests for strict Ternuxx-only configuration recovery."""
from __future__ import annotations

import base64
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import config_recovery  # noqa: E402


def profile(mode: str) -> bytes:
    return json.dumps({"schema_version": 1, "owner": "ternuxx", "provider": "native", "profile": mode}).encode() + b"\n"


class ConfigRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-recovery-")
        self.home = Path(self.temp.name)
        self.state = self.home / ".local/share/ternuxx"
        self.source = self.state / "boot/profile.json"
        self.source.parent.mkdir(parents=True)
        self.source.write_bytes(profile("native"))
        self.source.chmod(0o600)
        self.patch_home = patch.object(Path, "home", return_value=self.home)
        self.patch_home.start()
        self.addCleanup(self.patch_home.stop)
        self.addCleanup(self.temp.cleanup)

    def test_backup_preview_is_readonly_then_create_list_inspect(self):
        preview = config_recovery.create_backup(home=str(self.home), state_dir=str(self.state), name="before-restore")
        self.assertEqual(preview["action"], "preview")
        self.assertFalse((self.state / "backups").exists())
        created = config_recovery.create_backup(home=str(self.home), state_dir=str(self.state), name="before-restore",
                                                confirmed=True, plan_id=preview["plan_id"])
        archive = self.state / "backups/before-restore.json"
        self.assertEqual(archive.stat().st_mode & 0o777, 0o600)
        self.assertEqual(archive.parent.stat().st_mode & 0o777, 0o700)
        self.assertEqual(created["integrity"], "valid")
        self.assertEqual(config_recovery.list_backups(home=str(self.home), state_dir=str(self.state))["backups"][0]["integrity"], "valid")
        inspected = config_recovery.inspect_backup(home=str(self.home), state_dir=str(self.state), backup_id="before-restore")
        self.assertEqual(inspected["entries"][0]["path"], config_recovery.PROFILE_PATH)
        self.assertIn("shared/external storage", inspected["excluded_paths"])
        self.assertIn("SSH host/client private keys and credentials", inspected["excluded_paths"])
        self.assertTrue(created["operation_id"].isalnum())
        operation = json.loads(next((self.state / "operations").glob("*.json")).read_text())
        self.assertEqual(operation["kind"], "recovery.backup.create")
        self.assertEqual(operation["status"], "complete")

    def test_restore_preview_then_restore_creates_verified_rollback_snapshot(self):
        preview = config_recovery.create_backup(home=str(self.home), state_dir=str(self.state), name="native-snapshot")
        config_recovery.create_backup(home=str(self.home), state_dir=str(self.state), name="native-snapshot",
                                      confirmed=True, plan_id=preview["plan_id"])
        original = self.source.read_bytes()
        self.source.write_bytes(profile("cli-only"))
        restore_preview = config_recovery.restore_preview(home=str(self.home), state_dir=str(self.state), backup_id="native-snapshot")
        self.assertEqual(restore_preview["entries"][0]["action"], "replace")
        result = config_recovery.restore_backup(home=str(self.home), state_dir=str(self.state), backup_id="native-snapshot",
                                                confirmed=True, plan_id=restore_preview["plan_id"])
        self.assertEqual(self.source.read_bytes(), original)
        operation_records = [json.loads(item.read_text()) for item in (self.state / "operations").glob("*.json")]
        self.assertTrue(any(item["kind"] == "recovery.restore.apply" and item["status"] == "complete" for item in operation_records))
        self.assertEqual(self.source.stat().st_mode & 0o777, 0o600)
        rollback = config_recovery.inspect_backup(home=str(self.home), state_dir=str(self.state),
                                                 backup_id=result["rollback_backup_id"])
        self.assertEqual(rollback["integrity"], "valid")
        rollback_payload = json.loads((self.state / "backups" / f"{result['rollback_backup_id']}.json").read_text())
        self.assertEqual(base64.b64decode(rollback_payload["entries"][0]["data_b64"]), profile("cli-only"))

    def test_explicit_rollback_restores_pre_restore_state(self):
        preview = config_recovery.create_backup(home=str(self.home), state_dir=str(self.state), name="native-before")
        config_recovery.create_backup(home=str(self.home), state_dir=str(self.state), name="native-before",
                                      confirmed=True, plan_id=preview["plan_id"])
        self.source.write_bytes(profile("cli-only"))
        restore = config_recovery.restore_preview(home=str(self.home), state_dir=str(self.state), backup_id="native-before")
        applied = config_recovery.restore_backup(home=str(self.home), state_dir=str(self.state), backup_id="native-before",
                                                 confirmed=True, plan_id=restore["plan_id"])
        parent_id = applied["operation_id"]
        self.assertEqual(self.source.read_bytes(), profile("native"))
        rollback = config_recovery.rollback_preview(home=str(self.home), state_dir=str(self.state), operation_id=parent_id)
        self.assertEqual(rollback["action"], "rollback_preview")
        self.assertEqual(rollback["entries"][0]["action"], "replace")
        preview_only = config_recovery.rollback_restore(home=str(self.home), state_dir=str(self.state),
                                                        operation_id=parent_id)
        self.assertEqual(preview_only["plan_id"], rollback["plan_id"])
        self.assertEqual(self.source.read_bytes(), profile("native"))
        result = config_recovery.rollback_restore(home=str(self.home), state_dir=str(self.state),
                                                  operation_id=parent_id, confirmed=True, plan_id=rollback["plan_id"])
        self.assertEqual(result["action"], "rolled_back")
        self.assertEqual(self.source.read_bytes(), profile("cli-only"))
        records = config_recovery.operation_journal.list_records(str(self.state), home_dir=self.home)
        rollback_record = next(row for row in records if row["operation_id"] == result["operation_id"])
        self.assertEqual(rollback_record["kind"], "recovery.restore.rollback")
        self.assertEqual(rollback_record["parent_operation_id"], parent_id)
        self.assertEqual(rollback_record["status"], "complete")
        reverse_preview = config_recovery.rollback_preview(home=str(self.home), state_dir=str(self.state),
                                                           operation_id=result["operation_id"])
        reverse = config_recovery.rollback_restore(home=str(self.home), state_dir=str(self.state),
                                                   operation_id=result["operation_id"], confirmed=True,
                                                   plan_id=reverse_preview["plan_id"])
        self.assertEqual(reverse["action"], "rolled_back")
        self.assertEqual(self.source.read_bytes(), profile("native"))

    def test_rollback_preview_missing_operation_fails_read_only(self):
        with self.assertRaisesRegex(config_recovery.RecoveryError, "operation record was not found"):
            config_recovery.rollback_preview(home=str(self.home), state_dir=str(self.state),
                                             operation_id="0" * 32)
        self.assertFalse((self.state / "operations").exists())

    def test_rollback_of_restore_to_absent_profile_removes_added_file(self):
        preview = config_recovery.create_backup(home=str(self.home), state_dir=str(self.state), name="before-absent")
        config_recovery.create_backup(home=str(self.home), state_dir=str(self.state), name="before-absent",
                                      confirmed=True, plan_id=preview["plan_id"])
        self.source.unlink()
        restore = config_recovery.restore_preview(home=str(self.home), state_dir=str(self.state), backup_id="before-absent")
        result = config_recovery.restore_backup(home=str(self.home), state_dir=str(self.state), backup_id="before-absent",
                                                confirmed=True, plan_id=restore["plan_id"])
        self.assertEqual(self.source.read_bytes(), profile("native"))
        rollback_archive = json.loads((self.state / "backups" / f"{result['rollback_backup_id']}.json").read_text())
        self.assertFalse(rollback_archive["entries"][0]["present"])
        rollback = config_recovery.rollback_preview(home=str(self.home), state_dir=str(self.state),
                                                     operation_id=result["operation_id"])
        self.assertEqual(rollback["entries"][0]["action"], "remove")
        config_recovery.rollback_restore(home=str(self.home), state_dir=str(self.state),
                                         operation_id=result["operation_id"], confirmed=True,
                                         plan_id=rollback["plan_id"])
        self.assertFalse(self.source.exists())

    def test_explicit_rollback_resolves_needs_recovery_restore(self):
        preview = config_recovery.create_backup(home=str(self.home), state_dir=str(self.state), name="recovery-target")
        config_recovery.create_backup(home=str(self.home), state_dir=str(self.state), name="recovery-target",
                                      confirmed=True, plan_id=preview["plan_id"])
        self.source.write_bytes(profile("cli-only"))
        restore = config_recovery.restore_preview(home=str(self.home), state_dir=str(self.state), backup_id="recovery-target")
        original_write = config_recovery._write_atomic
        def write_then_fail(path, data, *, mode=0o600):
            original_write(path, data, mode=mode)
            if path == self.source:
                raise OSError("injected post-replace interruption")
        with patch.object(config_recovery, "_write_atomic", side_effect=write_then_fail):
            with self.assertRaises(OSError):
                config_recovery.restore_backup(home=str(self.home), state_dir=str(self.state),
                                               backup_id="recovery-target", confirmed=True,
                                               plan_id=restore["plan_id"])
        parent = next(row for row in config_recovery.operation_journal.list_records(str(self.state), home_dir=self.home)
                      if row["kind"] == "recovery.restore.apply")
        self.assertEqual(parent["status"], "needs_recovery")
        self.assertEqual(self.source.read_bytes(), profile("native"))
        preview = config_recovery.rollback_preview(home=str(self.home), state_dir=str(self.state),
                                                   operation_id=str(parent["operation_id"]))
        result = config_recovery.rollback_restore(home=str(self.home), state_dir=str(self.state),
                                                  operation_id=str(parent["operation_id"]), confirmed=True,
                                                  plan_id=preview["plan_id"])
        self.assertEqual(self.source.read_bytes(), profile("cli-only"))
        records = config_recovery.operation_journal.list_records(str(self.state), home_dir=self.home)
        resolved_parent = next(row for row in records if row["operation_id"] == parent["operation_id"])
        self.assertEqual(resolved_parent["status"], "failed")
        self.assertEqual(sum(row["status"] in config_recovery.operation_journal.ACTIVE for row in records), 0)

    def test_absent_profile_is_snapshotted_and_restore_removes_only_that_file(self):
        self.source.unlink()
        preview = config_recovery.create_backup(home=str(self.home), state_dir=str(self.state), name="default-profile")
        self.assertEqual(preview["entries"][0]["present"], False)
        config_recovery.create_backup(home=str(self.home), state_dir=str(self.state), name="default-profile",
                                      confirmed=True, plan_id=preview["plan_id"])
        self.source.write_bytes(profile("native"))
        restore = config_recovery.restore_preview(home=str(self.home), state_dir=str(self.state), backup_id="default-profile")
        self.assertEqual(restore["entries"][0]["action"], "remove")
        result = config_recovery.restore_backup(home=str(self.home), state_dir=str(self.state), backup_id="default-profile",
                                                confirmed=True, plan_id=restore["plan_id"])
        self.assertFalse(self.source.exists())
        rollback = config_recovery.inspect_backup(home=str(self.home), state_dir=str(self.state),
                                                 backup_id=result["rollback_backup_id"])
        self.assertTrue(rollback["entries"][0]["present"])
        self.assertEqual(base64.b64decode(json.loads((self.state / "backups" / f"{result['rollback_backup_id']}.json").read_text())["entries"][0]["data_b64"]), profile("native"))

    def test_restore_refuses_changed_target_and_missing_confirmation(self):
        preview = config_recovery.create_backup(home=str(self.home), state_dir=str(self.state), name="saved")
        config_recovery.create_backup(home=str(self.home), state_dir=str(self.state), name="saved", confirmed=True,
                                      plan_id=preview["plan_id"])
        restore = config_recovery.restore_preview(home=str(self.home), state_dir=str(self.state), backup_id="saved")
        self.assertEqual(config_recovery.restore_backup(home=str(self.home), state_dir=str(self.state), backup_id="saved")["action"], "restore_preview")
        self.source.write_bytes(profile("cli-only"))
        with self.assertRaisesRegex(config_recovery.RecoveryError, "changed"):
            config_recovery.restore_backup(home=str(self.home), state_dir=str(self.state), backup_id="saved",
                                           confirmed=True, plan_id=restore["plan_id"])
        self.assertEqual(self.source.read_bytes(), profile("cli-only"))

    def test_corrupt_checksum_unknown_schema_and_path_traversal_fail_closed(self):
        preview = config_recovery.create_backup(home=str(self.home), state_dir=str(self.state), name="checks")
        config_recovery.create_backup(home=str(self.home), state_dir=str(self.state), name="checks", confirmed=True,
                                      plan_id=preview["plan_id"])
        archive = self.state / "backups/checks.json"
        original = json.loads(archive.read_text())
        bad = dict(original)
        bad["entries"] = [dict(original["entries"][0], data_b64=base64.b64encode(profile("cli-only")).decode())]
        archive.write_text(json.dumps(bad)); archive.chmod(0o600)
        with self.assertRaisesRegex(config_recovery.RecoveryError, "integrity"):
            config_recovery.inspect_backup(home=str(self.home), state_dir=str(self.state), backup_id="checks")
        bad = dict(original); bad["schema_version"] = 99
        archive.write_text(json.dumps(bad)); archive.chmod(0o600)
        with self.assertRaisesRegex(config_recovery.RecoveryError, "schema"):
            config_recovery.inspect_backup(home=str(self.home), state_dir=str(self.state), backup_id="checks")
        bad = dict(original); bad.pop("integrity_sha256")
        bad["entries"] = [dict(original["entries"][0], path="../../.ssh/authorized_keys")]
        bad["integrity_sha256"] = config_recovery._hash(config_recovery._canonical(bad))
        archive.write_text(json.dumps(bad)); archive.chmod(0o600)
        with self.assertRaisesRegex(config_recovery.RecoveryError, "unowned"):
            config_recovery.inspect_backup(home=str(self.home), state_dir=str(self.state), backup_id="checks")

    def test_symlinked_boot_parent_cannot_escape_state_root(self):
        external = self.home.parent / f"external-boot-{self.home.name}"
        external.mkdir()
        (external / "profile.json").write_bytes(profile("native"))
        boot = self.state / "boot"
        boot.rename(self.state / "boot-original")
        boot.symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(config_recovery.RecoveryError, "symbolic link"):
            config_recovery.create_backup(home=str(self.home), state_dir=str(self.state), name="escape")

    def test_invalid_profile_symlink_and_outside_state_are_rejected(self):
        preview = config_recovery.create_backup(home=str(self.home), state_dir=str(self.state), name="valid")
        config_recovery.create_backup(home=str(self.home), state_dir=str(self.state), name="valid", confirmed=True,
                                      plan_id=preview["plan_id"])
        self.source.write_text('{bad json')
        with self.assertRaisesRegex(config_recovery.RecoveryError, "valid JSON"):
            config_recovery.restore_preview(home=str(self.home), state_dir=str(self.state), backup_id="valid")
        self.source.unlink()
        external = self.home.parent / "outside-state"
        with self.assertRaisesRegex(config_recovery.RecoveryError, "inside HOME"):
            config_recovery.list_backups(home=str(self.home), state_dir=str(external))
        self.source.symlink_to(external)
        with self.assertRaisesRegex(config_recovery.RecoveryError, "symbolic link"):
            config_recovery.create_backup(home=str(self.home), state_dir=str(self.state), name="link")


if __name__ == "__main__":
    unittest.main()
