"""Default-deny capability policy for future authenticated management adapters.

This module does not authenticate callers and is not a transport. An adapter
must establish a trusted session, then pass that session's explicit grants to
``authorize`` before dispatching an allowlisted operation.
"""
from __future__ import annotations

from collections.abc import Iterable


# One narrow capability per operation. New application operations must be
# reviewed here before any non-CLI adapter can expose them.
OPERATION_CAPABILITIES: dict[str, str] = {
    "management.catalog": "diagnostics.read",
    "doctor.report": "diagnostics.read",
    "ssh.inspect": "diagnostics.read",
    "native.ssh.status": "diagnostics.read",
    "proot.status": "diagnostics.read",
    "proot.app.launch": "applications.launch",
    "proot.shortcuts.list": "diagnostics.read",
    "proot.shortcuts.preview": "diagnostics.read",
    "proot.shortcuts.apply": "applications.manage",
    "proot.guest.verify": "guest.diagnostics.read",
    "remote.access.preview": "remote_policy.read",
    "ssh.service.start": "services.manage",
    "ssh.service.stop": "services.manage",
    "boot.status": "diagnostics.read",
    "boot.profile.status": "diagnostics.read",
    "boot.profile.preview": "diagnostics.read",
    "boot.enable": "boot.manage",
    "boot.disable": "boot.manage",
    "backup.create": "state.backup",
    "backup.list": "diagnostics.read",
    "backup.inspect": "diagnostics.read",
    "restore.preview": "diagnostics.read",
    "restore.apply": "state.restore",
    "recovery.status": "diagnostics.read",
    "recovery.resolve": "recovery.manage",
    "recovery.inspect": "diagnostics.read",
    "recovery.rollback.preview": "diagnostics.read",
    "recovery.rollback.apply": "recovery.manage",
    "wakelock.status": "diagnostics.read",
    "wakelock.acquire": "wakelock.manage",
    "wakelock.release": "wakelock.manage",
    "continuity.status": "continuity.read",
    "continuity.prepare": "continuity.manage",
    "continuity.verify": "continuity.manage",
    "continuity.prepare-reboot-test": "continuity.manage",
    "continuity.verify-reboot-test": "continuity.manage",
    "continuity.resume-info": "continuity.read",
}


def required_capability(operation: object) -> str | None:
    """Return the exact scope required for a known operation; unknown denies."""
    if not isinstance(operation, str):
        return None
    return OPERATION_CAPABILITIES.get(operation)


def authorize(operation: object, grants: Iterable[str]) -> bool:
    """Authorize only an explicitly granted exact capability.

    Strings/bytes are rejected as grant containers to avoid treating one
    capability string as an iterable of characters. No wildcard inheritance
    or implicit read/write escalation is supported.
    """
    required = required_capability(operation)
    if required is None or isinstance(grants, (str, bytes)):
        return False
    try:
        return required in grants
    except TypeError:
        return False
