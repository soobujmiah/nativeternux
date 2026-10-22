#!/usr/bin/env python3
"""Private, atomic journal for bounded native Ternuxx operations."""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import time
import uuid

ACTIVE = {"starting", "stopping", "needs_recovery"}
TERMINAL = {"complete", "failed"}
JOURNAL_KINDS = frozenset({
    "desktop.start", "desktop.stop", "boot.enable", "boot.disable",
    "service.start", "service.stop", "service.restart", "service.deploy", "service.deploy.rollback", "recovery.backup.create",
    "recovery.restore.apply", "recovery.restore.rollback",
})


def _root(state_dir: str | os.PathLike[str], home_dir: str | os.PathLike[str] | None = None) -> Path:
    home = Path(home_dir).expanduser().resolve() if home_dir is not None else Path.home().resolve()
    lexical = Path(state_dir).expanduser()
    try:
        relative = lexical.absolute().relative_to(home)
    except ValueError as exc:
        raise ValueError("state path must resolve inside HOME") from exc
    current = home
    for part in relative.parts:
        current = current / part
        try:
            if current.is_symlink():
                raise ValueError("state path contains a symbolic link")
        except OSError:
            pass
    root = lexical.resolve()
    if root == home or home not in root.parents:
        raise ValueError("state path must resolve inside HOME")
    return root / "operations"


def _write(path: Path, record: dict[str, object]) -> None:
    fd, name = tempfile.mkstemp(prefix=".operation.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(record, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, 0o600)
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


def _lock(root: Path) -> Path:
    lock = root / ".journal.lock"
    try:
        lock.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise RuntimeError("operation journal is busy; inspect it and retry") from exc
    return lock


def _read_record(path: Path) -> dict[str, object]:
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
        raise RuntimeError(f"unsafe operation record: {path.name}")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"unreadable journal record: {path.name}") from exc
    required = {"schema_version", "operation_id", "kind", "status", "owner", "provider", "initiating_pid", "detail", "created_at", "updated_at"}
    statuses = ACTIVE | TERMINAL
    allowed_keys = (required, required | {"parent_operation_id"})
    if (not isinstance(record, dict) or set(record) not in allowed_keys or record.get("schema_version") != 1
            or record.get("operation_id") != path.stem or record.get("kind") not in JOURNAL_KINDS
            or record.get("status") not in statuses or record.get("owner") != "ternuxx"
            or record.get("provider") != "native" or type(record.get("initiating_pid")) is not int
            or not isinstance(record.get("detail"), str)):
        raise RuntimeError(f"invalid journal record: {path.name}")
    parent_id = record.get("parent_operation_id")
    if record.get("kind") == "recovery.restore.rollback":
        if not isinstance(parent_id, str) or len(parent_id) != 32 or any(c not in "0123456789abcdef" for c in parent_id):
            raise RuntimeError(f"invalid journal record: {path.name}")
    elif "parent_operation_id" in record:
        raise RuntimeError(f"invalid journal record: {path.name}")
    return record


def list_records(state_dir: str, *, home_dir: str | os.PathLike[str] | None = None) -> list[dict[str, object]]:
    root = _root(state_dir, home_dir)
    try:
        metadata = root.lstat()
    except FileNotFoundError:
        return []
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise RuntimeError("operation journal directory is not private and owned")
    records = []
    for path in sorted(root.glob("*.json")):
        meta = path.lstat()
        if stat.S_ISLNK(meta.st_mode) or not stat.S_ISREG(meta.st_mode) or stat.S_IMODE(meta.st_mode) != 0o600:
            raise RuntimeError(f"unsafe operation record: {path.name}")
        record = _read_record(path)
        public = {key: record[key] for key in ("operation_id", "kind", "status", "owner", "provider", "detail", "created_at", "updated_at")}
        if "parent_operation_id" in record:
            public["parent_operation_id"] = record["parent_operation_id"]
        records.append(public)
    return records


def inspect_record(state_dir: str, operation_id: str, *, home_dir: str | os.PathLike[str] | None = None) -> dict[str, object]:
    if not operation_id.isalnum() or len(operation_id) != 32:
        raise ValueError("invalid operation ID")
    root = _root(state_dir, home_dir)
    path = root / f"{operation_id}.json"
    records = list_records(state_dir, home_dir=home_dir)
    match = next((record for record in records if record["operation_id"] == operation_id), None)
    if match is None:
        raise FileNotFoundError("operation record does not exist")
    return match


