"""Contract tests for the memory-only management-session primitive."""
from __future__ import annotations

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import management_authorization  # noqa: E402
import management_sessions  # noqa: E402


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class ManagementSessionTests(unittest.TestCase):
    def make_authority(self, *, clock=None, grants=None, idle_ttl=30):
        return management_sessions.ManagementSessionAuthority(
            "B" * 48,
            grants if grants is not None else {"diagnostics.read", "ssh.managed.lifecycle"},
            idle_ttl_seconds=idle_ttl,
            absolute_ttl_seconds=max(90, idle_ttl),
            clock=clock or FakeClock(),
        )

    def issue(self, authority, scopes=None):
        return authority.exchange_bootstrap(
            "B" * 48,
            scopes if scopes is not None else {"diagnostics.read", "ssh.managed.lifecycle"},
        )

    def test_bootstrap_issues_memory_only_scoped_credentials_once(self) -> None:
        authority = self.make_authority()
        issued = self.issue(authority, {"diagnostics.read"})
        self.assertEqual(issued.capabilities, ("diagnostics.read",))
        self.assertEqual(authority.active_session_count(), 1)
        self.assertNotIn(issued.bearer_token, repr(issued))
        self.assertNotIn(issued.csrf_token, repr(issued))
        with self.assertRaises(PermissionError):
            self.issue(authority, {"diagnostics.read"})

    def test_resume_restores_same_live_session_and_csrf_without_reusing_bootstrap(self) -> None:
        authority = self.make_authority()
        issued = self.issue(authority, {"diagnostics.read", "ssh.managed.lifecycle"})
        resumed = authority.resume_session(issued.bearer_token)
        self.assertEqual(resumed.session_ref, issued.session_ref)
        self.assertEqual(resumed.bearer_token, issued.bearer_token)
        self.assertEqual(resumed.csrf_token, issued.csrf_token)
        self.assertEqual(resumed.capabilities, issued.capabilities)
        self.assertTrue(authority.authorize_request(
            resumed.bearer_token, "ssh.service.restart", csrf_token=resumed.csrf_token).allowed)
        with self.assertRaises(PermissionError):
            self.issue(authority, {"diagnostics.read"})

    def test_resume_refuses_and_prunes_expired_session(self) -> None:
        clock = FakeClock()
        authority = self.make_authority(clock=clock, idle_ttl=30)
        issued = self.issue(authority, {"diagnostics.read"})
        clock.advance(30)
        with self.assertRaises(PermissionError):
            authority.resume_session(issued.bearer_token)
        self.assertEqual(authority.active_session_count(), 0)

    def test_concurrent_bootstrap_exchange_issues_at_most_one_session(self) -> None:
        authority = self.make_authority()
        def exchange():
            try:
                return authority.exchange_bootstrap("B" * 48, {"diagnostics.read"})
            except PermissionError:
                return None
        with ThreadPoolExecutor(max_workers=8) as pool:
            outcomes = list(pool.map(lambda _index: exchange(), range(8)))
        self.assertEqual(sum(outcome is not None for outcome in outcomes), 1)
        self.assertEqual(authority.active_session_count(), 1)

    def test_bootstrap_auth_and_requested_scopes_fail_closed(self) -> None:
        authority = self.make_authority()
        with self.assertRaises(PermissionError):
            authority.exchange_bootstrap("wrong" + "B" * 48, {"diagnostics.read"})
        with self.assertRaises(PermissionError):
            authority.exchange_bootstrap("B" * 48, {"boot.manage"})
        self.assertEqual(authority.active_session_count(), 0)

    def test_exact_scope_and_csrf_are_required_for_mutations(self) -> None:
        authority = self.make_authority()
        read_only = self.issue(authority, {"diagnostics.read"})
        self.assertTrue(authority.authorize_request(
            read_only.bearer_token, "ssh.inspect").allowed)
        denied = authority.authorize_request(
            read_only.bearer_token, "ssh.service.restart", csrf_token=read_only.csrf_token)
        self.assertEqual(denied.reason, "scope_denied")

        control = self.make_authority()
        scoped = self.issue(control, {"ssh.managed.lifecycle"})
        self.assertEqual(control.authorize_request(
            scoped.bearer_token, "ssh.service.restart").reason, "csrf_rejected")
        self.assertEqual(control.authorize_request(
            scoped.bearer_token, "ssh.service.restart", csrf_token="wrong").reason,
            "csrf_rejected")
        self.assertTrue(control.authorize_request(
            scoped.bearer_token, "ssh.service.restart", csrf_token=scoped.csrf_token).allowed)
        other = self.make_authority(grants={"services.manage"})
        services_only = self.issue(other, {"services.manage"})
        self.assertEqual(other.authorize_request(
            services_only.bearer_token, "ssh.service.stop", csrf_token=services_only.csrf_token).reason,
            "scope_denied")

    def test_graphics_verification_requires_control_scope_and_csrf(self):
        control = self.make_authority(grants={"graphics.manage"})
        issued = self.issue(control, {"graphics.manage"})
        with self.assertRaises(ValueError):
            self.make_authority(grants={"guest.diagnostics.read"})
        reader = self.make_authority(grants={"diagnostics.read"})
        read_session = self.issue(reader, {"diagnostics.read"})
        for operation in ("graphics.provider.verify",):
            with self.subTest(operation=operation):
                self.assertEqual(reader.authorize_request(
                    read_session.bearer_token, operation,
                    csrf_token=read_session.csrf_token).reason, "scope_denied")
                self.assertEqual(control.authorize_request(
                    issued.bearer_token, operation).reason, "csrf_rejected")
                self.assertTrue(control.authorize_request(
                    issued.bearer_token, operation, csrf_token=issued.csrf_token).allowed)

    def test_unknown_operations_and_bad_tokens_are_unauthenticated_or_denied(self) -> None:
        authority = self.make_authority()
        issued = self.issue(authority, {"diagnostics.read"})
        self.assertEqual(authority.authorize_request("short", "ssh.inspect").reason,
                         "unauthenticated")
        self.assertEqual(authority.authorize_request(
            issued.bearer_token, "shell.exec").reason, "scope_denied")

    def test_idle_and_absolute_expiry_are_enforced(self) -> None:
        clock = FakeClock()
        authority = self.make_authority(clock=clock)
        issued = self.issue(authority, {"diagnostics.read"})
        clock.advance(29)
        self.assertTrue(authority.authorize_request(issued.bearer_token, "ssh.inspect").allowed)
        clock.advance(30)
        self.assertEqual(authority.authorize_request(
            issued.bearer_token, "ssh.inspect").reason, "session_expired")

        clock = FakeClock()
        authority = self.make_authority(clock=clock, idle_ttl=60)
        issued = self.issue(authority, {"diagnostics.read"})
        clock.advance(30)
        self.assertTrue(authority.authorize_request(issued.bearer_token, "ssh.inspect").allowed)
        clock.advance(30)
        self.assertTrue(authority.authorize_request(issued.bearer_token, "ssh.inspect").allowed)
        clock.advance(30)
        self.assertEqual(authority.authorize_request(
            issued.bearer_token, "ssh.inspect").reason, "session_expired")

    def test_revoke_and_global_disable_invalidate_tokens(self) -> None:
        authority = self.make_authority()
        issued = self.issue(authority, {"diagnostics.read"})
        self.assertTrue(authority.revoke(issued.bearer_token))
        self.assertFalse(authority.revoke(issued.bearer_token))
        self.assertEqual(authority.authorize_request(
            issued.bearer_token, "ssh.inspect").reason, "unauthenticated")

        authority = self.make_authority()
        issued = self.issue(authority, {"diagnostics.read"})
        self.assertEqual(authority.revoke_all(), 1)
        self.assertEqual(authority.authorize_request(
            issued.bearer_token, "ssh.inspect").reason, "unauthenticated")
        with self.assertRaises(PermissionError):
            self.issue(authority, {"diagnostics.read"})

    def test_access_classification_covers_every_operation_exactly_once(self) -> None:
        read = management_sessions.READ_ONLY_OPERATIONS
        mutation = management_sessions.MUTATING_OPERATIONS
        known = set(management_authorization.OPERATION_CAPABILITIES)
        self.assertTrue(management_sessions.MUTATING_OPERATIONS)
        self.assertTrue(read.isdisjoint(mutation))
        self.assertEqual(read | mutation, known)
        self.assertNotIn("ssh.inspect", mutation)

    def test_bootstrap_secret_generator_returns_high_entropy_url_safe_value(self) -> None:
        secret = management_sessions.new_bootstrap_secret()
        self.assertGreaterEqual(len(secret), 40)
        self.assertTrue(all(character.isalnum() or character in "-_" for character in secret))


if __name__ == "__main__":
    unittest.main()
