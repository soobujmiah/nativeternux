"""Shared human-facing vocabulary for Ternuxx management clients.

The resource catalog remains authoritative for category and resource identity.
This module supplies presentation labels only; it never decides lifecycle state
or authorizes an operation.
"""
from __future__ import annotations

from typing import Final

STATUS_LABELS: Final[dict[str, str]] = {
    "healthy": "Healthy",
    "running": "Running",
    "ready": "Ready",
    "starting": "Starting",
    "stopping": "Stopping",
    "stopped": "Stopped",
    "failed": "Failed",
    "stale": "Stale",
    "unknown": "Unknown",
    "unsafe": "Unsafe",
    "partial": "Partial",
    "implemented": "Implemented",
    "external": "Externally managed",
    "unverified": "Unverified",
    "unavailable": "Unavailable",
    "planned": "Planned",
    "not-queried": "Not checked",
}

STATUS_TONES: Final[dict[str, str]] = {
    "healthy": "good", "running": "good", "ready": "good",
    "implemented": "good", "starting": "pending", "stopping": "pending",
    "partial": "pending", "stale": "warning", "failed": "danger",
    "unsafe": "danger", "unknown": "muted", "stopped": "muted",
    "external": "muted", "unverified": "muted", "unavailable": "muted",
    "planned": "muted", "not-queried": "muted",
}

OPERATION_LABELS: Final[dict[str, str]] = {
    "management.catalog": "Browse resources",
    "desktop.status": "Desktop status",
    "desktop.monitor.status": "Activity monitoring policy",
    "desktop.monitor.configure": "Update monitoring policy",
    "doctor.report": "System health report",
    "ssh.inspect": "SSH listener inspection",
    "native.ssh.status": "Managed SSH status",
    "proot.status": "Debian PRoot status",
    "proot.guest.verify": "Verify guest integration",
    "proot.shortcuts.list": "Application shortcuts",
    "proot.shortcuts.preview": "Preview shortcut change",
    "proot.shortcuts.apply": "Apply shortcut change",
    "ssh.service.start": "Start managed SSH",
    "ssh.service.stop": "Stop managed SSH",
    "boot.profile.status": "Boot profile status",
    "boot.profile.preview": "Preview boot profile",
    "boot.cron.status": "Cron boot integration status",
    "boot.cron.validate": "Validate Cron boot integration",
    "boot.cron.preview": "Preview Cron boot integration change",
    "boot.cron.enable": "Enable Cron at Termux boot",
    "boot.cron.disable": "Disable Cron at Termux boot",
    "recovery.status": "Recovery status",
    "backup.list": "Available backups",
}


def status_label(value: object) -> str:
    """Translate known status values while preserving unknown values safely."""
    if not isinstance(value, str):
        return "Unknown"
    return STATUS_LABELS.get(value, value.replace("_", " ").capitalize())


def operation_label(operation: str) -> str:
    """Return a friendly operation label without hiding unknown operations."""
    return OPERATION_LABELS.get(operation, operation.replace(".", " ").replace("_", " ").capitalize())
