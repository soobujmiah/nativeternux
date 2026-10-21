"""Shared human-facing vocabulary for Ternuxx management clients.

The resource catalog remains authoritative for category and resource identity.
This module supplies presentation labels only; it never decides lifecycle state
or authorizes an operation.
"""
from __future__ import annotations

from typing import Final


FIELD_LABELS: Final[dict[str, str]] = {
    "status": "Status", "state": "State", "current": "Current state",
    "ready": "Ready for startup", "blockers": "What must be fixed", "actions": "Startup actions",
    "readiness": "Readiness", "availability": "Availability",
    "ownership": "Ownership", "authority": "Managed by",
    "provider": "Provider", "environment": "Environment",
    "enabled": "Enabled", "running": "Running", "healthy": "Health",
    "interval_seconds": "Check interval (seconds)", "interval_value": "Check interval",
    "activity_launch": "Request Activity launch when missing",
    "focus_check": "Check Activity focus", "boot": "Boot startup",
    "boot_status": "Boot status", "persistent": "Keep active in background",
    "wakelock": "Wake Lock", "last_checked": "Last checked",
    "message": "Details", "impact": "Change impact", "action": "Action",
    "operation_id": "Action", "id": "Reference", "code": "Reference",
    "profile": "Profile", "endpoint": "Connection address",
    "port": "Port", "bind_address": "Bind address", "auth_methods": "Login methods",
    "password_authentication": "Password login", "public_key_authentication": "Key login",
    "key_fingerprint": "Key fingerprint", "fingerprint": "Fingerprint",
    "listener": "Listener", "service": "Service", "operation": "Operation",
    "category": "Category", "name": "Name", "description": "Description",
    "count": "Count", "unresolved_count": "Items needing attention",
    "read_only": "Read-only check", "reason": "Reason", "error": "Problem",
    'boot_id_relation': 'Boot ID check',
    'configured_profile': 'Selected startup profile',
    'desired': 'Target state',
    'last_verified_at': 'Last verified',
    'source_operation': 'Checked by',
    'gui_visible': 'Visible on screen',
    'x11': 'X11 display',
    'xfce4_session': 'XFCE desktop',
    'supervisor': 'Session manager',
    'listen_address': 'Listen address',
    'pid': 'Process ID',
    'process_start': 'Process start identity',
    'owner_count': 'Active Wake Lock owners',
    'platform_lock_state': 'Android Wake Lock state',
    'phase': 'Phase',
}

HIDDEN_FIELDS: Final[frozenset[str]] = frozenset({
    "password", "private_key", "secret", "token", "bootstrap_secret",
    "api_version", "request_id", "plan_id", "idempotency_key",
})

VALUE_LABELS: Final[dict[str, str]] = {
    "ternuxx_verified": "Verified as managed by Ternuxx",
    "configuration-managed-scheduler-not-installed": "Policy saved; background checker is not installed",
    "scheduler-not-installed": "Background checker is not installed",
    "source-scheduler-not-installed": "Background checker is not installed",
    "disabled-by-default": "Off by default",
    "native-termux": "Native Termux",
    "debian-proot": "Debian PRoot",
    "android-host-via-termux": "Android host through Termux",
    "loopback": "This device only (127.0.0.1)",
    "service.stop": "Service stop",
    "service.start": "Service start",
    "service.restart": "Service restart",
    'proot-debian': 'Debian PRoot',
    'debian-glibc-guest': 'Debian Linux guest',
    'not-queried': 'Not checked yet',
    'not_configured': 'Not configured',
    'query-required': 'Check status to confirm',
    'query_required': 'Check status to confirm',
    'cold-boot-unverified': 'Boot startup not verified',
    'definition-verified-listener-pid-unverified': 'Service file verified; live listener ownership unknown',
    'read-only-evidence': 'Read-only diagnostic',
    'not_running': 'Not running',
    'not_connected': 'Not connected',
    'connected': 'Connected',
    'available': 'Available',
    'unavailable': 'Unavailable',
    'true': 'Yes',
    'false': 'No',
}

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
    "ssh.inspect": "SSH connection status",
    "native.ssh.status": "Managed SSH status",
    "boot.status": "Termux boot readiness",
    "boot.enable": "Enable startup profile",
    "boot.disable": "Disable startup profile",
    "wakelock.status": "Wake Lock status",
    "wakelock.acquire": "Keep selected service awake",
    "wakelock.release": "Release selected service Wake Lock",
    "cron.status": "Scheduled task service status",
    "management.logs.list": "Available Ternuxx logs",
    "management.logs.read": "Read recent Ternuxx log entries",
}