def record_path(state_dir: str, operation_id: str, *, home_dir: str | os.PathLike[str] | None = None) -> Path:
    """Return the validated absolute path for one journal record without creating state."""
    if not isinstance(operation_id, str) or not operation_id.isalnum() or len(operation_id) != 32:
        raise ValueError("invalid operation ID")
    return _root(state_dir, home_dir) / f"{operation_id}.json"


def _load_active(root: Path) -> list[dict[str, object]]:
    active = []
    for path in sorted(root.glob("*.json")):
        record = _read_record(path)
        if record.get("status") in ACTIVE:
            active.append(record)
    return active


def _rollback_chain_matches(root: Path, target_id: str, pending: list[dict[str, object]]) -> bool:
    """Allow recovery only when every pending record is in this restore ancestry chain."""
    chain: dict[str, dict[str, object]] = {}
    current_id: str | None = target_id
    allowed = {"recovery.restore.apply", "recovery.restore.rollback"}
    while current_id is not None:
        if current_id in chain:
            return False
        try:
            record = _read_record(root / f"{current_id}.json")
        except (OSError, RuntimeError):
            return False
        if record.get("operation_id") != current_id or record.get("kind") not in allowed:
            return False
        chain[current_id] = record
        parent_id = record.get("parent_operation_id")
        current_id = parent_id if isinstance(parent_id, str) else None
    expected_pending = {op_id for op_id, record in chain.items() if record.get("status") in ACTIVE}
    observed_pending = {str(record.get("operation_id")) for record in pending}
    return expected_pending == observed_pending


def _timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def begin(state_dir: str, kind: str, detail: str, *, home_dir: str | os.PathLike[str] | None = None,
          parent_operation_id: str | None = None) -> str:
    initial_status = {
        "desktop.start": "starting",
        "desktop.stop": "stopping",
        "boot.enable": "starting",
        "boot.disable": "stopping",
        "service.start": "starting",
        "service.stop": "stopping",
        "service.restart": "starting",
        "service.deploy": "starting",
        "service.deploy.rollback": "starting",
        "recovery.backup.create": "starting",
        "recovery.restore.apply": "starting",
        "recovery.restore.rollback": "starting",
    }.get(kind)
    if initial_status is None:
        raise ValueError("unsupported operation kind")
    if len(detail) > 240:
        raise ValueError("operation detail too long")
    if kind == "recovery.restore.rollback":
        if (not isinstance(parent_operation_id, str) or len(parent_operation_id) != 32
                or any(c not in "0123456789abcdef" for c in parent_operation_id)):
            raise ValueError("rollback requires a valid parent operation ID")
    elif parent_operation_id is not None:
        raise ValueError("parent operation ID is allowed only for a recovery rollback")
    root = _root(state_dir, home_dir)
    root.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(root.parent, 0o700)
    root.mkdir(mode=0o700, exist_ok=True)
    os.chmod(root, 0o700)
    lock = _lock(root)
    try:
        parent_record = None
        if kind == "recovery.restore.rollback":
            parent_record = _read_record(root / f"{parent_operation_id}.json")
            if (parent_record.get("kind") not in {"recovery.restore.apply", "recovery.restore.rollback"}
                    or parent_record.get("status") not in {"complete", "needs_recovery"}):
                raise RuntimeError("rollback parent is not an eligible configuration restore")
        pending = _load_active(root)
        if pending:
            authorized_parent = (
                kind == "recovery.restore.rollback" and parent_record is not None
                and parent_record.get("status") in {"complete", "needs_recovery"}
                and _rollback_chain_matches(root, str(parent_operation_id), pending)
            )
            if not authorized_parent:
                raise RuntimeError("an earlier operation is unresolved; Doctor must be reviewed before another mutation")
        operation_id = uuid.uuid4().hex
        now = _timestamp()
        record = {
            "schema_version": 1,
            "operation_id": operation_id,
            "kind": kind,
            "status": initial_status,
            "owner": "ternuxx",
            "provider": "native",
            "initiating_pid": os.getpid(),
            "detail": detail,
            "created_at": now,
            "updated_at": now,
        }
        if parent_operation_id is not None:
            record["parent_operation_id"] = parent_operation_id
        _write(root / f"{operation_id}.json", record)
        return operation_id
    finally:
        lock.rmdir()


