"""Durable mutation idempotency and secret-free audit contract tests."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import management_request_store  # noqa: E402


SESSION = "session-reference-0001"
KEY = "idempotency-key-0001"
FINGERPRINT = hashlib.sha256(b"exact operation request").hexdigest()
REQUEST_ID = "request-00000001"
OPERATION = "ssh.service.start"


class ManagementRequestStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-request-store-")
        self.home = Path(self.temp.name) / "home"
        self.home.mkdir(mode=0o700)
        self.state_dir = self.home / ".local" / "share" / "ternuxx"
        self.state_dir.mkdir(parents=True, mode=0o700)
        os.chmod(self.home / ".local", 0o700)
        os.chmod(self.home / ".local" / "share", 0o700)
        self.store = self.create_store()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def create_store(self):
        return management_request_store.ManagementRequestStore(
            home=self.home, state_dir=self.state_dir)

    def begin(self, store=None, *, fingerprint=FINGERPRINT):
        return (store or self.store).begin(
            session_ref=SESSION, idempotency_key=KEY, fingerprint=fingerprint,
            request_id=REQUEST_ID, operation=OPERATION)

    def test_durable_begin_rejects_conflict_and_survives_new_store_instance(self) -> None:
        self.assertIs(self.store.durable, True)
        self.assertEqual(self.begin(), "new")
        self.assertEqual(self.begin(fingerprint="f" * 64), "conflict")
        reopened = self.create_store()
        self.assertEqual(self.begin(reopened), "in_progress")
        record_files = list((self.store.records).glob("*.json"))
        self.assertEqual(len(record_files), 1)
        self.assertNotIn(KEY, record_files[0].name)
        self.assertNotIn(KEY, record_files[0].read_text())
        self.assertEqual(record_files[0].stat().st_mode & 0o777, 0o600)

    def test_completed_duplicate_never_replays_response_or_mutation(self) -> None:
        self.assertEqual(self.begin(), "new")
        self.store.complete(session_ref=SESSION, idempotency_key=KEY,
                            fingerprint=FINGERPRINT, http_status=200,
                            outcome="succeeded", duration_ms=23)
        self.assertEqual(self.begin(self.create_store()), "completed")

    def test_audit_has_only_allowlisted_metadata_and_both_phases(self) -> None:
        secret = "bearer-secret-value-that-must-not-be-recorded"
        self.assertEqual(self.begin(), "new")
        self.store.complete(session_ref=SESSION, idempotency_key=KEY,
                            fingerprint=FINGERPRINT, http_status=200,
                            outcome="succeeded", duration_ms=23)
        raw = self.store.audit_path.read_text()
        self.assertNotIn(KEY, raw)
        self.assertNotIn(secret, raw)
        events = [json.loads(line) for line in raw.splitlines()]
        self.assertEqual([event["event"] for event in events], ["started", "succeeded"])
        allowed = {"schema_version", "event_id", "occurred_at_utc", "session_ref",
                   "request_id", "operation", "capability", "event", "http_status", "duration_ms"}
        self.assertEqual(set(events[0]), allowed)
        self.assertEqual(set(events[1]), allowed)
        self.assertEqual(self.store.audit_path.stat().st_mode & 0o777, 0o600)

    def test_corrupt_or_insecure_record_fails_closed(self) -> None:
        self.assertEqual(self.begin(), "new")
        record = next(self.store.records.glob("*.json"))
        os.chmod(record, 0o644)
        with self.assertRaises(RuntimeError):
            self.begin(self.create_store())

    def test_nonfinite_or_unreasonable_timestamp_fails_closed(self) -> None:
        self.assertEqual(self.begin(), "new")
        record_path = next(self.store.records.glob("*.json"))
        raw = record_path.read_text()
        record_path.write_text(raw.replace('"created_at_epoch":', '"created_at_epoch":NaN,"unused":'))
        with self.assertRaises(RuntimeError):
            self.begin(self.create_store())
        record = json.loads(raw)
        record["created_at_epoch"] = 1_000_000_000_001
        record_path.write_text(json.dumps(record))
        with self.assertRaises(RuntimeError):
            self.begin(self.create_store())

    def test_symlinked_record_and_state_paths_are_rejected(self) -> None:
        self.assertEqual(self.begin(), "new")
        record = next(self.store.records.glob("*.json"))
        outside = Path(self.temp.name) / "outside.json"
        outside.write_text(record.read_text())
        record.unlink()
        record.symlink_to(outside)
        with self.assertRaises(RuntimeError):
            self.begin(self.create_store())

        other = Path(self.temp.name) / "other"
        other.mkdir(mode=0o700)
        link = self.home / "linked-state"
        link.symlink_to(other, target_is_directory=True)
        with self.assertRaises(ValueError):
            management_request_store.ManagementRequestStore(home=self.home, state_dir=link)

    def test_outside_home_and_nonprivate_state_are_rejected(self) -> None:
        outside = Path(self.temp.name) / "outside"
        outside.mkdir(mode=0o700)
        with self.assertRaises(ValueError):
            management_request_store.ManagementRequestStore(home=self.home, state_dir=outside)
        os.chmod(self.state_dir, 0o755)
        with self.assertRaises(ValueError):
            self.create_store()


if __name__ == "__main__":
    unittest.main()
