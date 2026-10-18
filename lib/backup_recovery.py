#!/usr/bin/env python3
"""Preview-first reconciliation for interrupted native backup creation."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re

import config_recovery
import operation_journal


class BackupRecoveryError(RuntimeError):
    """An interrupted backup cannot be safely reconciled."""


def preview(operation_id: str, *, home: str | os.PathLike[str],
            state_dir: str | os.PathLike[str]) -> dict[str, object]:
    if not isinstance(operation_id, str) or not re.fullmatch(r"[a-f0-9]{32}", operation_id):
        raise BackupRecoveryError("Operation ID is invalid")
    try:
        record = operation_journal.inspect_record(str(state_dir), operation_id, home_dir=home)
        if record.get("kind") != "recovery.backup.create" or record.get("status") not in {"starting", "needs_recovery"}:
            raise BackupRecoveryError("Only an interrupted backup-create operation can be resolved")
        detail = str(record.get("detail", ""))
        match = re.fullmatch(r"create backup ([A-Za-z0-9._-]{1,64})", detail)
        if match is None:
            match = re.fullmatch(r"backup ([A-Za-z0-9._-]{1,64}) needs review", detail)
        if not match:
            raise BackupRecoveryError("Backup journal does not contain a valid backup name")
        backup_id = config_recovery._validate_name(match.group(1))
        _home, _source, backups = config_recovery._paths(home, state_dir)
        archive_path = backups / f"{backup_id}.json"
        try:
            _verified_path, archive = config_recovery._load_archive(backups, backup_id)
        except config_recovery.RecoveryError as exc:
            if "does not exist" in str(exc):
                resolution, integrity, archive_sha256 = "failed", "absent", None
            else:
                raise BackupRecoveryError("Backup archive exists but cannot be verified; preserve the unresolved record") from exc
        else:
            resolution, integrity = "complete", "valid"
            archive_sha256 = str(archive["integrity_sha256"])
    except BackupRecoveryError:
        raise
    except (OSError, ValueError, RuntimeError, config_recovery.RecoveryError) as exc:
        raise BackupRecoveryError("Backup operation or archive path is unavailable or unsafe") from exc
    core: dict[str, object] = {
        "operation_id": operation_id,
        "record_kind": record["kind"],
        "record_updated_at": record["updated_at"],
        "backup_id": backup_id,
        "archive_path": str(archive_path),
        "archive_integrity": integrity,
        "archive_sha256": archive_sha256,
        "affected_paths": [str(operation_journal.record_path(str(state_dir), operation_id, home_dir=home))],
        "resolution": resolution,
    }
    plan_id = hashlib.sha256(json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {**core, "plan_id": plan_id, "requires_confirmation": True, "changed": False,
            "read_only": True,
            "impact": "Updates only the listed journal path; the backup archive is inspected but never changed."}


def resolve(operation_id: str, *, home: str | os.PathLike[str], state_dir: str | os.PathLike[str],
            confirmed: bool, plan_id: str | None) -> dict[str, object]:
    if type(confirmed) is not bool:
        raise BackupRecoveryError("Explicit confirmation is required")
    current = preview(operation_id, home=home, state_dir=state_dir)
    if not confirmed:
        return current
    if not isinstance(plan_id, str) or plan_id != current["plan_id"]:
        raise BackupRecoveryError("Recovery state changed or the exact preview plan ID is missing")
    verified = preview(operation_id, home=home, state_dir=state_dir)
    if verified["plan_id"] != plan_id:
        raise BackupRecoveryError("Backup archive or journal changed after preview")
    operation_journal.resolve_backup_record(
        str(state_dir), operation_id, expected_updated_at=str(current["record_updated_at"]),
        backup_id=str(current["backup_id"]), archive_integrity=str(current["archive_integrity"]), home_dir=home,
    )
    return {"operation_id": operation_id, "backup_id": current["backup_id"],
            "resolution": current["resolution"], "changed": True, "read_only": False,
            "affected_paths": current["affected_paths"], "archive_changed": False}