def update(state_dir: str, operation_id: str, status: str, detail: str, *, home_dir: str | os.PathLike[str] | None = None) -> None:
    if not operation_id.isalnum() or len(operation_id) != 32:
        raise ValueError("invalid operation ID")
    if status not in ("complete", "failed", "needs_recovery"):
        raise ValueError("invalid terminal operation status")
    if len(detail) > 500:
        raise ValueError("operation detail too long")
    root = _root(state_dir, home_dir)
    path = root / f"{operation_id}.json"
    lock = _lock(root)
    try:
        record = _read_record(path)
        if not isinstance(record, dict) or record.get("operation_id") != operation_id:
            raise RuntimeError("operation record identity mismatch")
        if record.get("status") not in ("starting", "stopping", "needs_recovery"):
            raise RuntimeError("operation record is already terminal")
        record["status"] = status
        record["detail"] = detail
        record["updated_at"] = _timestamp()
        _write(path, record)
    finally:
        lock.rmdir()



def resolve_service_record(
    state_dir: str,
    operation_id: str,
    *,
    expected_kind: str,
    expected_updated_at: str,
    result: str,
    observed_status: str,
    home_dir: str | os.PathLike[str] | None = None,
) -> None:
    """Resolve one needs_recovery SSH service record after an exact state review."""
    if (not operation_id.isalnum() or len(operation_id) != 32
            or expected_kind not in {"service.start", "service.stop", "service.restart"}
            or result not in TERMINAL or observed_status not in {"running", "stopped"}):
        raise ValueError("invalid service recovery resolution")
    target = "stopped" if expected_kind == "service.stop" else "running"
    if (result == "complete") != (observed_status == target):
        raise ValueError("resolution does not match the observed target state")
    root = _root(state_dir, home_dir)
    path = root / f"{operation_id}.json"
    lock = _lock(root)
    try:
        active = _load_active(root)
        if [str(record.get("operation_id")) for record in active] != [operation_id]:
            raise RuntimeError("unrelated or multiple unresolved operations require separate review")
        record = _read_record(path)
        expected_status = "stopping" if expected_kind == "service.stop" else "starting"
        if (record.get("operation_id") != operation_id or record.get("kind") != expected_kind
                or record.get("status") not in {"needs_recovery", expected_status}
                or record.get("updated_at") != expected_updated_at):
            raise RuntimeError("service recovery journal state changed after preview")
        record["status"] = result
        record["detail"] = f"explicit service recovery resolution={result}; observed={observed_status}"
        record["updated_at"] = _timestamp()
        _write(path, record)
    finally:
        lock.rmdir()



def resolve_boot_profile_record(
    state_dir: str,
    operation_id: str,
    *,
    expected_kind: str,
    expected_updated_at: str,
    result: str,
    requested_profile: str,
    observed_profile: str,
    state_matches_target: bool,
    home_dir: str | os.PathLike[str] | None = None,
) -> None:
    """Resolve one interrupted profile journal after allowlisted file inspection."""
    if (not operation_id.isalnum() or len(operation_id) != 32
            or expected_kind not in {"boot.enable", "boot.disable"}
            or result not in TERMINAL
            or requested_profile not in {"cli-only", "native", "proot", "hybrid", "absent"}
            or observed_profile not in {"cli-only", "native", "proot", "hybrid", "absent"}
            or type(state_matches_target) is not bool):
        raise ValueError("invalid boot-profile recovery resolution")
    if ((expected_kind == "boot.disable") != (requested_profile == "absent")
            or ((result == "complete") != state_matches_target)):
        raise ValueError("resolution does not match the observed requested profile state")
    root = _root(state_dir, home_dir)
    path = root / f"{operation_id}.json"
    lock = _lock(root)
    try:
        active = _load_active(root)
        if [str(record.get("operation_id")) for record in active] != [operation_id]:
            raise RuntimeError("unrelated or multiple unresolved operations require separate review")
        record = _read_record(path)
        expected_status = "starting" if expected_kind == "boot.enable" else "stopping"
        if (record.get("operation_id") != operation_id or record.get("kind") != expected_kind
                or record.get("status") not in {"needs_recovery", expected_status}
                or record.get("updated_at") != expected_updated_at):
            raise RuntimeError("boot-profile recovery journal state changed after preview")
        record["status"] = result
        record["detail"] = f"explicit boot-profile recovery resolution={result}; requested={requested_profile}; observed={observed_profile}; matches_target={state_matches_target}"
        record["updated_at"] = _timestamp()
        _write(path, record)
    finally:
        lock.rmdir()


