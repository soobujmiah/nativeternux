#!/usr/bin/env python3
"""Dispatcher for narrowly scoped, preview-first journal reconciliation."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import Callable

import boot_profile_recovery
import backup_recovery
import desktop_session_recovery
import operation_journal
import restore_recovery
import runit_deployment
import service_recovery


class OperationRecoveryError(RuntimeError):
    """No supported operation-specific recovery handler is available."""


_HANDLER_GROUP_BY_KIND = {
    "service.start": "service",
    "service.stop": "service",
    "service.restart": "service",
    "service.deploy": "deploy",
    "service.deploy.rollback": "deploy_rollback",
    "boot.enable": "boot",
    "boot.disable": "boot",
    "desktop.start": "desktop",
    "desktop.stop": "desktop",
    "recovery.backup.create": "backup",
    "recovery.restore.apply": "restore",
    "recovery.restore.rollback": "restore",
}
SUPPORTED_KINDS = frozenset(_HANDLER_GROUP_BY_KIND)


def _kind(operation_id: str, *, state_dir: str | os.PathLike[str], home: str | os.PathLike[str]) -> str:
    try:
        record = operation_journal.inspect_record(str(state_dir), operation_id, home_dir=home)
    except (OSError, ValueError, RuntimeError) as exc:
        raise OperationRecoveryError("Operation record is unavailable or unsafe") from exc
    if record.get("status") not in {"starting", "stopping", "needs_recovery"}:
        raise OperationRecoveryError("Operation is not awaiting recovery")
    return str(record.get("kind"))


def preview(
    operation_id: str,
    *,
    prefix: str | os.PathLike[str],
    state_dir: str | os.PathLike[str],
    home: str | os.PathLike[str],
    source: str | os.PathLike[str] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    proc_root: Path = Path("/proc"),
) -> dict[str, object]:
    kind = _kind(operation_id, state_dir=state_dir, home=home)
    handler_group = _HANDLER_GROUP_BY_KIND.get(kind)
    if handler_group == "service":
        return service_recovery.preview(operation_id, prefix=prefix, state_dir=state_dir,
                                        home=home, source=source, runner=runner)
    if handler_group == "deploy":
        return runit_deployment.preview_rollback(operation_id, prefix=prefix, state_dir=state_dir,
                                                  home=home, runner=runner)
    if handler_group == "deploy_rollback":
        detail = operation_journal.inspect_record(str(state_dir), operation_id, home_dir=home)["detail"]
        deployment_id = str(detail).split("rollback of ", 1)[-1].split(" ", 1)[0]
        return runit_deployment.preview_rollback(deployment_id, prefix=prefix, state_dir=state_dir,
                home=home, runner=runner, recovery_operation_id=operation_id)
    if handler_group == "boot":
        return boot_profile_recovery.preview(operation_id, home=home, state_dir=state_dir)
    if handler_group == "desktop":
        return desktop_session_recovery.preview(operation_id, home=home, state_dir=state_dir,
                                                proc_root=proc_root)
    if handler_group == "backup":
        return backup_recovery.preview(operation_id, home=home, state_dir=state_dir)
    if handler_group == "restore":
        return restore_recovery.preview(operation_id, home=home, state_dir=state_dir)
    raise OperationRecoveryError("This operation kind has no safe recovery handler")


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
    proc_root: Path = Path("/proc"),
) -> dict[str, object]:
    kind = _kind(operation_id, state_dir=state_dir, home=home)
    handler_group = _HANDLER_GROUP_BY_KIND.get(kind)
    if handler_group == "service":
        return service_recovery.resolve(operation_id, prefix=prefix, state_dir=state_dir,
                                        home=home, confirmed=confirmed, plan_id=plan_id,
                                        source=source, runner=runner)
    if handler_group in {"deploy", "deploy_rollback"}:
        deployment_id = operation_id
        if handler_group == "deploy_rollback":
            detail = operation_journal.inspect_record(str(state_dir), operation_id, home_dir=home)["detail"]
            deployment_id = str(detail).split("rollback of ", 1)[-1].split(" ", 1)[0]
        plan = runit_deployment.preview_rollback(deployment_id, prefix=prefix, state_dir=state_dir,
                home=home, runner=runner,
                recovery_operation_id=(operation_id if handler_group == "deploy_rollback" else None))
        return runit_deployment.apply_rollback(deployment_id, prefix=prefix, state_dir=state_dir,
                home=home, confirmed=confirmed, plan_id=plan_id, runner=runner,
                recovery_operation_id=(operation_id if handler_group == "deploy_rollback" else None))
    if handler_group == "boot":
        return boot_profile_recovery.resolve(operation_id, home=home, state_dir=state_dir,
                                             confirmed=confirmed, plan_id=plan_id)
    if handler_group == "desktop":
        return desktop_session_recovery.resolve(operation_id, home=home, state_dir=state_dir,
                                                confirmed=confirmed, plan_id=plan_id, proc_root=proc_root)
    if handler_group == "backup":
        return backup_recovery.resolve(operation_id, home=home, state_dir=state_dir,
                                       confirmed=confirmed, plan_id=plan_id)
    if handler_group == "restore":
        return restore_recovery.resolve(operation_id, home=home, state_dir=state_dir,
                                        confirmed=confirmed, plan_id=plan_id)
    raise OperationRecoveryError("This operation kind has no safe recovery handler")
