#!/usr/bin/env python3
"""Preview-first lifecycle control for the one fixed Ternuxx Runit SSH unit."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import time
from typing import Callable

import operation_journal
import ssh_diagnostics

SERVICE_ID = "ternuxx-sshd"


class ServiceActionError(RuntimeError):
    """An ownership, state, or confirmation check prevented service control."""


def _source_path(source: str | os.PathLike[str] | None) -> Path:
    return ssh_diagnostics.service_definition_source(source)


def _manager(prefix: Path) -> Path:
    path = prefix / "bin/sv"
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ServiceActionError("Termux Runit command is unavailable") from exc
    if (stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid() or metadata.st_mode & 0o022
            or not metadata.st_mode & 0o100):
        raise ServiceActionError("Termux Runit command identity is unsafe")
    return path


def _manager_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise ServiceActionError("Termux Runit command identity cannot be read") from exc


def _status(
    prefix: Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> str:
    manager = _manager(prefix)
    try:
        result = runner([str(manager), "status", SERVICE_ID], capture_output=True, text=True,
                        timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ServiceActionError("Termux Runit status is unavailable") from exc
    lines = result.stdout.splitlines()
    if not lines:
        raise ServiceActionError("Termux Runit returned an unknown service state")
    line = lines[0].strip()
    if line.startswith(f"run: {SERVICE_ID}:"):
        return "running"
    if line.startswith(f"down: {SERVICE_ID}:"):
        return "stopped"
    raise ServiceActionError("Termux Runit returned an unknown service state")


def _snapshot(
    action: str,
    *,
    prefix: str | os.PathLike[str],
    source: str | os.PathLike[str] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    if action not in {"start", "stop"}:
        raise ServiceActionError("SSH service action must be start or stop")
    prefix_path = Path(prefix)
    identity = ssh_diagnostics._managed_service_definition_identity(prefix_path, _source_path(source))
    if identity.get("status") != "verified":
        raise ServiceActionError("Fixed Ternuxx service definition ownership is not verified")
    manager = _manager(prefix_path)
    current = _status(prefix_path, runner=runner)
    target = "running" if action == "start" else "stopped"
    core = {
        "service_id": SERVICE_ID,
        "action": action,
        "current_status": current,
        "target_status": target,
        "source_sha256": identity.get("source_sha256"),
        "installed_sha256": identity.get("installed_sha256"),
        "manager": "runit",
        "manager_sha256": _manager_sha256(manager),
    }
    plan_id = hashlib.sha256(json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    changed = current != target
    return {
        **core,
        "plan_id": plan_id if changed else None,
        "requires_confirmation": changed,
        "changed": False,
        "read_only": True,
        "impact": ("Stops only the fixed Ternuxx Runit unit; clients connected to its managed SSH port may disconnect."
                   if action == "stop" else "Starts only the fixed Ternuxx Runit unit; it does not change SSH configuration."),
    }


def preview(
    action: str,
    *,
    prefix: str | os.PathLike[str],
    source: str | os.PathLike[str] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    return _snapshot(action, prefix=prefix, source=source, runner=runner)


def apply(
    action: str,
    *,
    prefix: str | os.PathLike[str],
    home: str | os.PathLike[str],
    state_dir: str | os.PathLike[str],
    confirmed: bool,
    plan_id: str | None,
    source: str | os.PathLike[str] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, object]:
    if type(confirmed) is not bool:
        raise ServiceActionError("Explicit confirmation is required")
    current_plan = preview(action, prefix=prefix, source=source, runner=runner)
    if not confirmed:
        return current_plan
    if not isinstance(plan_id, str) or not current_plan["requires_confirmation"] or plan_id != current_plan["plan_id"]:
        raise ServiceActionError("Service plan changed or the exact plan ID is missing")
    prefix_path = Path(prefix)
    operation_kind = "service.start" if action == "start" else "service.stop"
    operation_id = operation_journal.begin(
        str(state_dir), operation_kind,
        f"{action} fixed {SERVICE_ID} unit",
        home_dir=home,
    )
    command = "up" if action == "start" else "down"
    operation_status = "needs_recovery"
    final_status = "unknown"
    try:
        manager = _manager(prefix_path)
        try:
            runner([str(manager), command, SERVICE_ID], capture_output=True, text=True,
                   timeout=8, check=False)
        except (OSError, subprocess.TimeoutExpired):
            raise ServiceActionError("Runit action timed out or could not run")
        target = "running" if action == "start" else "stopped"
        deadline = monotonic() + 5.0
        while True:
            try:
                final_status = _status(prefix_path, runner=runner)
            except ServiceActionError:
                final_status = "unknown"
            if final_status == target:
                operation_status = "complete"
                break
            if monotonic() >= deadline:
                operation_status = "failed" if final_status == current_plan["current_status"] else "needs_recovery"
                break
            sleep(0.1)
        detail = f"{SERVICE_ID} {action} verified={operation_status == 'complete'} status={final_status}"
        operation_journal.update(str(state_dir), operation_id, operation_status, detail, home_dir=home)
        if operation_status != "complete":
            raise ServiceActionError(f"Service action did not reach the requested state; journal={operation_id}")
        return {
            "service_id": SERVICE_ID,
            "action": action,
            "status": final_status,
            "changed": True,
            "operation_id": operation_id,
            "read_only": False,
        }
    except Exception:
        # Preserve active journal evidence if a failure occurs after begin().
        try:
            record = operation_journal.inspect_record(str(state_dir), operation_id, home_dir=home)
            if record["status"] in operation_journal.ACTIVE:
                operation_journal.update(str(state_dir), operation_id, "needs_recovery",
                                         f"{SERVICE_ID} {action} outcome requires review",
                                         home_dir=home)
        except Exception:
            pass
        raise
