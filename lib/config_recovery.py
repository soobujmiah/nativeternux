#!/usr/bin/env python3
"""Allowlisted, integrity-checked Ternuxx configuration backup and restore."""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Any

import operation_journal

ARCHIVE_FORMAT = "ternuxx-config-backup"
SCHEMA_VERSION = 1
SOFTWARE_VERSION = "0.1.0"
MAX_ARCHIVE_BYTES = 512 * 1024
MAX_ENTRY_BYTES = 64 * 1024
BACKUP_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
PROFILE_PATH = "state/boot/profile.json"
EXCLUDED_PATHS = [
    "External storage and unrelated Termux application state",
    "shared/external storage",
    "SSH host/client private keys and credentials",
    "managed OpenSSH configuration",
    "desktop sessions, logs, PID/socket records, and operation journals",
    "continuity checkpoints and reboot nonces",
    "Termux:Boot scripts and unrelated user files",
]


class RecoveryError(ValueError):
    """A recovery archive or target failed a safety/integrity check."""


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _paths(home: str | os.PathLike[str], state_dir: str | os.PathLike[str]) -> tuple[Path, Path, Path]:
    home_path = Path(home).expanduser().resolve(strict=True)
    state_lexical = Path(state_dir).expanduser()
    try:
        state_abs = state_lexical.absolute()
        rel = state_abs.relative_to(home_path)
    except ValueError as exc:
        raise RecoveryError("Ternuxx state path must be inside HOME") from exc
    current = home_path
    for part in rel.parts:
        current = current / part
        try:
            if stat.S_ISLNK(current.lstat().st_mode):
                raise RecoveryError("Ternuxx state path contains a symbolic link")
        except FileNotFoundError:
            pass
    state = state_lexical.resolve(strict=False)
    if state == home_path or home_path not in state.parents:
        raise RecoveryError("Ternuxx state path must resolve inside HOME")
    source = state / "boot" / "profile.json"
    backups = state / "backups"
    for path in (state / "boot", source, backups):
        try:
            if stat.S_ISLNK(path.lstat().st_mode):
                raise RecoveryError("managed recovery path contains a symbolic link")
        except FileNotFoundError:
            pass
    return home_path, source, backups


def _profile_valid(data: bytes) -> None:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise RecoveryError("boot profile is not valid JSON") from exc
    if (not isinstance(value, dict) or set(value) != {"schema_version", "owner", "provider", "profile"}
            or value.get("schema_version") != 1 or value.get("owner") != "ternuxx"
            or value.get("provider") != "native"
            or value.get("profile") not in {"cli-only", "native"}):
        raise RecoveryError("boot profile does not match the supported Ternuxx schema")


def _target_entries(source: Path) -> list[dict[str, Any]]:
    try:
        metadata = source.lstat()
    except FileNotFoundError:
        empty_hash = _hash(b"")
        return [{"path": PROFILE_PATH, "present": False, "mode": 0o600, "size": 0,
                 "sha256": empty_hash, "data_b64": ""}]
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise RecoveryError("managed profile path is not a regular file")
    if metadata.st_size > MAX_ENTRY_BYTES:
        raise RecoveryError("managed profile exceeds the backup size limit")
    data = source.read_bytes()
    _profile_valid(data)
    return [{"path": PROFILE_PATH, "present": True, "mode": 0o600, "size": len(data), "sha256": _hash(data),
             "data_b64": base64.b64encode(data).decode("ascii")}]


def _plan_id(backup_id: str, entries: list[dict[str, Any]]) -> str:
    summary = [{key: entry[key] for key in ("path", "present", "mode", "size", "sha256")} for entry in entries]
    return _hash(_canonical({"backup_id": backup_id, "entries": summary}))


def _archive_payload(backup_id: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "format": ARCHIVE_FORMAT,
        "schema_version": SCHEMA_VERSION,
        "software_version": SOFTWARE_VERSION,
        "backup_id": backup_id,
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "entries": entries,
        "excluded_paths": EXCLUDED_PATHS,
    }
    manifest["integrity_sha256"] = _hash(_canonical(manifest))
    return manifest


