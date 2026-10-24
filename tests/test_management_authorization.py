"""Default-deny capability policy for future non-CLI adapters."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import management_authorization  # noqa: E402
import management_service  # noqa: E402


class ManagementAuthorizationTests(unittest.TestCase):
    def test_every_application_operation_has_exactly_one_explicit_scope(self) -> None:
        # Ticket issuance is a transport-only Web operation handled by the
        # authenticated terminal endpoint, not generic management dispatch.
        self.assertEqual(set(management_authorization.OPERATION_CAPABILITIES),
                         set(management_service.OPERATIONS))
        self.assertTrue(all(isinstance(scope, str) and scope and "." in scope
                            for scope in management_authorization.OPERATION_CAPABILITIES.values()))

    def test_retired_proot_and_terminal_operations_are_denied(self) -> None:
        for operation in ("proot.status", "proot.app.launch", "proot.sessions.health",
                          "proot.shortcuts.apply", "terminal.start", "terminal.input"):
            self.assertIsNone(management_authorization.required_capability(operation))
            self.assertFalse(management_authorization.authorize(operation, {"diagnostics.read"}))

    def test_unknown_or_malformed_operation_fails_closed(self) -> None:
        for operation in ("shell.exec", "adb.forward", None, [], {"ssh.inspect": True}):
            self.assertIsNone(management_authorization.required_capability(operation))
            self.assertFalse(management_authorization.authorize(operation, {"diagnostics.read"}))

    def test_ssh_key_inventory_has_separate_read_scope(self) -> None:
        self.assertEqual(management_authorization.required_capability("ssh.keys.list"), "ssh.credentials.read")
        self.assertFalse(management_authorization.authorize("ssh.keys.list", {"diagnostics.read"}))
        self.assertTrue(management_authorization.authorize("ssh.keys.list", {"ssh.credentials.read"}))
        import management_sessions
        self.assertIn("ssh.keys.list", management_sessions.READ_ONLY_OPERATIONS)
        self.assertNotIn("ssh.keys.list", management_sessions.MUTATING_OPERATIONS)

    def test_directory_tree_file_handoff_uses_read_only_diagnostics_scope(self) -> None:
        import management_sessions
        self.assertEqual(management_authorization.required_capability("software.app.run"), "software.manage")
        self.assertFalse(management_authorization.authorize("software.app.run", {"diagnostics.read"}))
        self.assertTrue(management_authorization.authorize("software.app.run", {"software.manage"}))
        self.assertIn("software.app.run", management_sessions.READ_ONLY_OPERATIONS)
        self.assertNotIn("software.app.run", management_sessions.MUTATING_OPERATIONS)

    def test_grants_are_exact_and_do_not_escalate(self) -> None:
        self.assertTrue(management_authorization.authorize("ssh.inspect", {"diagnostics.read"}))
        self.assertFalse(management_authorization.authorize("ssh.service.stop", {"diagnostics.read"}))
        self.assertFalse(management_authorization.authorize("ssh.inspect", {"services.manage"}))
        self.assertFalse(management_authorization.authorize("ssh.inspect", {"*"}))

    def test_invalid_grant_containers_fail_closed(self) -> None:
        for grants in ("diagnostics.read", b"diagnostics.read", None, 5):
            self.assertFalse(management_authorization.authorize("ssh.inspect", grants))


if __name__ == "__main__":
    unittest.main()
