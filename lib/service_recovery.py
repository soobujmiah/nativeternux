#!/usr/bin/env python3
"""Preview-first reconciliation for unresolved fixed native SSH service actions."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Callable
import subprocess

import operation_journal
import runit_service


class ServiceRecoveryError(RuntimeError):
    """A service journal record could not be safely reconciled."""


def _snapshot(
    operation_id: str,
    *,
    prefix: str | os.PathLike[str],
    state_dir: str | os.PathLike[str],
    home: str | os.PathLike[str],
    source: str | os.PathLike[str] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    if not isinstance(operation_id, str) or len(operation_id) != 32 or any(c not in "0123456789abcdef" for c in operation_id):
        raise ServiceRecoveryError("Operation ID is invalid")
    try:
        record = operation_journal.inspect_record(str(state_dir), operation_id, home_dir=home)
    except (OSError, ValueError, RuntimeError) as exc:
        raise ServiceRecoveryError("Operation record is unavailable or unsafe") from exc
    kind = record.get("kind")
    status_value = record.get("status")
    initial_status = "starting" if kind == "service.start" else "stopping"
    if (kind not in {"service.start", "service.stop"}
            or status_value not in {"needs_recovery", initial_status}):
        raise ServiceRecoveryError("Only an interrupted native SSH service action can be resolved")
    action = "start" if kind == "service.start" else "stop"
    status = runit_service.preview(action, prefix=prefix, source=source, runner=runner)
    target = "running" if action == "start" else "stopped"
    result = "complete" if status["current_status"] == target else "failed"
    core = {
        "operation_id": operation_id,
        "record_kind": record["kind"],
        "record_updated_at": record["updated_at"],
        "affected_paths": [str(operation_journal.record_path(str(state_dir), operation_id, home_dir=home))],
        "observed_service_status": status["current_status"],
        "expected_service_status": target,
        "resolution": result,
        "source_sha256": status["source_sha256"],
        "installed_sha256": status["installed_sha256"],
        "manager_sha256": status["manager_sha256"],
    }
    plan_id = hashlib.sha256(json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        **core,
        "plan_id": plan_id,
        "requires_confirmation": True,
        "changed": False,
        "read_only": True,
        "impact": "Updates only the listed journal path; it does not start or stop the SSH service.",
    }


def preview(operation_id: str, **kwargs: object) -> dict[str, object]:
    return _snapshot(operation_id, **kwargs)  # type: ignore[arg-type]


def resolve(
    operation_id: str,
    *,
    prefix: str | os.PathLike[str],
    state_dir: str | os.PathLike[str],
    home: str | os.PathLike[str],
    confirmed: bool,
    plan_id: str | None,
    source: str | os.PathLike[str] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    if type(confirmed) is not bool:
        raise ServiceRecoveryError("Explicit confirmation is required")
    current = _snapshot(operation_id, prefix=prefix, state_dir=state_dir, home=home,
                        source=source, runner=runner)
    if not confirmed:
        return current
    if not isinstance(plan_id, str) or plan_id != current["plan_id"]:
        raise ServiceRecoveryError("Recovery state changed or the exact preview plan ID is missing")
    # Re-observe the fixed unit immediately before touching the journal. This
    # operation never invokes the service manager's up/down actions.
    verified = _snapshot(operation_id, prefix=prefix, state_dir=state_dir, home=home,
                         source=source, runner=runner)
    if verified["plan_id"] != plan_id:
        raise ServiceRecoveryError("Service or journal state changed after preview")
    operation_journal.resolve_service_record(
        str(state_dir), operation_id, expected_kind=str(current["record_kind"]),
        expected_updated_at=str(current["record_updated_at"]),
        result=str(current["resolution"]), observed_status=str(current["observed_service_status"]),
        home_dir=home,
    )
    return {
        "operation_id": operation_id,
        "resolution": current["resolution"],
        "observed_service_status": current["observed_service_status"],
        "changed": True,
        "read_only": False,
        "affected_paths": current["affected_paths"],
        "service_action_performed": False,
    }
