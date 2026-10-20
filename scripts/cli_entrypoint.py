#!/usr/bin/env python3
"""Preview-first installer and rollback for the native Ternuxx CLI entrypoint."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/tx-installed"
MAX_SNAPSHOT = 1024 * 1024


class InstallError(Exception):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _plan_id(value: object) -> str:
    return _sha(_canonical(value))


def _atomic_write(path: Path, data: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as stream:
            fd = -1
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = ""
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if fd >= 0:
            os.close(fd)
        if temporary:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def _target(prefix: str | os.PathLike[str]) -> Path:
    root = Path(prefix)
    if not root.is_absolute() or root.is_symlink():
        raise InstallError("Termux PREFIX must be an absolute non-symlink path")
    parent = root / "bin"
    if parent.is_symlink() or not parent.is_dir():
        raise InstallError("Termux PREFIX/bin must be an existing real directory")
    return parent / "tx"


def preview(*, prefix: str | os.PathLike[str]) -> dict[str, object]:
    target = _target(prefix)
    try:
        desired = SOURCE.read_bytes()
        syntax = subprocess.run([shutil.which("bash") or "bash", "-n", str(SOURCE)],
                                capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InstallError("source validation could not run") from exc
    if syntax.returncode != 0:
        raise InstallError("installed entrypoint source failed bash syntax validation")
    try:
        metadata = target.lstat()
    except FileNotFoundError:
        original = None
        mode = None
    else:
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid():
            raise InstallError("installed CLI target is not a regular file owned by this user")
        if metadata.st_size > MAX_SNAPSHOT:
            raise InstallError("installed CLI target exceeds the backup size limit")
        original = target.read_bytes()
        mode = stat.S_IMODE(metadata.st_mode)
    record: dict[str, object] = {
        "target": str(target),
        "source": str(SOURCE),
        "source_sha256": _sha(desired),
        "installed_sha256": _sha(original) if original is not None else None,
        "target_mode": mode,
        "changed": original != desired,
    }
    record["plan_id"] = _plan_id(record)
    record["read_only"] = True
    record["requires_confirmation"] = record["changed"]
    record["diff"] = {
        "old": original.decode("utf-8", "replace").splitlines() if original is not None else [],
        "new": desired.decode("utf-8").splitlines(),
    }
    record["impact"] = "Atomically replaces only PREFIX/bin/tx. Keeps the existing nativeternux executable and libraries untouched; rollback restores the exact prior entrypoint."
    return record


def _snapshot_root(home: str | os.PathLike[str], *, create: bool) -> Path:
    root = Path(home) / ".local/share/ternuxx/cli-entrypoint-recovery"
    if root.exists() or root.is_symlink():
        metadata = root.lstat()
        if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid():
            raise InstallError("CLI recovery path is not a safe owned directory")
        if stat.S_IMODE(metadata.st_mode) & 0o077:
            raise InstallError("CLI recovery directory permissions are not private")
    elif create:
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(root, 0o700)
    return root


def apply(*, prefix: str | os.PathLike[str], home: str | os.PathLike[str],
          confirmed: bool, plan_id: str | None) -> dict[str, object]:
    if confirmed is not True:
        raise InstallError("explicit confirmation is required")
    plan = preview(prefix=prefix)
    if not plan["requires_confirmation"] or plan["plan_id"] != plan_id:
        raise InstallError("entrypoint changed after preview or exact plan ID is missing")
    target = Path(str(plan["target"]))
    try:
        metadata = target.lstat()
    except FileNotFoundError:
        if plan["installed_sha256"] is not None:
            raise InstallError("installed CLI target changed after preview")
        original = None
        old_mode = None
    else:
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid():
            raise InstallError("installed CLI target changed after preview")
        original = target.read_bytes()
        old_mode = stat.S_IMODE(metadata.st_mode)
        if _sha(original) != plan["installed_sha256"]:
            raise InstallError("installed CLI target changed after preview")
    desired = SOURCE.read_bytes()
    operation_id = uuid.uuid4().hex
    snapshot = {
        "schema_version": 1,
        "operation_id": operation_id,
        "target": str(target),
        "original_b64": base64.b64encode(original).decode("ascii") if original is not None else None,
        "original_mode": old_mode,
        "original_sha256": _sha(original) if original is not None else None,
        "installed_sha256": _sha(desired),
    }
    if len(_canonical(snapshot)) > MAX_SNAPSHOT * 2:
        raise InstallError("entrypoint recovery snapshot exceeds its size limit")
    snapshot_path = _snapshot_root(home, create=True) / f"{operation_id}.json"
    _atomic_write(snapshot_path, _canonical(snapshot) + b"\n", 0o600)
    try:
        _atomic_write(target, desired, 0o755)
        if _sha(target.read_bytes()) != snapshot["installed_sha256"]:
            raise InstallError("installed CLI entrypoint did not verify")
    except Exception as exc:
        try:
            if original is None:
                target.unlink(missing_ok=True)
            else:
                _atomic_write(target, original, int(old_mode))
        except Exception as restore_exc:
            raise InstallError(f"install failed; automatic restore needs recovery; operation={operation_id}") from restore_exc
        raise InstallError(f"install failed; previous entrypoint restored; operation={operation_id}") from exc
    return {"status": "installed", "operation_id": operation_id,
            "target": str(target), "installed_sha256": _sha(desired),
            "rollback_available": True, "read_only": False}


def rollback_preview(*, operation_id: str, prefix: str | os.PathLike[str],
                      home: str | os.PathLike[str]) -> dict[str, object]:
    path = _snapshot_root(home, create=False) / f"{operation_id}.json"
    try:
        metadata = path.lstat()
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) != 0o600 or metadata.st_size > MAX_SNAPSHOT * 2):
            raise InstallError("CLI recovery snapshot identity is unsafe")
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        raise InstallError("CLI recovery snapshot is unavailable or invalid") from exc
    target = _target(prefix)
    if record.get("schema_version") != 1 or record.get("operation_id") != operation_id or record.get("target") != str(target):
        raise InstallError("CLI recovery snapshot identity does not match target")
    try:
        target_info = target.lstat()
    except OSError as exc:
        raise InstallError("installed CLI target is unavailable") from exc
    if not stat.S_ISREG(target_info.st_mode) or target_info.st_uid != os.getuid():
        raise InstallError("installed CLI target is not a safe regular file")
    current = target.read_bytes()
    if _sha(current) != record.get("installed_sha256"):
        raise InstallError("installed CLI changed since deployment; rollback refused")
    original = base64.b64decode(record["original_b64"], validate=True) if record["original_b64"] is not None else None
    if original is not None and _sha(original) != record.get("original_sha256"):
        raise InstallError("CLI recovery snapshot checksum is invalid")
    core = {"operation_id": operation_id, "target": str(target),
            "current_sha256": _sha(current),
            "restore_sha256": _sha(original) if original is not None else None}
    return {**core, "plan_id": _plan_id(core), "read_only": True,
            "requires_confirmation": True,
            "diff": {"old": current.decode("utf-8", "replace").splitlines(),
                     "new": original.decode("utf-8", "replace").splitlines() if original is not None else []}}


def rollback(*, operation_id: str, prefix: str | os.PathLike[str], home: str | os.PathLike[str],
             confirmed: bool, plan_id: str | None) -> dict[str, object]:
    if confirmed is not True:
        raise InstallError("explicit rollback confirmation is required")
    plan = rollback_preview(operation_id=operation_id, prefix=prefix, home=home)
    if plan["plan_id"] != plan_id:
        raise InstallError("CLI rollback plan changed or exact plan ID is missing")
    path = _snapshot_root(home, create=False) / f"{operation_id}.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    target = Path(str(plan["target"]))
    original = base64.b64decode(record["original_b64"], validate=True) if record["original_b64"] is not None else None
    if original is None:
        target.unlink()
    else:
        _atomic_write(target, original, int(record["original_mode"]))
    return {"status": "rolled_back", "operation_id": operation_id,
            "target": str(target), "restored_sha256": _sha(original) if original is not None else None,
            "read_only": False, "snapshot_retained": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preview", "apply", "rollback-preview", "rollback"))
    parser.add_argument("--prefix", default=os.environ.get("PREFIX", "/data/data/com.termux/files/usr"))
    parser.add_argument("--home", default=os.environ.get("HOME", ""))
    parser.add_argument("--operation-id")
    parser.add_argument("--plan-id")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()
    try:
        if args.action == "preview":
            result = preview(prefix=args.prefix)
        elif args.action == "apply":
            result = apply(prefix=args.prefix, home=args.home, confirmed=args.yes, plan_id=args.plan_id)
        elif args.action == "rollback-preview":
            if not args.operation_id:
                raise InstallError("--operation-id is required")
            result = rollback_preview(operation_id=args.operation_id, prefix=args.prefix, home=args.home)
        else:
            if not args.operation_id:
                raise InstallError("--operation-id is required")
            result = rollback(operation_id=args.operation_id, prefix=args.prefix, home=args.home,
                              confirmed=args.yes, plan_id=args.plan_id)
        print(json.dumps({"ok": True, "data": result}, sort_keys=True))
        return 0
    except InstallError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
