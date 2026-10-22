from __future__ import annotations

import base64
import contextlib
import io
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import management_authorization
import management_http_runtime
import management_service
import management_sessions
import terminal_ui


def ed25519_public() -> str:
    kind = "ssh-ed25519"
    key = b"x" * 32
    blob = struct.pack(">I", len(kind)) + kind.encode() + struct.pack(">I", len(key)) + key
    return f"{kind} {base64.b64encode(blob).decode()} test-key"


class SshKeyClientContractTests(unittest.TestCase):
    def test_cli_reads_public_key_from_stdin_and_derives_fingerprint_on_server(self):
        key = ed25519_public()
        response = {"ok": True, "operation": "ssh.keys.add.preview",
                    "data": {"fingerprint": "SHA256:redacted", "changed": True}}
        output = io.StringIO()
        with patch.dict(os.environ, {"TERMUX_VERSION": "test",
                "PREFIX": "/data/data/com.termux/files/usr",
                "HOME": "/tmp/fixture-home",
                "TERNUXX_STATE_DIR": "/tmp/fixture-home/.local/share/ternuxx"}), \
             patch.object(sys, "stdin", io.StringIO(key + "\n")), \
             patch.object(sys, "stdout", output), \
             patch.object(management_service, "dispatch", return_value=response) as dispatch:
            result = management_service.main([
                "--operation", "ssh.keys.add.preview", "--public-key-stdin", "--json"])
        self.assertEqual(result, 0)
        request = dispatch.call_args.args[0]
        self.assertEqual(request["args"], {"public_key": key})
        self.assertNotIn(key, output.getvalue())

    def test_cli_ssh_autostart_preview_requires_typed_preference(self):
        response = {"ok": True, "data": {"status": "ready", "changed": True}}
        with patch.dict(os.environ, {"TERMUX_VERSION": "test", "PREFIX": "/data/data/com.termux/files/usr", "HOME": "/tmp/home"}), \
             patch("sys.stdout", io.StringIO()), \
             patch.object(management_service, "dispatch", return_value=response) as dispatch:
            self.assertEqual(management_service.main(["--operation", "ssh.service.autostart.preview",
                "--autostart-disabled", "--json"]), 0)
        self.assertEqual(dispatch.call_args.args[0]["args"], {"enabled": False})

    def test_cli_client_key_preview_uses_typed_name_argument(self):
        response = {"ok": True, "data": {"status": "ready"}}
        output = io.StringIO()
        with patch.dict(os.environ, {"TERMUX_VERSION": "test",
                "PREFIX": "/data/data/com.termux/files/usr", "HOME": "/tmp/home"}), \
             patch.object(sys, "stdout", output), \
             patch.object(management_service, "dispatch", return_value=response) as dispatch:
            self.assertEqual(management_service.main([
                "--operation", "ssh.client-key.create.preview",
                "--key-name", "recovery8023", "--json"]), 0)
        self.assertEqual(dispatch.call_args.args[0]["args"], {"name": "recovery8023"})

    def test_web_and_session_policies_expose_only_scoped_previewed_key_mutations(self):
        expected = {"ssh.keys.add.preview", "ssh.keys.add.apply",
                    "ssh.keys.remove.preview", "ssh.keys.remove.apply",
                    "ssh.client-key.create.preview", "ssh.client-key.create.apply"}
        autostart_mutations = {"ssh.service.autostart.preview", "ssh.service.autostart.apply"}
        self.assertTrue(expected | autostart_mutations <= management_http_runtime._WEB_MUTATING_OPERATIONS)
        self.assertEqual({management_authorization.required_capability(op) for op in expected},
                         {"ssh.credentials.manage"})
        self.assertTrue(expected | autostart_mutations <= management_sessions.MUTATING_OPERATIONS)
        self.assertEqual(management_authorization.required_capability("ssh.service.autostart.status"), "diagnostics.read")
        page = (ROOT / "lib/management_web_ui.html").read_text()
        self.assertIn("Enroll a public key", page)
        self.assertIn("Remove a key by fingerprint", page)
        self.assertIn("sshKeyPlan(\"ssh.keys.add.preview\"", page)
        self.assertIn("sshKeyPlan(\"ssh.keys.remove.preview\"", page)
        self.assertIn("both owner-managed SSH 8022 and Ternuxx SSH 8023", page)

    def test_tui_catalog_lists_only_owned_regular_public_key_files(self):
        with tempfile.TemporaryDirectory(prefix="tui-ssh-keys-") as temp:
            home = Path(temp)
            ssh = home / ".ssh"
            ssh.mkdir(mode=0o700)
            (ssh / "laptop.pub").write_text(ed25519_public() + "\n")
            (ssh / "two-lines.pub").write_text(ed25519_public() + "\n" + ed25519_public() + "\n")
            (ssh / "bad.pub").write_text("not a key\n")
            (ssh / "link.pub").symlink_to(ssh / "laptop.pub")
            os.chown(home, os.getuid(), -1)
            os.chown(ssh, os.getuid(), -1)
            with patch.object(terminal_ui.Path, "home", return_value=home):
                keys = terminal_ui._public_key_catalog()
        self.assertEqual([item["name"] for item in keys], ["laptop.pub"])
        self.assertEqual(keys[0]["key_type"], "ssh-ed25519")

    def test_gtk_key_management_is_in_shared_resource_catalog(self):
        catalog = management_service.dispatch({
            "api_version": 1, "request_id": "gtk-key-catalog-001",
            "operation": "management.catalog", "args": {},
        }, env={"TERMUX_VERSION": "fixture", "PREFIX": "/data/data/com.termux/files/usr",
                "HOME": "/tmp", "TERNUXX_STATE_DIR": "/tmp/.local/share/ternuxx"})
        self.assertTrue(catalog["ok"])
        ssh = next(item for item in catalog["data"]["resources"]
                   if item["id"] == "network.ssh.managed-8023")
        self.assertIn("ssh.keys.add.preview", ssh["supported_operations"])
        self.assertIn("ssh.client-key.create.preview", ssh["supported_operations"])
        self.assertIn("ssh.service.autostart.status", ssh["supported_operations"])
        self.assertIn("ssh.service.autostart.preview", ssh["supported_operations"])
        self.assertIn("ssh.service.autostart.apply", ssh["supported_operations"])


if __name__ == "__main__":
    unittest.main()
