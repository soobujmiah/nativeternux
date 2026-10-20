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
        self.assertEqual(set(management_authorization.OPERATION_CAPABILITIES),
                         set(management_service.OPERATIONS))
        self.assertTrue(all(isinstance(scope, str) and scope and "." in scope
                            for scope in management_authorization.OPERATION_CAPABILITIES.values()))

    def test_proot_app_launch_and_shortcut_apply_require_distinct_capabilities(self) -> None:
        self.assertEqual(management_authorization.required_capability("proot.shortcuts.list"), "diagnostics.read")
        self.assertEqual(management_authorization.required_capability("proot.shortcuts.preview"), "diagnostics.read")
        self.assertEqual(management_authorization.required_capability("proot.app.launch"), "applications.launch")
        self.assertEqual(management_authorization.required_capability("proot.shortcuts.apply"), "applications.shortcuts.manage")
        self.assertEqual(management_authorization.required_capability("proot.shortcuts.sync"), "applications.manage")
        self.assertFalse(management_authorization.authorize("proot.shortcuts.apply", ["diagnostics.read"]))
        self.assertFalse(management_authorization.authorize("proot.shortcuts.apply", ["applications.manage"]))
        self.assertTrue(management_authorization.authorize("proot.shortcuts.apply", ["applications.shortcuts.manage"]))
        self.assertFalse(management_authorization.authorize("proot.shortcuts.sync", ["applications.shortcuts.manage"]))

    def test_proot_health_uses_read_scope_and_is_not_mutating(self) -> None:
        import management_sessions
        self.assertEqual(management_authorization.required_capability("proot.sessions.health"), "diagnostics.read")
        self.assertIn("proot.sessions.health", management_sessions.READ_ONLY_OPERATIONS)
        self.assertNotIn("proot.sessions.health", management_sessions.MUTATING_OPERATIONS)

    def test_unknown_or_malformed_operation_fails_closed(self) -> None:
        for operation in ("shell.exec", "adb.forward", None, [], {"ssh.inspect": True}):
            self.assertIsNone(management_authorization.required_capability(operation))
            self.assertFalse(management_authorization.authorize(operation, {"diagnostics.read"}))

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
