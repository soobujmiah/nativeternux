"""Ephemeral bearer sessions for the authenticated local management transport.

This module does not open sockets, persist credentials, or dispatch operations.
The HTTP adapter must call ``authorize_request`` before using the application
service. It must keep the issued bearer and CSRF values out of URLs and logs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import secrets
import threading
import time
from collections.abc import Callable, Iterable

import management_authorization


DEFAULT_IDLE_TTL_SECONDS = 15 * 60
DEFAULT_ABSOLUTE_TTL_SECONDS = 8 * 60 * 60
MAX_CAPABILITIES = 32
MAX_TOKEN_LENGTH = 256

# Every known operation must be explicitly classified. Mutations also require
# the session-specific CSRF proof in a custom header.
MUTATING_OPERATIONS = frozenset({
    "desktop.start", "desktop.stop", "desktop.restart", "desktop.monitor.configure",
    "ssh.service.start", "ssh.service.stop", "ssh.service.deploy", "ssh.service.deploy.rollback.apply", "boot.enable", "boot.disable", "boot.cron.enable", "boot.cron.disable",
    "backup.create", "restore.apply", "recovery.resolve",
    "recovery.rollback.apply", "wakelock.acquire", "wakelock.release",
    "continuity.prepare", "continuity.verify", "continuity.prepare-reboot-test",
    "continuity.verify-reboot-test", "proot.app.launch", "proot.shortcuts.apply",
    "cron.jobs.create", "cron.jobs.update", "cron.jobs.remove",
    "proot.start", "proot.stop", "proot.recovery.reconcile",
    "cron.scheduler.start", "cron.scheduler.stop", "timezone.set",
})
READ_ONLY_OPERATIONS = frozenset({
    "management.catalog", "agent.hermes.status", "cron.status", "cron.executor.self_test",
    "proot.sessions.list", "proot.sessions.show", "proot.sessions.health", "proot.recovery.inspect",
    "proot.recovery.reconcile.preview", "proot.profiles.list", "proot.profiles.show",
    "proot.start.preview", "proot.stop.preview", "cron.jobs.list",
    "timezone.status", "timezone.list",
    "cron.jobs.show", "cron.jobs.validate", "cron.jobs.next_runs", "cron.executions.list", "cron.executions.show", "desktop.status", "desktop.monitor.status", "doctor.report",
    "ssh.inspect", "ssh.service.deploy.rollback.preview", "native.ssh.status", "proot.status", "proot.guest.verify",
    "proot.shortcuts.list", "proot.shortcuts.preview",
    "remote.access.preview", "boot.status", "boot.profile.status",
    "boot.profile.preview", "boot.cron.status", "boot.cron.validate", "boot.cron.preview", "backup.list", "backup.inspect", "restore.preview",
    "recovery.status", "recovery.inspect", "recovery.rollback.preview",
    "wakelock.status", "continuity.status", "continuity.resume-info",
})


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def new_bootstrap_secret() -> str:
    """Create a high-entropy secret for a trusted local server launcher."""
    return secrets.token_urlsafe(32)


@dataclass(frozen=True)
class IssuedSession:
    """One-time session credentials; repr deliberately hides both secrets."""

    session_ref: str
    bearer_token: str = field(repr=False)
    csrf_token: str = field(repr=False)
    capabilities: tuple[str, ...]
    idle_ttl_seconds: int
    absolute_ttl_seconds: int


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason: str
    session_ref: str | None = None


@dataclass
class _Session:
    session_ref: str
    bearer_digest: str
    csrf_digest: str
    capabilities: frozenset[str]
    created_at: float
    last_seen_at: float


class ManagementSessionAuthority:
    """Memory-only session issuer with a one-use local bootstrap secret.

    ``bootstrap_capabilities`` represents scopes approved by the trusted local
    server launcher. A browser/client can only request a subset. The caller is
    responsible for obtaining the bootstrap secret through a reviewed local
    channel and for enforcing loopback, Host, Origin, and request limits.
    """

    def __init__(
        self,
        bootstrap_secret: str,
        bootstrap_capabilities: Iterable[str],
        *,
        idle_ttl_seconds: int = DEFAULT_IDLE_TTL_SECONDS,
        absolute_ttl_seconds: int = DEFAULT_ABSOLUTE_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        token_factory: Callable[[], str] = secrets.token_urlsafe,
    ) -> None:
        if not isinstance(bootstrap_secret, str) or len(bootstrap_secret) < 40:
            raise ValueError("bootstrap secret must contain at least 40 characters")
        if type(idle_ttl_seconds) is not int or not 30 <= idle_ttl_seconds <= 3600:
            raise ValueError("idle TTL must be an integer from 30 to 3600 seconds")
        if type(absolute_ttl_seconds) is not int or not idle_ttl_seconds <= absolute_ttl_seconds <= 86400:
            raise ValueError("absolute TTL must be between idle TTL and 86400 seconds")
        self._bootstrap_digest = _digest(bootstrap_secret)
        self._bootstrap_used = False
        self._bootstrap_capabilities = self._validate_capabilities(bootstrap_capabilities)
        self._idle_ttl = idle_ttl_seconds
        self._absolute_ttl = absolute_ttl_seconds
        self._clock = clock
        self._token_factory = token_factory
        self._sessions: dict[str, _Session] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _validate_capabilities(capabilities: Iterable[str]) -> frozenset[str]:
        if isinstance(capabilities, (str, bytes)):
            raise ValueError("capabilities must be an explicit collection")
        try:
            values = tuple(capabilities)
        except TypeError as exc:
            raise ValueError("capabilities must be an explicit collection") from exc
        known = set(management_authorization.OPERATION_CAPABILITIES.values())
        if (len(values) > MAX_CAPABILITIES
                or any(not isinstance(value, str) or value not in known for value in values)
                or len(set(values)) != len(values)):
            raise ValueError("capabilities contain an unknown, duplicate, or excessive scope")
        return frozenset(values)

    def exchange_bootstrap(self, supplied_secret: str, requested_capabilities: Iterable[str]) -> IssuedSession:
        """Exchange the local bootstrap secret once for a narrowly scoped session."""
        if not isinstance(supplied_secret, str) or len(supplied_secret) > MAX_TOKEN_LENGTH:
            raise PermissionError("bootstrap authentication failed")
        with self._lock:
            if not hmac.compare_digest(_digest(supplied_secret), self._bootstrap_digest):
                raise PermissionError("bootstrap authentication failed")
            if self._bootstrap_used:
                raise PermissionError("bootstrap authentication failed")
            requested = self._validate_capabilities(requested_capabilities)
            if not requested.issubset(self._bootstrap_capabilities):
                raise PermissionError("requested capabilities are not approved")
            self._prune_expired()

            bearer = self._new_secret()
            csrf = self._new_secret()
            session_ref = self._token_factory()
            if (not isinstance(session_ref, str) or len(session_ref) < 16
                    or len(session_ref) > MAX_TOKEN_LENGTH):
                raise RuntimeError("session reference generation failed")
            if bearer == csrf or session_ref in {bearer, csrf}:
                raise RuntimeError("session credential collision")
            now = self._clock()
            digest = _digest(bearer)
            if digest in self._sessions:
                raise RuntimeError("session token collision")
            self._sessions[digest] = _Session(
                session_ref=session_ref,
                bearer_digest=digest,
                csrf_digest=_digest(csrf),
                capabilities=requested,
                created_at=now,
                last_seen_at=now,
            )
            self._bootstrap_used = True
            return IssuedSession(
                session_ref=session_ref,
                bearer_token=bearer,
                csrf_token=csrf,
                capabilities=tuple(sorted(requested)),
                idle_ttl_seconds=self._idle_ttl,
                absolute_ttl_seconds=self._absolute_ttl,
            )

    def authorize_request(
        self,
        bearer_token: str,
        operation: object,
        *,
        csrf_token: str | None = None,
    ) -> AuthorizationDecision:
        """Check session lifetime, exact operation scope, and mutation CSRF."""
        if not isinstance(bearer_token, str) or not 40 <= len(bearer_token) <= MAX_TOKEN_LENGTH:
            return AuthorizationDecision(False, "unauthenticated")
        digest = _digest(bearer_token)
        with self._lock:
            session = self._sessions.get(digest)
            if session is None:
                return AuthorizationDecision(False, "unauthenticated")
            now = self._clock()
            if (now - session.last_seen_at >= self._idle_ttl
                    or now - session.created_at >= self._absolute_ttl):
                self._sessions.pop(digest, None)
                return AuthorizationDecision(False, "session_expired")
            required = management_authorization.required_capability(operation)
            if required is None or required not in session.capabilities:
                return AuthorizationDecision(False, "scope_denied", session.session_ref)
            if operation in MUTATING_OPERATIONS:
                if not isinstance(csrf_token, str) or len(csrf_token) > MAX_TOKEN_LENGTH:
                    return AuthorizationDecision(False, "csrf_rejected", session.session_ref)
                if not hmac.compare_digest(_digest(csrf_token), session.csrf_digest):
                    return AuthorizationDecision(False, "csrf_rejected", session.session_ref)
            session.last_seen_at = now
            return AuthorizationDecision(True, "authorized", session.session_ref)

    def revoke(self, bearer_token: str) -> bool:
        """Revoke one session without returning or persisting its credentials."""
        if not isinstance(bearer_token, str) or len(bearer_token) > MAX_TOKEN_LENGTH:
            return False
        with self._lock:
            return self._sessions.pop(_digest(bearer_token), None) is not None

    def revoke_session(self, bearer_token: str, csrf_token: str) -> bool:
        """Revoke the presented session only when its CSRF proof also matches."""
        if (not isinstance(bearer_token, str) or not 40 <= len(bearer_token) <= MAX_TOKEN_LENGTH
                or not isinstance(csrf_token, str) or len(csrf_token) > MAX_TOKEN_LENGTH):
            return False
        digest = _digest(bearer_token)
        with self._lock:
            session = self._sessions.get(digest)
            if session is None:
                return False
            now = self._clock()
            if (now - session.last_seen_at >= self._idle_ttl
                    or now - session.created_at >= self._absolute_ttl):
                self._sessions.pop(digest, None)
                return False
            if not hmac.compare_digest(_digest(csrf_token), session.csrf_digest):
                return False
            self._sessions.pop(digest, None)
            return True

    def revoke_all(self) -> int:
        """Invalidate all active sessions and permanently consume bootstrap."""
        with self._lock:
            count = len(self._sessions)
            self._sessions.clear()
            self._bootstrap_used = True
            return count

    def active_session_count(self) -> int:
        """Return a count only; never expose session tokens or private metadata."""
        with self._lock:
            self._prune_expired()
            return len(self._sessions)

    def _prune_expired(self) -> None:
        with self._lock:
            now = self._clock()
            expired = [
                digest for digest, session in self._sessions.items()
                if (now - session.last_seen_at >= self._idle_ttl
                    or now - session.created_at >= self._absolute_ttl)
            ]
            for digest in expired:
                self._sessions.pop(digest, None)

    def _new_secret(self) -> str:
        value = self._token_factory()
        if not isinstance(value, str) or len(value) < 40 or len(value) > MAX_TOKEN_LENGTH:
            raise RuntimeError("secure token generation failed")
        return value
