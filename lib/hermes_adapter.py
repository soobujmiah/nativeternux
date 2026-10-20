"""Read-only adapter for the locally installed Hermes scheduler status.

This first provider slice deliberately does not read task definitions, modify
Hermes configuration, start its gateway, or execute scheduled/user tasks.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import re
import subprocess
from typing import Callable


Runner = Callable[..., subprocess.CompletedProcess[str]]
_NATIVE_PREFIX = Path("/data/data/com.termux/files/usr")
_VERSION = re.compile(r"^Hermes Agent (v\S+)", re.MULTILINE)
_NOT_SERVING = re.compile(r"""No scheduler is serving profile ['"]([^'"]+)['"]""")
_READY = "Gateway is running — cron jobs will fire automatically"


def inspect(*, prefix: str, home: str, runner: Runner = subprocess.run) -> dict[str, object]:
    """Inspect Hermes version and scheduler health without exposing CLI output."""
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    root = Path(prefix)
    expected_root = _NATIVE_PREFIX
    if str(root) != str(expected_root) or not home:
        return _unavailable("native_termux_required", checked_at)

    executable = root / "bin/hermes"
    try:
        resolved = executable.resolve(strict=True)
        canonical_root = root.resolve(strict=True)
        if os.path.commonpath((str(canonical_root), str(resolved))) != str(canonical_root):
            return _unavailable("executable_outside_termux_prefix", checked_at)
        if not resolved.is_file() or not os.access(resolved, os.X_OK):
            return _unavailable("executable_not_runnable", checked_at)
    except (OSError, ValueError):
        return _unavailable("not_installed", checked_at)

    env = {"HOME": home, "PREFIX": str(root), "PATH": str(root / "bin")}
    try:
        version_result = runner([str(executable), "--version"], capture_output=True,
                                text=True, timeout=5, check=False, env=env)
        if version_result.returncode != 0:
            return _unavailable("version_probe_failed", checked_at)
        match = _VERSION.search(version_result.stdout or "")
        version = match.group(1) if match else "unknown"
        status_result = runner([str(executable), "cron", "status"], capture_output=True,
                               text=True, timeout=8, check=False, env=env)
    except subprocess.TimeoutExpired:
        return _unknown("probe_timeout", checked_at)
    except OSError:
        return _unavailable("probe_unavailable", checked_at)

    if status_result.returncode != 0:
        return {
            "provider_id": "hermes", "contract_version": 1, "availability": "available",
            "version": version, "management_mode": "disconnected",
            "task_operations": "unsupported",
            "scheduler": {"state": "unknown", "profile": "unknown", "health": "unknown"},
            "checked_at": checked_at, "error_code": "status_probe_failed",
        }

    output = status_result.stdout or ""
    no_scheduler = _NOT_SERVING.search(output)
    if no_scheduler:
        scheduler_state, profile, health = "not_running", no_scheduler.group(1), "not_ready"
    elif _READY in output:
        scheduler_state = "running"
        profile_match = re.search(r"""profile ['"]([^'"]+)['"]""", output)
        profile = profile_match.group(1) if profile_match else "unknown"
        health = "ready"
    else:
        scheduler_state, profile, health = "unknown", "unknown", "unknown"

    return {
        "provider_id": "hermes", "contract_version": 1, "availability": "available",
        "version": version, "management_mode": "disconnected",
        "task_operations": "unsupported",
        "scheduler": {"state": scheduler_state, "profile": profile, "health": health},
        "checked_at": checked_at,
        "error_code": None if scheduler_state != "unknown" else "unrecognized_status_output",
    }


def _unavailable(code: str, checked_at: str) -> dict[str, object]:
    return {"provider_id": "hermes", "contract_version": 1, "availability": "unavailable",
            "version": "unknown", "management_mode": "disconnected", "task_operations": "unsupported",
            "scheduler": {"state": "unknown", "profile": "unknown", "health": "unknown"},
            "checked_at": checked_at, "error_code": code}


def _unknown(code: str, checked_at: str) -> dict[str, object]:
    return {"provider_id": "hermes", "contract_version": 1, "availability": "unknown",
            "version": "unknown", "management_mode": "disconnected", "task_operations": "unsupported",
            "scheduler": {"state": "unknown", "profile": "unknown", "health": "unknown"},
            "checked_at": checked_at, "error_code": code}