def resolve_desktop_record(
    state_dir: str,
    operation_id: str,
    *,
    expected_kind: str,
    expected_updated_at: str,
    result: str,
    observed_session_status: str,
    home_dir: str | os.PathLike[str] | None = None,
) -> None:
    """Resolve one interrupted desktop operation after process/session inspection."""
    if (not operation_id.isalnum() or len(operation_id) != 32
            or expected_kind not in {"desktop.start", "desktop.stop"}
            or result not in TERMINAL
            or observed_session_status not in {"absent", "failed", "stopped", "running", "stop_incomplete"}):
        raise ValueError("invalid desktop recovery resolution")
    target_match = ((expected_kind == "desktop.start" and observed_session_status == "running")
                    or (expected_kind == "desktop.stop" and observed_session_status == "stopped"))
    if (result == "complete") != target_match:
        raise ValueError("resolution does not match the observed desktop target state")
    root = _root(state_dir, home_dir)
    path = root / f"{operation_id}.json"
    lock = _lock(root)
    try:
        active = _load_active(root)
        if [str(record.get("operation_id")) for record in active] != [operation_id]:
            raise RuntimeError("unrelated or multiple unresolved operations require separate review")
        record = _read_record(path)
        expected_status = "starting" if expected_kind == "desktop.start" else "stopping"
        if (record.get("operation_id") != operation_id or record.get("kind") != expected_kind
                or record.get("status") not in {"needs_recovery", expected_status}
                or record.get("updated_at") != expected_updated_at):
            raise RuntimeError("desktop recovery journal state changed after preview")
        record["status"] = result
        record["detail"] = f"explicit desktop recovery resolution={result}; observed={observed_session_status}"
        record["updated_at"] = _timestamp()
        _write(path, record)
    finally:
        lock.rmdir()


