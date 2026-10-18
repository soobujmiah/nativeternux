"""Fixture tests for read-only inspection and explicit journal-only boot recovery."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import boot_profile_recovery  # noqa: E402
import boot_profiles  # noqa: E402
import operation_journal  # noqa: E402
import operation_recovery  # noqa: E402


class BootProfileRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-boot-recovery-")
        self.home = Path(self.temp.name) / "home"
        self.home.mkdir()
        self.state = self.home / ".local/share/ternuxx"
        self.script = self.home / ".termux/boot/10-ternuxx-profile"
        self.profile = self.state / "boot/profile.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def pending(self, kind: str, profile: str = "native", status: str = "needs_recovery") -> str:
        detail = f"profile {profile}" if kind == "boot.enable" else "disable managed boot profile"
        operation_id = operation_journal.begin(str(self.state), kind, detail, home_dir=self.home)
        if status == "needs_recovery":
            operation_journal.update(str(self.state), operation_id, status, detail, home_dir=self.home)
        return operation_id

    def write_profile(self, profile: str = "native") -> None:
        self.profile.parent.mkdir(parents=True, exist_ok=True)
        self.profile.write_text(json.dumps({"schema_version": 1, "owner": "ternuxx", "provider": "native",
                                            "profile": profile}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        self.profile.chmod(0o600)

    def write_script(self, profile: str = "native") -> None:
        self.script.parent.mkdir(parents=True, exist_ok=True)
        self.script.write_bytes(boot_profiles._managed_script(profile))
        self.script.chmod(0o700)

    def test_enable_recovery_marks_complete_only_for_exact_profile_and_script(self) -> None:
        operation_id = self.pending("boot.enable", "native", status="starting")
        self.write_profile("native")
        self.write_script("native")
        preview = operation_recovery.preview(operation_id, prefix=self.home, home=self.home, state_dir=self.state)
        schema = json.loads((ROOT / "schemas/boot-profile-recovery.schema.json").read_text())
        preview_schema, applied_schema = schema["oneOf"]
        self.assertEqual(set(preview), set(preview_schema["required"]))
        expected_journal = str(self.state.resolve() / "operations" / f"{operation_id}.json")
        self.assertEqual(preview["affected_paths"], [expected_journal])
        self.assertEqual(preview["resolution"], "complete")
        result = operation_recovery.resolve(operation_id, prefix=self.home, home=self.home, state_dir=self.state,
                                            confirmed=True, plan_id=str(preview["plan_id"]))
        self.assertEqual(set(result), set(applied_schema["required"]))
        self.assertEqual(result["affected_paths"], [expected_journal])
        self.assertFalse(result["boot_files_changed"])
        self.assertEqual(operation_journal.inspect_record(str(self.state), operation_id, home_dir=self.home)["status"], "complete")

    def test_partial_enable_and_incomplete_disable_are_resolved_as_failed(self) -> None:
        enable_id = self.pending("boot.enable", "native")
        self.write_profile("native")
        preview = boot_profile_recovery.preview(enable_id, home=self.home, state_dir=self.state)
        self.assertEqual(preview["resolution"], "failed")
        boot_profile_recovery.resolve(enable_id, home=self.home, state_dir=self.state,
                                      confirmed=True, plan_id=str(preview["plan_id"]))
        self.assertEqual(operation_journal.inspect_record(str(self.state), enable_id, home_dir=self.home)["status"], "failed")

        disable_id = self.pending("boot.disable")
        self.write_profile("cli-only")
        self.write_script("cli-only")
        preview = boot_profile_recovery.preview(disable_id, home=self.home, state_dir=self.state)
        self.assertEqual(preview["resolution"], "failed")
        boot_profile_recovery.resolve(disable_id, home=self.home, state_dir=self.state,
                                      confirmed=True, plan_id=str(preview["plan_id"]))
        self.assertEqual(operation_journal.inspect_record(str(self.state), disable_id, home_dir=self.home)["status"], "failed")

    def test_disable_complete_when_both_owned_files_are_absent(self) -> None:
        operation_id = self.pending("boot.disable")
        preview = boot_profile_recovery.resolve(operation_id, home=self.home, state_dir=self.state,
                                                confirmed=False, plan_id=None)
        self.assertEqual(preview["resolution"], "complete")
        boot_profile_recovery.resolve(operation_id, home=self.home, state_dir=self.state,
                                      confirmed=True, plan_id=str(preview["plan_id"]))
        self.assertFalse(self.script.exists())
        self.assertFalse(self.profile.exists())
        self.assertEqual(operation_journal.inspect_record(str(self.state), operation_id, home_dir=self.home)["status"], "complete")

    def test_crash_left_disable_operation_can_be_reconciled_from_stopping(self) -> None:
        operation_id = self.pending("boot.disable", status="stopping")
        preview = boot_profile_recovery.preview(operation_id, home=self.home, state_dir=self.state)
        self.assertEqual(preview["resolution"], "complete")
        boot_profile_recovery.resolve(operation_id, home=self.home, state_dir=self.state,
                                      confirmed=True, plan_id=str(preview["plan_id"]))
        self.assertEqual(operation_journal.inspect_record(str(self.state), operation_id, home_dir=self.home)["status"], "complete")

    def test_stale_preview_and_unrecognized_script_fail_closed(self) -> None:
        operation_id = self.pending("boot.enable", "native")
        self.write_profile("native")
        self.write_script("native")
        preview = boot_profile_recovery.preview(operation_id, home=self.home, state_dir=self.state)
        self.script.write_text("#!/bin/sh\necho user\n", encoding="utf-8")
        self.script.chmod(0o700)
        with self.assertRaisesRegex(boot_profile_recovery.BootProfileRecoveryError, "not a recognized"):
            boot_profile_recovery.resolve(operation_id, home=self.home, state_dir=self.state,
                                          confirmed=True, plan_id=str(preview["plan_id"]))
        self.assertEqual(operation_journal.inspect_record(str(self.state), operation_id, home_dir=self.home)["status"], "needs_recovery")

    def test_symlink_and_unsafe_file_mode_are_rejected_without_changes(self) -> None:
        operation_id = self.pending("boot.enable", "native")
        self.write_profile("native")
        self.write_script("native")
        self.script.chmod(0o777)
        with self.assertRaisesRegex(boot_profile_recovery.BootProfileRecoveryError, "unsafe or invalid"):
            boot_profile_recovery.preview(operation_id, home=self.home, state_dir=self.state)
        self.assertEqual(operation_journal.inspect_record(str(self.state), operation_id, home_dir=self.home)["status"], "needs_recovery")


if __name__ == "__main__":
    unittest.main()
