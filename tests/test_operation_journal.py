"""Durable operation journal contract tests."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import operation_journal  # noqa: E402
import operation_recovery  # noqa: E402
import doctor_report  # noqa: E402


class OperationJournalTest(unittest.TestCase):
    def test_every_journal_kind_has_an_operation_specific_recovery_route(self):
        self.assertEqual(operation_journal.JOURNAL_KINDS, operation_recovery.SUPPORTED_KINDS)

    def test_atomic_private_lifecycle_and_unresolved_guard(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            state = home / ".local/share/ternuxx"
            with patch.object(Path, "home", return_value=home):
                operation_id = operation_journal.begin(str(state), "desktop.start", "display :8")
                record_path = state / "operations" / f"{operation_id}.json"
                self.assertEqual(record_path.stat().st_mode & 0o777, 0o600)
                self.assertEqual((record_path.parent.stat().st_mode & 0o777), 0o700)
                with self.assertRaisesRegex(RuntimeError, "earlier operation is unresolved"):
                    operation_journal.begin(str(state), "desktop.stop", "blocked")
                operation_journal.update(str(state), operation_id, "complete", "ready")
                operation_journal.begin(str(state), "desktop.stop", "clean")

    def test_boot_operations_start_with_directional_status(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            state = home / ".local/share/ternuxx"
            with patch.object(Path, "home", return_value=home):
                enable_id = operation_journal.begin(str(state), "boot.enable", "native profile")
                enable = json.loads((state / "operations" / f"{enable_id}.json").read_text())
                self.assertEqual(enable["status"], "starting")
                operation_journal.update(str(state), enable_id, "complete", "enabled")
                disable_id = operation_journal.begin(str(state), "boot.disable", "native profile")
                disable = json.loads((state / "operations" / f"{disable_id}.json").read_text())
                self.assertEqual(disable["status"], "stopping")

    def test_rollback_journal_requires_and_links_one_matching_unresolved_restore(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            state = home / ".state"
            with patch.object(Path, "home", return_value=home):
                parent = operation_journal.begin(str(state), "recovery.restore.apply", "restore target")
                operation_journal.update(str(state), parent, "needs_recovery", "restore interrupted")
                child = operation_journal.begin(str(state), "recovery.restore.rollback", "restore rollback",
                                                parent_operation_id=parent)
                linked = operation_journal.inspect_record(str(state), child)
                self.assertEqual(linked["parent_operation_id"], parent)
                with self.assertRaises(RuntimeError):
                    operation_journal.begin(str(state), "desktop.start", "blocked")
                operation_journal.update(str(state), child, "complete", "rollback applied")
                operation_journal.update(str(state), parent, "failed", "compensated")
                self.assertEqual(operation_journal.inspect_record(str(state), parent)["status"], "failed")

    def test_rollback_journal_allows_only_matching_nested_recovery_chain(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            state = home / ".state"
            with patch.object(Path, "home", return_value=home):
                parent = operation_journal.begin(str(state), "recovery.restore.apply", "restore")
                operation_journal.update(str(state), parent, "needs_recovery", "partial restore")
                child = operation_journal.begin(str(state), "recovery.restore.rollback", "rollback one",
                                                parent_operation_id=parent)
                operation_journal.update(str(state), child, "needs_recovery", "rollback interrupted")
                grandchild = operation_journal.begin(str(state), "recovery.restore.rollback", "rollback rollback",
                                                     parent_operation_id=child)
                record = operation_journal.inspect_record(str(state), grandchild)
                self.assertEqual(record["parent_operation_id"], child)
                operation_journal.update(str(state), grandchild, "complete", "recovered")
                operation_journal.update(str(state), child, "failed", "compensated")
                operation_journal.update(str(state), parent, "failed", "compensated")

    def test_rollback_journal_does_not_bypass_unrelated_pending_operation(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            state = home / ".state"
            with patch.object(Path, "home", return_value=home):
                parent = operation_journal.begin(str(state), "recovery.restore.apply", "restore")
                operation_journal.update(str(state), parent, "needs_recovery", "interrupted")
                record_path = state / "operations" / f"{parent}.json"
                unrelated = json.loads(record_path.read_text())
                unrelated["operation_id"] = "f" * 32
                unrelated["kind"] = "desktop.start"
                unrelated["status"] = "starting"
                unrelated_path = record_path.with_name(f"{'f' * 32}.json")
                unrelated_path.write_text(json.dumps(unrelated), encoding="utf-8")
                unrelated_path.chmod(0o600)
                with self.assertRaises(RuntimeError):
                    operation_journal.begin(str(state), "recovery.restore.rollback", "blocked rollback",
                                            parent_operation_id=parent)

    def test_rollback_journal_rejects_wrong_parent_and_parentless_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            state = home / ".state"
            with patch.object(Path, "home", return_value=home):
                parent = operation_journal.begin(str(state), "desktop.stop", "not a restore")
                operation_journal.update(str(state), parent, "failed", "finished")
                with self.assertRaises(RuntimeError):
                    operation_journal.begin(str(state), "recovery.restore.rollback", "bad parent",
                                            parent_operation_id=parent)
                with self.assertRaises(ValueError):
                    operation_journal.begin(str(state), "recovery.restore.rollback", "missing parent")

    def test_outside_home_and_invalid_updates_rejected(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as outside:
            with patch.object(Path, "home", return_value=Path(home)):
                with self.assertRaises(ValueError):
                    operation_journal.begin(outside, "desktop.start", "bad")
                state = Path(home) / "state"
                operation_id = operation_journal.begin(str(state), "desktop.start", "ok")
                with self.assertRaises(ValueError):
                    operation_journal.update(str(state), operation_id, "running", "bad")
                with self.assertRaises(ValueError):
                    operation_journal.update(str(state), "../" + operation_id, "failed", "bad")

    def test_doctor_does_not_read_journal_outside_home(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as outside:
            with patch.object(Path, "home", return_value=Path(home)):
                doctor_report.FINDINGS.clear()
                doctor_report.check_operations(Path(outside))
            self.assertEqual(doctor_report.FINDINGS[0]["id"], "NTX-OP-004")
            self.assertEqual(doctor_report.FINDINGS[0]["severity"], "error")
            self.assertEqual(list(Path(outside).iterdir()), [])

    def test_readonly_list_and_inspect_redact_process_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            state = home / ".state"
            with patch.object(Path, "home", return_value=home):
                operation_id = operation_journal.begin(str(state), "recovery.backup.create", "create sample")
                operation_journal.update(str(state), operation_id, "complete", "saved")
                listed = operation_journal.list_records(str(state))
                inspected = operation_journal.inspect_record(str(state), operation_id)
            self.assertEqual(listed[0]["kind"], "recovery.backup.create")
            self.assertEqual(inspected["status"], "complete")
            self.assertNotIn("initiating_pid", inspected)

    def test_readonly_list_does_not_create_missing_journal(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            state = home / ".state"
            with patch.object(Path, "home", return_value=home):
                self.assertEqual(operation_journal.list_records(str(state)), [])
            self.assertFalse(state.exists())

    def test_doctor_reports_unresolved_without_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            state = home / ".local/share/ternuxx"
            with patch.object(Path, "home", return_value=home):
                operation_journal.begin(str(state), "desktop.stop", "state running")
                doctor_report.FINDINGS.clear()
                doctor_report.check_operations(state)
            finding = next(f for f in doctor_report.FINDINGS if f["id"] == "NTX-OP-003")
            self.assertEqual(finding["severity"], "warning")
            self.assertIn("status=stopping", finding["observed"])
            self.assertEqual(len(list((state / "operations").glob("*.json"))), 1)


if __name__ == "__main__":
    unittest.main()
