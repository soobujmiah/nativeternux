from __future__ import annotations

import base64
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import ssh_key_inventory
import ssh_key_manager


class SshKeyManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.home.mkdir(mode=0o700)
        os.chown(self.home, os.getuid(), -1)
        self.ssh = self.home / ".ssh"
        self.ssh.mkdir(mode=0o700)
        os.chown(self.ssh, os.getuid(), -1)
        self.keys = self.ssh / "authorized_keys"
        self.uid = os.getuid()
        self.key_store = Path(self.tmp.name) / "test-credentials"
        self.key_store.mkdir(mode=0o700)
        self.first = self._generate("key-one", "first-test-key")
        self.second = self._generate("key-two", "second-test-key")
        self.fp1 = ssh_key_inventory._parse_line(self.first)["fingerprint"]
        self.fp2 = ssh_key_inventory._parse_line(self.second)["fingerprint"]

    def _generate(self, name: str, comment: str) -> str:
        path = self.key_store / name
        result = subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "",
                                 "-C", comment, "-f", str(path)],
                                capture_output=True, text=True, timeout=10, check=False)
        if result.returncode:
            self.fail("temporary test key generation failed")
        return path.with_suffix(".pub").read_text(encoding="utf-8").strip()

    def tearDown(self):
        self.tmp.cleanup()

    def test_preview_add_contains_no_key_bytes_and_discloses_shared_service_impact(self):
        plan = ssh_key_manager.preview("add", home=self.home, uid=self.uid,
                                       fingerprint=self.fp1, public_key=self.first)
        self.assertEqual(plan["status"], "ready")
        self.assertEqual(plan["affects_services"],
                         ["owner-managed SSH 8022", "Ternuxx managed SSH 8023"])
        self.assertNotIn(self.first, repr(plan))
        self.assertNotIn("fixture-key-one", repr(plan))

    def test_confirmed_add_is_atomic_mode_0600_and_idempotent(self):
        plan = ssh_key_manager.preview("add", home=self.home, uid=self.uid,
                                       fingerprint=self.fp1, public_key=self.first)
        result = ssh_key_manager.apply("add", home=self.home, uid=self.uid,
            fingerprint=self.fp1, public_key=self.first, confirmed=True, plan_id=plan["plan_id"])
        self.assertEqual(result["status"], "complete")
        self.assertEqual(self.keys.read_text(), self.first + "\n")
        self.assertEqual(self.keys.stat().st_mode & 0o777, 0o600)
        again = ssh_key_manager.preview("add", home=self.home, uid=self.uid,
                                        fingerprint=self.fp1, public_key=self.first)
        self.assertFalse(again["changed"])

    def test_stale_plan_does_not_overwrite_concurrent_key_changes(self):
        plan = ssh_key_manager.preview("add", home=self.home, uid=self.uid,
                                       fingerprint=self.fp1, public_key=self.first)
        self.keys.write_text(self.second + "\n")
        self.keys.chmod(0o600)
        result = ssh_key_manager.apply("add", home=self.home, uid=self.uid,
            fingerprint=self.fp1, public_key=self.first, confirmed=True, plan_id=plan["plan_id"])
        self.assertEqual(result["status"], "stale_plan")
        self.assertEqual(self.keys.read_text(), self.second + "\n")

    def test_remove_exact_fingerprint_preserves_other_records_and_invalid_lines(self):
        self.keys.write_text("# owner comment\n" + self.first + "\nnot-a-key\n" + self.second + "\n")
        self.keys.chmod(0o600)
        plan = ssh_key_manager.preview("remove", home=self.home, uid=self.uid, fingerprint=self.fp1)
        result = ssh_key_manager.apply("remove", home=self.home, uid=self.uid,
            fingerprint=self.fp1, confirmed=True, plan_id=plan["plan_id"])
        self.assertEqual(result["status"], "complete")
        updated = self.keys.read_text()
        self.assertNotIn(self.fp1, updated)
        self.assertIn("# owner comment", updated)
        self.assertIn("not-a-key", updated)
        self.assertIn(self.second, updated)
        self.assertEqual(self.keys.stat().st_mode & 0o777, 0o600)

    def test_malformed_fingerprint_is_rejected(self):
        with self.assertRaisesRegex(ssh_key_manager.SshKeyMutationError, "fingerprint"):
            ssh_key_manager.preview("remove", home=self.home, uid=self.uid,
                                    fingerprint="SHA256:abc")

    def test_last_authorized_key_cannot_be_removed_before_replacement_is_enrolled(self):
        self.keys.write_text(self.first + "\n")
        self.keys.chmod(0o600)
        with self.assertRaisesRegex(ssh_key_manager.SshKeyMutationError, "last authorized key"):
            ssh_key_manager.preview("remove", home=self.home, uid=self.uid, fingerprint=self.fp1)

    def test_public_key_control_characters_are_rejected(self):
        malformed = self.first + "\x00injected"
        with self.assertRaises(ssh_key_manager.SshKeyMutationError):
            ssh_key_manager.preview("add", home=self.home, uid=self.uid,
                                    fingerprint=self.fp1, public_key=malformed)

    def test_remove_duplicate_records_removes_all_exact_matches(self):
        self.keys.write_text(self.first + "\n" + self.first + "\n" + self.second + "\n")
        self.keys.chmod(0o600)
        plan = ssh_key_manager.preview("remove", home=self.home, uid=self.uid, fingerprint=self.fp1)
        self.assertEqual(plan["matching_entries"], 2)
        result = ssh_key_manager.apply("remove", home=self.home, uid=self.uid,
            fingerprint=self.fp1, confirmed=True, plan_id=plan["plan_id"])
        self.assertEqual(result["status"], "complete")
        self.assertEqual(self.keys.read_text(), self.second + "\n")

    def test_malformed_key_blob_is_rejected_even_when_type_and_fingerprint_parse(self):
        blob = struct.pack(">I", len("ssh-ed25519")) + b"ssh-ed25519" + b"bad"
        bad_key = "ssh-ed25519 " + base64.b64encode(blob).decode() + " broken"
        fp = ssh_key_inventory._parse_line(bad_key)["fingerprint"]
        with self.assertRaises(ssh_key_manager.SshKeyMutationError):
            ssh_key_manager.preview("add", home=self.home, uid=self.uid,
                                    fingerprint=fp, public_key=bad_key)

    def test_mismatched_fingerprint_and_policy_options_are_rejected(self):
        with self.assertRaises(ssh_key_manager.SshKeyMutationError):
            ssh_key_manager.preview("add", home=self.home, uid=self.uid,
                                    fingerprint=self.fp2, public_key=self.first)
        with self.assertRaises(ssh_key_manager.SshKeyMutationError):
            ssh_key_manager.preview("add", home=self.home, uid=self.uid,
                fingerprint=self.fp1, public_key="restrict,command=\"id\" " + self.first)

    def test_symlink_target_and_unsafe_directory_are_rejected(self):
        outside = Path(self.tmp.name) / "outside"
        outside.write_text(self.first + "\n")
        self.keys.symlink_to(outside)
        with self.assertRaises(ssh_key_manager.SshKeyMutationError):
            ssh_key_manager.preview("remove", home=self.home, uid=self.uid, fingerprint=self.fp1)
        self.keys.unlink()
        self.ssh.chmod(0o755)
        with self.assertRaises(ssh_key_manager.SshKeyMutationError):
            ssh_key_manager.preview("add", home=self.home, uid=self.uid,
                                    fingerprint=self.fp1, public_key=self.first)


if __name__ == "__main__":
    unittest.main()