def _write_atomic(path: Path, data: bytes, *, mode: int = 0o600) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    fd, name = tempfile.mkstemp(prefix=".ternuxx-recovery-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
        try:
            dfd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
        except OSError:
            pass
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass


def _save_archive(path: Path, backup_id: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
    payload = _archive_payload(backup_id, entries)
    raw = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    if len(raw) > MAX_ARCHIVE_BYTES:
        raise RecoveryError("backup archive exceeds the size limit")
    _write_atomic(path, raw)
    return payload


def _load_archive(backups: Path, backup_id: str) -> tuple[Path, dict[str, Any]]:
    if not BACKUP_ID_RE.fullmatch(backup_id):
        raise RecoveryError("backup ID is malformed")
    path = backups / f"{backup_id}.json"
    try:
        root_mode = stat.S_IMODE(backups.lstat().st_mode)
        if stat.S_ISLNK(backups.lstat().st_mode) or not stat.S_ISDIR(backups.lstat().st_mode) or root_mode != 0o700:
            raise RecoveryError("backup directory is not private and owned")
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
            raise RecoveryError("backup archive is not a private regular file")
        if metadata.st_size > MAX_ARCHIVE_BYTES:
            raise RecoveryError("backup archive exceeds the size limit")
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RecoveryError("backup archive does not exist") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecoveryError("backup archive is unreadable or invalid JSON") from exc
    expected_fields = {"format", "schema_version", "software_version", "backup_id", "created_at_utc", "entries", "excluded_paths", "integrity_sha256"}
    if not isinstance(payload, dict) or set(payload) != expected_fields or payload.get("format") != ARCHIVE_FORMAT:
        raise RecoveryError("backup format or fields are unknown")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise RecoveryError("backup schema is unknown or newer")
    if payload.get("backup_id") != backup_id:
        raise RecoveryError("backup identity does not match its filename")
    if not isinstance(payload.get("created_at_utc"), str):
        raise RecoveryError("backup timestamp is malformed")
    try:
        dt.datetime.fromisoformat(payload["created_at_utc"])
    except ValueError as exc:
        raise RecoveryError("backup timestamp is malformed") from exc
    if payload.get("excluded_paths") != EXCLUDED_PATHS:
        raise RecoveryError("backup exclusion manifest is unknown")
    integrity = payload.get("integrity_sha256")
    unsigned = dict(payload)
    unsigned.pop("integrity_sha256", None)
    if not isinstance(integrity, str) or _hash(_canonical(unsigned)) != integrity:
        raise RecoveryError("backup integrity check failed")
    entries = payload.get("entries")
    if not isinstance(entries, list) or len(entries) > 8:
        raise RecoveryError("backup entries are malformed")
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "present", "mode", "size", "sha256", "data_b64"}:
            raise RecoveryError("backup entry metadata is malformed")
        relative = entry["path"]
        if relative != PROFILE_PATH or relative in seen:
            raise RecoveryError("backup contains an unowned or duplicate path")
        seen.add(relative)
        if type(entry["present"]) is not bool or entry["mode"] != 0o600 or type(entry["size"]) is not int or not 0 <= entry["size"] <= MAX_ENTRY_BYTES:
            raise RecoveryError("backup entry mode, presence, or size is invalid")
        try:
            data = base64.b64decode(entry["data_b64"], validate=True)
        except (ValueError, TypeError) as exc:
            raise RecoveryError("backup entry data is not valid base64") from exc
        if len(data) != entry["size"] or _hash(data) != entry["sha256"]:
            raise RecoveryError("backup entry checksum or size does not match")
        if entry["present"]:
            _profile_valid(data)
        elif data or entry["size"] != 0:
            raise RecoveryError("absent profile entry must not contain file data")
    version = payload.get("software_version")
    if not isinstance(version, str) or not re.fullmatch(r"0\.1\.\d+", version):
        raise RecoveryError("backup software version is not compatible")
    return path, payload


def _current_hash(source: Path) -> str | None:
    try:
        metadata = source.lstat()
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise RecoveryError("restore target is not a regular Ternuxx-owned file")
    if metadata.st_size > MAX_ENTRY_BYTES:
        raise RecoveryError("restore target exceeds the size limit")
    data = source.read_bytes()
    _profile_valid(data)
    return _hash(data)

def _restore_plan_id(backup_id: str, integrity: str, destination_hash: str | None) -> str:
    return _hash(_canonical({"backup_id": backup_id, "archive_integrity": integrity,
                             "destination_sha256": destination_hash, "target": PROFILE_PATH}))


def _validate_name(name: str) -> str:
    if not isinstance(name, str) or not BACKUP_ID_RE.fullmatch(name):
        raise RecoveryError("backup name must use 1-64 letters, numbers, dot, dash, or underscore")
    return name


def list_backups(*, home: str, state_dir: str) -> dict[str, Any]:
    _home, _source, backups = _paths(home, state_dir)
    if not backups.exists():
        return {"backups": [], "read_only": True}
    if backups.is_symlink() or not backups.is_dir() or stat.S_IMODE(backups.stat().st_mode) != 0o700:
        raise RecoveryError("backup directory is not private and owned")
    rows = []
    for path in sorted(backups.glob("*.json")):
        if not BACKUP_ID_RE.fullmatch(path.stem):
            continue
        try:
            _path, payload = _load_archive(backups, path.stem)
            rows.append({"backup_id": path.stem, "integrity": "valid", "created_at_utc": payload["created_at_utc"],
                         "entry_count": len(payload["entries"])})
        except RecoveryError as exc:
            rows.append({"backup_id": path.stem, "integrity": "invalid", "error": str(exc)})
    return {"backups": rows, "read_only": True}


def inspect_backup(*, home: str, state_dir: str, backup_id: str) -> dict[str, Any]:
    _home, _source, backups = _paths(home, state_dir)
    _path, payload = _load_archive(backups, backup_id)
    return {"backup_id": backup_id, "integrity": "valid", "schema_version": payload["schema_version"],
            "software_version": payload["software_version"], "created_at_utc": payload["created_at_utc"],
            "entries": [{"path": e["path"], "present": e["present"], "size": e["size"], "sha256": e["sha256"], "mode": "0600"}
                        for e in payload["entries"]],
            "excluded_paths": payload["excluded_paths"], "read_only": True}


def create_backup(*, home: str, state_dir: str, name: str, confirmed: bool = False,
                  plan_id: str | None = None) -> dict[str, Any]:
    name = _validate_name(name)
    _home, source, backups = _paths(home, state_dir)
    entries = _target_entries(source)
    current_plan = _plan_id(name, entries)
    destination = backups / f"{name}.json"
    if not confirmed:
        return {"action": "preview", "backup_id": name, "plan_id": current_plan,
                "destination": str(destination), "entries": [{"path": e["path"], "present": e["present"], "size": e["size"], "sha256": e["sha256"]} for e in entries],
                "excluded_paths": EXCLUDED_PATHS, "read_only": True}
    if plan_id != current_plan:
        raise RecoveryError("backup contents changed or preview ID is missing; create and review a new preview")
    if destination.exists() or destination.is_symlink():
        raise RecoveryError("backup name already exists; choose a new name")
    operation_id = operation_journal.begin(state_dir, "recovery.backup.create", f"create backup {name}", home_dir=home)
    try:
        payload = _save_archive(destination, name, entries)
        _path, verified = _load_archive(backups, name)
        if verified.get("integrity_sha256") != payload["integrity_sha256"]:
            raise RecoveryError("written backup failed verification")
        operation_journal.update(state_dir, operation_id, "complete", f"backup {name} verified", home_dir=home)
    except Exception:
        try:
            operation_journal.update(state_dir, operation_id, "needs_recovery", f"backup {name} needs review", home_dir=home)
        except Exception:
            pass
        raise
    return {"action": "created", "backup_id": name, "integrity": "valid",
            "destination": str(destination), "entry_count": len(entries), "operation_id": operation_id}


def restore_preview(*, home: str, state_dir: str, backup_id: str) -> dict[str, Any]:
    _home, source, backups = _paths(home, state_dir)
    _path, payload = _load_archive(backups, backup_id)
    destination_hash = _current_hash(source)
    plan_id = _restore_plan_id(backup_id, payload["integrity_sha256"], destination_hash)
    entries = []
    for entry in payload["entries"]:
        action = ("remove" if destination_hash else "no_change") if not entry["present"] else ("replace" if destination_hash else "add")
        entries.append({"path": entry["path"], "action": action,
                        "current_sha256": destination_hash, "backup_sha256": entry["sha256"] if entry["present"] else None,
                        "conflict": False})
    return {"action": "restore_preview", "backup_id": backup_id, "integrity": "valid",
            "plan_id": plan_id, "entries": entries, "rollback_required": True, "read_only": True}


def _rollback_snapshot(source: Path, backups: Path, operation_id: str) -> str:
    rollback_id = f"rollback-{operation_id}"
    try:
        metadata = source.lstat()
    except FileNotFoundError:
        entry = {"path": PROFILE_PATH, "present": False, "mode": 0o600, "size": 0,
                 "sha256": _hash(b""), "data_b64": ""}
        _save_archive(backups / f"{rollback_id}.json", rollback_id, [entry])
        return rollback_id
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise RecoveryError("restore target cannot be snapshotted safely")
    if metadata.st_size > MAX_ENTRY_BYTES:
        raise RecoveryError("restore target exceeds rollback size limit")
    data = source.read_bytes()
    entry = {"path": PROFILE_PATH, "present": True, "mode": 0o600, "size": len(data), "sha256": _hash(data),
             "data_b64": base64.b64encode(data).decode("ascii")}
    _save_archive(backups / f"{rollback_id}.json", rollback_id, [entry])
    return rollback_id

def rollback_preview(*, home: str, state_dir: str, operation_id: str) -> dict[str, Any]:
    """Preview rollback of a completed or explicitly unresolved profile restore."""
    try:
        record = operation_journal.inspect_record(state_dir, operation_id, home_dir=home)
    except FileNotFoundError as exc:
        raise RecoveryError("restore operation record was not found") from exc
    if record.get("kind") not in {"recovery.restore.apply", "recovery.restore.rollback"}:
        raise RecoveryError("only a recorded profile restore or rollback can be rolled back")
    if record.get("status") not in {"complete", "needs_recovery"}:
        raise RecoveryError("restore operation must be complete or marked needs_recovery before rollback")
    backup_id = f"rollback-{operation_id}"
    try:
        preview = restore_preview(home=home, state_dir=state_dir, backup_id=backup_id)
    except FileNotFoundError as exc:
        raise RecoveryError("rollback snapshot is missing") from exc
    preview.update({"action": "rollback_preview", "operation_id": operation_id,
                    "rollback_backup_id": backup_id})
    return preview


def restore_backup(*, home: str, state_dir: str, backup_id: str, confirmed: bool = False,
                   plan_id: str | None = None, _operation_kind: str = "recovery.restore.apply",
                   _parent_operation_id: str | None = None) -> dict[str, Any]:
    if _operation_kind not in {"recovery.restore.apply", "recovery.restore.rollback"}:
        raise RecoveryError("unsupported restore journal operation kind")
    if (_operation_kind == "recovery.restore.rollback") != (_parent_operation_id is not None):
        raise RecoveryError("recovery rollback requires exactly one parent operation")
    preview = restore_preview(home=home, state_dir=state_dir, backup_id=backup_id)
    if not confirmed:
        return preview
    if plan_id != preview["plan_id"]:
        raise RecoveryError("restore target changed or preview ID is missing; review a new restore preview")
    _home_path, source, backups = _paths(home, state_dir)
    _archive_path, payload = _load_archive(backups, backup_id)
    latest_destination_hash = _current_hash(source)
    if _restore_plan_id(backup_id, payload["integrity_sha256"], latest_destination_hash) != plan_id:
        raise RecoveryError("backup or restore target changed after preview; review a new preview")
    operation_id = operation_journal.begin(state_dir, _operation_kind, f"restore backup {backup_id}",
                                           home_dir=home, parent_operation_id=_parent_operation_id)
    rollback_id = None
    try:
        rollback_id = _rollback_snapshot(source, backups, operation_id)
        entries = payload["entries"]
        if entries:
            entry = entries[0]
            if entry["present"]:
                data = base64.b64decode(entry["data_b64"], validate=True)
                _profile_valid(data)
                source.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                os.chmod(source.parent, 0o700)
                _write_atomic(source, data, mode=0o600)
                _profile_valid(source.read_bytes())
            elif source.exists():
                source.unlink()
                try:
                    dfd = os.open(source.parent, os.O_RDONLY)
                    try:
                        os.fsync(dfd)
                    finally:
                        os.close(dfd)
                except OSError:
                    pass
        operation_journal.update(state_dir, operation_id, "complete", f"restored {backup_id}; rollback={rollback_id or 'none'}", home_dir=home)
    except Exception:
        try:
            operation_journal.update(state_dir, operation_id, "needs_recovery", f"restore {backup_id} needs review; rollback={rollback_id or 'none'}", home_dir=home)
        except Exception:
            pass
        raise
    return {"action": "restored", "backup_id": backup_id, "operation_id": operation_id,
            "rollback_backup_id": rollback_id, "affected_paths": [e["path"] for e in payload["entries"]],
            "result": "complete", "manual_steps": []}

def rollback_restore(*, home: str, state_dir: str, operation_id: str, confirmed: bool = False,
                     plan_id: str | None = None) -> dict[str, Any]:
    preview = rollback_preview(home=home, state_dir=state_dir, operation_id=operation_id)
    if not confirmed:
        return preview
    if plan_id != preview["plan_id"]:
        raise RecoveryError("rollback target changed or preview ID is missing; review a new preview")
    result = restore_backup(
        home=home, state_dir=state_dir, backup_id=str(preview["rollback_backup_id"]),
        confirmed=True, plan_id=plan_id, _operation_kind="recovery.restore.rollback",
        _parent_operation_id=operation_id,
    )
    parent = operation_journal.inspect_record(state_dir, operation_id, home_dir=home)
    if parent.get("status") == "needs_recovery":
        operation_journal.update(state_dir, operation_id, "failed",
                                 f"compensated by recovery operation {result['operation_id']}", home_dir=home)
    result.update({"action": "rolled_back", "rollback_of_operation": operation_id})
    return result