def resolve_backup_record(
    state_dir: str,
    operation_id: str,
    *,
    expected_updated_at: str,
    backup_id: str,
    archive_integrity: str,
    home_dir: str | os.PathLike[str] | None = None,
) -> None:
    """Resolve one interrupted backup-create record after archive verification."""
    if (not operation_id.isalnum() or len(operation_id) != 32 or archive_integrity not in {"valid", "absent"}
            or not isinstance(backup_id, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", backup_id)):
        raise ValueError("invalid backup recovery resolution")
    result = "complete" if archive_integrity == "valid" else "failed"
    root = _root(state_dir, home_dir)
    path = root / f"{operation_id}.json"
    lock = _lock(root)
    try:
        active = _load_active(root)
        if [str(record.get("operation_id")) for record in active] != [operation_id]:
            raise RuntimeError("unrelated or multiple unresolved operations require separate review")
        record = _read_record(path)
        detail = record.get("detail", "")
        name = re.fullmatch(r"create backup ([A-Za-z0-9._-]{1,64})", str(detail))
        if name is None:
            name = re.fullmatch(r"backup ([A-Za-z0-9._-]{1,64}) needs review", str(detail))
        expected_status = "starting" if detail.startswith("create backup ") else "needs_recovery"
        if (record.get("operation_id") != operation_id or record.get("kind") != "recovery.backup.create"
                or record.get("status") not in {expected_status, "needs_recovery"}
                or record.get("updated_at") != expected_updated_at or name is None or name.group(1) != backup_id):
            raise RuntimeError("backup recovery journal state changed after preview")
        record["status"] = result
        record["detail"] = f"explicit backup recovery resolution={result}; backup_id={backup_id}; archive={archive_integrity}"
        record["updated_at"] = _timestamp()
        _write(path, record)
    finally:
        lock.rmdir()


def resolve_restore_record(
    state_dir: str,
    operation_id: str,
    *,
    expected_kind: str,
    expected_updated_at: str,
    result: str,
    observed_outcome: str,
    parent_operation_id: object,
    expected_parent_status: object,
    expected_parent_updated_at: object,
    home_dir: str | os.PathLike[str] | None = None,
) -> None:
    """Resolve an interrupted atomic profile restore from verified file state."""
    if (not re.fullmatch(r"[a-f0-9]{32}", operation_id)
            or expected_kind not in {"recovery.restore.apply", "recovery.restore.rollback"}
            or result not in TERMINAL or observed_outcome not in {"archive_target", "pre_restore_state"}
            or ((result == "complete") != (observed_outcome == "archive_target"))):
        raise ValueError("invalid restore recovery resolution")
    if (expected_kind == "recovery.restore.apply") != (parent_operation_id is None):
        raise ValueError("restore recovery parent identity does not match operation kind")
    root = _root(state_dir, home_dir)
    path = root / f"{operation_id}.json"
    lock = _lock(root)
    try:
        active = _load_active(root)
        record = _read_record(path)
        expected_status = {"starting", "needs_recovery"}
        if (record.get("operation_id") != operation_id or record.get("kind") != expected_kind
                or record.get("status") not in expected_status or record.get("updated_at") != expected_updated_at):
            raise RuntimeError("restore recovery journal state changed after preview")

        ancestry: dict[str, dict[str, object]] = {operation_id: record}
        if expected_kind == "recovery.restore.rollback":
            if (not isinstance(parent_operation_id, str) or not re.fullmatch(r"[a-f0-9]{32}", parent_operation_id)
                    or expected_parent_status not in {"complete", "needs_recovery"}
                    or not isinstance(expected_parent_updated_at, str)):
                raise ValueError("invalid restore recovery parent snapshot")
            current_id: str | None = parent_operation_id
            while current_id is not None:
                if current_id in ancestry:
                    raise RuntimeError("restore recovery parent chain has a cycle")
                parent = _read_record(root / f"{current_id}.json")
                if (parent.get("operation_id") != current_id
                        or parent.get("kind") not in {"recovery.restore.apply", "recovery.restore.rollback"}):
                    raise RuntimeError("restore recovery parent chain is invalid")
                ancestry[current_id] = parent
                next_parent = parent.get("parent_operation_id")
                current_id = next_parent if isinstance(next_parent, str) else None
            direct_parent = ancestry[parent_operation_id]
            if (direct_parent.get("status") != expected_parent_status
                    or direct_parent.get("updated_at") != expected_parent_updated_at):
                raise RuntimeError("restore parent state changed after preview")
        elif any(item.get("status") in ACTIVE for item in active if item.get("operation_id") != operation_id):
            raise RuntimeError("unrelated unresolved operation requires separate review")

        expected_active = {op_id for op_id, item in ancestry.items() if item.get("status") in ACTIVE}
        observed_active = {str(item.get("operation_id")) for item in active}
        if expected_active != observed_active:
            raise RuntimeError("unrelated or changed unresolved operations require separate review")

        record["status"] = result
        record["detail"] = f"explicit restore recovery resolution={result}; observed={observed_outcome}"
        record["updated_at"] = _timestamp()
        _write(path, record)
        if (expected_kind == "recovery.restore.rollback" and result == "complete"
                and expected_parent_status == "needs_recovery"):
            direct_parent = ancestry[str(parent_operation_id)]
            direct_parent["status"] = "failed"
            direct_parent["detail"] = f"compensated by recovery operation {operation_id}"
            direct_parent["updated_at"] = _timestamp()
            _write(root / f"{parent_operation_id}.json", direct_parent)
    finally:
        lock.rmdir()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("begin")
    start.add_argument("state_dir")
    start.add_argument("kind")
    start.add_argument("detail")
    finish = sub.add_parser("update")
    finish.add_argument("state_dir")
    finish.add_argument("operation_id")
    finish.add_argument("status")
    finish.add_argument("detail")
    args = parser.parse_args()
    try:
        if args.command == "begin":
            print(begin(args.state_dir, args.kind, args.detail))
        else:
            update(args.state_dir, args.operation_id, args.status, args.detail)
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"operation journal: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