ERROR_MESSAGES: Final[dict[str, str]] = {
    "live_status_unavailable": "No live status check is available for this item.",
    "unknown_resource": "This item is no longer in the management catalog.",
    "invalid_action": "That action is not available.",
    "invalid_arguments": "The action details are incomplete or invalid.",
    "cancelled": "The action was cancelled.",
    "terminal_broker_unavailable": "The managed terminal service is unavailable.",
}


def status_label(value: object) -> str:
    """Translate known status values while preserving unknown values safely."""
    if not isinstance(value, str):
        return "Unknown"
    return STATUS_LABELS.get(value, value.replace("_", " ").capitalize())


def operation_label(operation: str) -> str:
    """Return a friendly operation label without hiding unknown operations."""
    return OPERATION_LABELS.get(operation, operation.replace(".", " ").replace("_", " ").capitalize())


def human_value(value: object) -> str:
    """Render common machine states as readable prose without changing data."""
    if isinstance(value, bool):
        return "On" if value else "Off"
    if value is None:
        return "Not reported"
    if isinstance(value, str):
        if value in VALUE_LABELS:
            return VALUE_LABELS[value]
        if value in STATUS_LABELS:
            return STATUS_LABELS[value]
        return value.replace("_", " ").replace("-", " ").strip().capitalize()
    return str(value)


def format_report(value: object) -> str:
    """Format shared-service responses for people; omit credentials and IDs."""
    lines: list[str] = []
    if isinstance(value, dict):
        if value.get("ok") is True:
            lines.append("Result: Completed")
        elif value.get("ok") is False:
            lines.append("Result: Needs attention")
        error = value.get("error")
        if isinstance(error, dict):
            code = error.get("code")
            if isinstance(code, str):
                message = ERROR_MESSAGES.get(
                    code, code.replace("_", " ").replace("-", " ").capitalize()
                )
                lines.append("Issue: " + message)
            detail = error.get("message") or error.get("detail")
            if isinstance(detail, str) and detail:
                lines.append("Details: " + detail)

    def visit(item: object, depth: int = 0, label: str | None = None) -> None:
        indent = "  " * depth
        if isinstance(item, dict):
            for key, child in item.items():
                normalized = str(key).lower()
                if depth == 0 and normalized in {"ok", "error"}:
                    continue
                if normalized in HIDDEN_FIELDS or any(x in normalized for x in ("private_key", "password", "secret", "token")):
                    continue
                if normalized in {"request_id", "plan_id", "idempotency_key", "session_id", "journal_id"}:
                    continue
                title = FIELD_LABELS.get(normalized, str(key).replace("_", " ").replace(".", " ").capitalize())
                visit(child, depth + (1 if label else 0), title)
        elif isinstance(item, (list, tuple)):
            if label and not item:
                lines.append(f"{indent}{label}: None")
            for index, child in enumerate(item, 1):
                if isinstance(child, (dict, list, tuple)):
                    lines.append(f"{indent}{index}.")
                    visit(child, depth + 1)
                else:
                    lines.append(f"{indent}{index}. {human_value(child)}")
        else:
            rendered = str(item) if label in {"Reference", "Action"} else human_value(item)
            lines.append(f"{indent}{label + ': ' if label else ''}{rendered}")

    visit(value)
    return "\n".join(lines) if lines else "No readable details were returned."
