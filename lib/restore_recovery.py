#!/usr/bin/env python3
"""Preview-first reconciliation for interrupted native profile restores."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat

import config_recovery
import operation_journal


class RestoreRecoveryError(RuntimeError):
    """A journaled restore outcome is unsafe or ambiguous."""


def _matches(entry: dict[str, object], current_hash: str | None) -> bool:
    return (current_hash is None) if entry.get("present") is False else current_hash == entry.get("sha256")


def _snapshot(operation_id: str, *, home: str | os.PathLike[str],
              state_dir: str | os.PathLike[str]) -> dict[str, object]:
    if not isinstance(operation_id, str) or not re.fullmatch(r"[a-f0-9]{32}", operation_id):
        raise RestoreRecoveryError("Operation ID is invalid")
    try:
        record = operation_journal.inspect_record(str(state_dir), operation_id, home_dir=home)
        kind = record.get("kind")
        if kind not in {"recovery.restore.apply", "recovery.restore.rollback"}:
            raise RestoreRecoveryError("Only a profile restore apply/rollback operation can be resolved")
        initial = "starting"
        if record.get("status") not in {initial, "needs_recovery"}:
            raise RestoreRecoveryError("Restore operation is not awaiting recovery")
        detail = str(record.get("detail", ""))
        match = re.fullmatch(r"restore backup ([A-Za-z0-9._-]{1,64})", detail)
        if match is None:
            match = re.fullmatch(r"restore ([A-Za-z0-9._-]{1,64}) needs review; rollback=(?:none|rollback-[a-f0-9]{32})", detail)
        if match is None:
            raise RestoreRecoveryError("Restore journal does not contain a recognized backup intent")
        backup_id = match.group(1)
        parent_id = record.get("parent_operation_id")
        parent = None
        if kind == "recovery.restore.rollback":
            if (not isinstance(parent_id, str) or not re.fullmatch(r"[a-f0-9]{32}", parent_id)
                    or backup_id != f"rollback-{parent_id}"):
                raise RestoreRecoveryError("Rollback journal does not match its recorded parent")
            parent = operation_journal.inspect_record(str(state_dir), parent_id, home_dir=home)
            if (parent.get("kind") not in {"recovery.restore.apply", "recovery.restore.rollback"}
                    or parent.get("status") not in {"complete", "needs_recovery"}):
                raise RestoreRecoveryError("Rollback parent is not an eligible restore operation")
        elif parent_id is not None:
            raise RestoreRecoveryError("Restore apply unexpectedly has a parent operation")

        _home, source, backups = config_recovery._paths(home, state_dir)
        archive_path, archive = config_recovery._load_archive(backups, backup_id)
        entries = archive.get("entries")
        if not isinstance(entries, list) or len(entries) != 1 or entries[0].get("path") != config_recovery.PROFILE_PATH:
            raise RestoreRecoveryError("Restore archive does not contain exactly the managed profile")
        target_entry = entries[0]
        try:
            profile_metadata = source.lstat()
        except FileNotFoundError:
            profile_metadata = None
        if profile_metadata is not None and (
            stat.S_ISLNK(profile_metadata.st_mode) or not stat.S_ISREG(profile_metadata.st_mode)
            or profile_metadata.st_uid != os.getuid() or stat.S_IMODE(profile_metadata.st_mode) != 0o600
        ):
            raise RestoreRecoveryError("Current profile ownership or mode is unsafe")
        target_hash = config_recovery._current_hash(source)
        if _matches(target_entry, target_hash):
            observed, resolution = "archive_target", "complete"
        else:
            rollback_id = f"rollback-{operation_id}"
            try:
                rollback_path, rollback = config_recovery._load_archive(backups, rollback_id)
            except config_recovery.RecoveryError as exc:
                if "does not exist" in str(exc):
                    raise RestoreRecoveryError("Restore outcome is ambiguous; no verified pre-restore snapshot exists") from exc
                raise RestoreRecoveryError("Pre-restore snapshot exists but cannot be verified") from exc
            original_entries = rollback.get("entries")
            if (not isinstance(original_entries, list) or len(original_entries) != 1
                    or original_entries[0].get("path") != config_recovery.PROFILE_PATH
                    or not _matches(original_entries[0], target_hash)):
                raise RestoreRecoveryError("Current profile matches neither the restore target nor its pre-restore snapshot")
            observed, resolution = "pre_restore_state", "failed"

    except RestoreRecoveryError:
        raise
    except (OSError, ValueError, RuntimeError, config_recovery.RecoveryError) as exc:
        raise RestoreRecoveryError("Restore journal, archive, or profile path is unavailable or unsafe") from exc

    affected_paths = [str(operation_journal.record_path(str(state_dir), operation_id, home_dir=home))]
    if parent is not None and parent.get("status") == "needs_recovery" and resolution == "complete":
        affected_paths.append(str(operation_journal.record_path(str(state_dir), str(parent_id), home_dir=home)))
    core: dict[str, object] = {
        "operation_id": operation_id,
        "record_kind": kind,
        "record_updated_at": record["updated_at"],
        "backup_id": backup_id,
        "archive_integrity_sha256": str(archive["integrity_sha256"]),
        "target_profile_sha256": target_hash,
        "restore_target_sha256": str(target_entry["sha256"]) if target_entry.get("present") else None,
        "observed_outcome": observed,
        "resolution": resolution,
        "parent_operation_id": parent_id,
        "parent_status": parent.get("status") if parent is not None else None,
        "parent_updated_at": parent.get("updated_at") if parent is not None else None,
        "affected_paths": affected_paths,
        "inspected_paths": [str(source), str(archive_path)] + ([str(rollback_path)] if observed == "pre_restore_state" else []),
    }
    plan_id = hashlib.sha256(json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {**core, "plan_id": plan_id, "requires_confirmation": True, "changed": False,
            "read_only": True,
            "impact": "Updates only the listed journal record(s); profile and archive paths are inspected and never changed."}


def preview(operation_id: str, *, home: str | os.PathLike[str],
            state_dir: str | os.PathLike[str]) -> dict[str, object]:
    return _snapshot(operation_id, home=home, state_dir=state_dir)


def resolve(operation_id: str, *, home: str | os.PathLike[str], state_dir: str | os.PathLike[str],
            confirmed: bool, plan_id: str | None) -> dict[str, object]:
    if type(confirmed) is not bool:
        raise RestoreRecoveryError("Explicit confirmation is required")
    current = preview(operation_id, home=home, state_dir=state_dir)
    if not confirmed:
        return current
    if not isinstance(plan_id, str) or plan_id != current["plan_id"]:
        raise RestoreRecoveryError("Restore state changed or the exact preview plan ID is missing")
    verified = preview(operation_id, home=home, state_dir=state_dir)
    if verified["plan_id"] != plan_id:
        raise RestoreRecoveryError("Restore target, archive, parent journal, or operation journal changed after preview")
    operation_journal.resolve_restore_record(
        str(state_dir), operation_id, expected_kind=str(current["record_kind"]),
        expected_updated_at=str(current["record_updated_at"]), result=str(current["resolution"]),
        observed_outcome=str(current["observed_outcome"]), parent_operation_id=current["parent_operation_id"],
        expected_parent_status=current["parent_status"], expected_parent_updated_at=current["parent_updated_at"],
        home_dir=home,
    )
    return {"operation_id": operation_id, "resolution": current["resolution"],
            "observed_outcome": current["observed_outcome"], "changed": True, "read_only": False,
            "affected_paths": current["affected_paths"], "profile_file_changed": False,
            "archive_changed": False}
