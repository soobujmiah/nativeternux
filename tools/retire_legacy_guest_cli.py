#!/usr/bin/env python3
"""Preview, retire, and exactly restore the old Debian guest Ternux companion."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import time

TARGET_RELATIVE = Path("usr/local/bin/ternux")
_BACKUP_ID = re.compile(r"^plan-[0-9a-f]{64}$")


class RetirementError(ValueError):
    pass


def _check_private_dir(path: Path, *, create: bool = False) -> Path:
    path = path.absolute()
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise RetirementError("backup state path contains a symlink")
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077):
        raise RetirementError("backup state directory ownership or mode is unsafe")
    return path


def _rootfs_identity(rootfs: Path) -> tuple[Path, os.stat_result]:
    rootfs = rootfs.absolute()
    current = Path(rootfs.anchor)
    for part in rootfs.parts[1:]:
        current = current / part
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise RetirementError("rootfs path contains a symlink")
    info = rootfs.lstat()
    if not stat.S_ISDIR(info.st_mode):
        raise RetirementError("Debian rootfs is not a directory")
    return rootfs, info


def _target_and_parent(rootfs: Path) -> tuple[Path, os.stat_result, os.stat_result]:
    rootfs, root_info = _rootfs_identity(rootfs)
    parent = rootfs
    parent_info = root_info
    for component in TARGET_RELATIVE.parts[:-1]:
        parent = parent / component
        parent_info = parent.lstat()
        if stat.S_ISLNK(parent_info.st_mode) or not stat.S_ISDIR(parent_info.st_mode):
            raise RetirementError("legacy CLI parent path contains an unsafe component")
        if parent_info.st_dev != root_info.st_dev:
            raise RetirementError("legacy CLI parent path crosses a filesystem boundary")
    return parent / TARGET_RELATIVE.name, root_info, parent_info


def _read_target(rootfs: Path) -> tuple[Path, os.stat_result, bytes, str]:
    path, root_info, parent_info = _target_and_parent(rootfs)
    parent = path.parent
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode)
            or info.st_nlink != 1 or info.st_uid != os.getuid()):
        raise RetirementError("legacy CLI target is not the expected single-link owned regular file")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(fd)
        if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
            raise RetirementError("legacy CLI changed while it was being inspected")
        chunks = []
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
    finally:
        os.close(fd)
    data = b"".join(chunks)
    if (len(data) > 1024 * 1024 or b"ternux guest companion" not in data
            or b"TERNUX_GUEST_VERSION=" not in data):
        raise RetirementError("target contents do not identify the expected legacy guest companion")
    if (info.st_dev != root_info.st_dev or parent_info.st_dev != root_info.st_dev):
        raise RetirementError("legacy CLI is outside the expected Debian rootfs filesystem")
    return path, info, data, hashlib.sha256(data).hexdigest()


def _backup_root(state_dir: Path, rootfs_info: os.stat_result, *, create: bool = False) -> Path:
    state = _check_private_dir(state_dir)
    if state.stat().st_dev != rootfs_info.st_dev:
        raise RetirementError("backup state and Debian rootfs must share a filesystem for atomic retirement")
    backup_root = state / "proot" / "legacy-cli-backups"
    parent = backup_root.parent
    if parent.exists() or parent.is_symlink():
        _check_private_dir(parent)
    elif create:
        parent.mkdir(mode=0o700, parents=True)
    if backup_root.exists() or backup_root.is_symlink():
        _check_private_dir(backup_root)
    elif create:
        backup_root.mkdir(mode=0o700)
    if create and backup_root.stat().st_dev != rootfs_info.st_dev:
        raise RetirementError("legacy CLI backup path is not on the rootfs filesystem")
    return backup_root


def preview(rootfs: Path, state_dir: Path) -> dict[str, object]:
    rootfs, root_info = _rootfs_identity(rootfs)
    state = _check_private_dir(state_dir)
    backup_root = _backup_root(state, root_info)
    path, info, data, digest = _read_target(rootfs)
    parent_info = path.parent.stat()
    payload = {
        "operation": "retire-legacy-debian-guest-cli",
        "rootfs": str(rootfs), "rootfs_device": root_info.st_dev,
        "rootfs_inode": root_info.st_ino,
        "target": str(path), "target_device": info.st_dev,
        "target_inode": info.st_ino, "target_size": info.st_size,
        "target_sha256": digest, "target_uid": info.st_uid,
        "target_gid": info.st_gid, "target_mode": stat.S_IMODE(info.st_mode),
        "target_mtime_ns": info.st_mtime_ns,
        "parent_device": parent_info.st_dev, "parent_inode": parent_info.st_ino,
        "backup_root": str(backup_root), "backup_filesystem_device": state.stat().st_dev,
        "confirmation_required": True,
        "impact": "Moves only /usr/local/bin/ternux out of the active Debian rootfs into a private same-filesystem rollback snapshot; no PRoot process is signaled.",
    }
    plan_id = "plan-" + hashlib.sha256(json.dumps(payload, sort_keys=True,
                                                   separators=(",", ":")).encode()).hexdigest()
    return {"plan_id": plan_id, **payload}


def _backup_dir(state_dir: Path, backup_id: str) -> Path:
    if not isinstance(backup_id, str) or not _BACKUP_ID.fullmatch(backup_id):
        raise RetirementError("legacy CLI backup ID is invalid")
    state = _check_private_dir(state_dir)
    path = state / "proot" / "legacy-cli-backups" / backup_id
    parent = _check_private_dir(path.parent)
    if parent.stat().st_dev != state.stat().st_dev:
        raise RetirementError("backup path filesystem changed")
    return path


def _lock(state_dir: Path):
    state = _check_private_dir(state_dir)
    lock_path = state / "proot" / ".legacy-cli-retirement.lock"
    lock_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
        os.close(fd)
        raise RetirementError("legacy CLI retirement lock is unsafe")
    fcntl.flock(fd, fcntl.LOCK_EX)
    return fd


def _write_json(path: Path, payload: dict[str, object]) -> None:
    temp = path.with_name(path.name + ".tmp-" + str(os.getpid()))
    fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        data = json.dumps(payload, sort_keys=True, indent=2).encode() + b"\n"
        view = memoryview(data)
        while view:
            view = view[os.write(fd, view):]
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temp, path)
    os.chmod(path, 0o600)


def apply(rootfs: Path, state_dir: Path, plan_id: str) -> dict[str, object]:
    if not isinstance(plan_id, str) or not _BACKUP_ID.fullmatch(plan_id):
        raise RetirementError("an exact preview plan ID is required")
    lock_fd = _lock(state_dir)
    try:
        plan = preview(rootfs, state_dir)
        if plan["plan_id"] != plan_id:
            raise RetirementError("legacy CLI preview is stale; review a fresh preview")
        path = Path(plan["target"])
        _backup_root(state_dir, _rootfs_identity(rootfs)[1], create=True)
        backup_dir = _backup_dir(state_dir, plan_id)
        if backup_dir.exists() or backup_dir.is_symlink():
            raise RetirementError("backup ID already exists; refusing to overwrite it")
        backup_dir.mkdir(mode=0o700)
        metadata = {**plan, "backup_id": plan_id, "state": "prepared",
                    "created_at_ns": time.time_ns()}
        _write_json(backup_dir / "metadata.json", metadata)
        # Recheck the exact source immediately before an atomic same-filesystem rename.
        current = preview(rootfs, state_dir)
        if current["plan_id"] != plan_id:
            raise RetirementError("legacy CLI changed after preview; no file was moved")
        backup_file = backup_dir / "ternux"
        os.rename(path, backup_file)
        moved = backup_file.lstat()
        moved_hash = hashlib.sha256(backup_file.read_bytes()).hexdigest()
        if ((moved.st_dev, moved.st_ino, moved.st_size, moved.st_uid, moved.st_gid,
             stat.S_IMODE(moved.st_mode), moved.st_mtime_ns, moved_hash) !=
                (plan["target_device"], plan["target_inode"], plan["target_size"],
                 plan["target_uid"], plan["target_gid"], plan["target_mode"],
                 plan["target_mtime_ns"], plan["target_sha256"])):
            if not path.exists() and not path.is_symlink():
                os.rename(backup_file, path)
            raise RetirementError("moved file identity differs from the preview; file restored when safe")
        _write_json(backup_dir / "metadata.json", {**metadata, "state": "retired"})
        return {"retired": True, "backup_id": plan_id,
                "backup_path": str(backup_file), "sha256": plan["target_sha256"],
                "target": str(path), "rootfs_inode": plan["rootfs_inode"]}
    finally:
        os.close(lock_fd)


def rollback(rootfs: Path, state_dir: Path, backup_id: str) -> dict[str, object]:
    lock_fd = _lock(state_dir)
    try:
        backup_dir = _backup_dir(state_dir, backup_id)
        metadata_path = backup_dir / "metadata.json"
        if metadata_path.is_symlink() or not metadata_path.is_file():
            raise RetirementError("legacy CLI backup metadata is missing or unsafe")
        metadata = json.loads(metadata_path.read_text())
        rootfs = rootfs.absolute()
        target, root_info, parent_info = _target_and_parent(rootfs)
        if (metadata.get("rootfs") != str(rootfs)
                or metadata.get("rootfs_device") != root_info.st_dev
                or metadata.get("rootfs_inode") != root_info.st_ino):
            raise RetirementError("rollback rootfs identity does not match the retired target")
        if (parent_info.st_dev, parent_info.st_ino) != (metadata.get("parent_device"), metadata.get("parent_inode")):
            raise RetirementError("rollback target directory identity changed")
        if target.exists() or target.is_symlink():
            raise RetirementError("rollback target already exists; refusing to overwrite it")
        backup = backup_dir / "ternux"
        info = backup.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                or info.st_dev != metadata.get("target_device")
                or info.st_ino != metadata.get("target_inode")
                or stat.S_IMODE(info.st_mode) != metadata.get("target_mode")
                or hashlib.sha256(backup.read_bytes()).hexdigest() != metadata.get("target_sha256")):
            raise RetirementError("legacy CLI backup identity or contents are invalid")
        os.rename(backup, target)
        restored = target.lstat()
        if (restored.st_dev, restored.st_ino, restored.st_uid, restored.st_gid,
                stat.S_IMODE(restored.st_mode), restored.st_mtime_ns) != (
                metadata["target_device"], metadata["target_inode"], metadata["target_uid"],
                metadata["target_gid"], metadata["target_mode"], metadata["target_mtime_ns"]):
            raise RetirementError("restored CLI metadata differs from the recorded original")
        _write_json(metadata_path, {**metadata, "state": "restored", "restored_at_ns": time.time_ns()})
        return {"restored": True, "backup_id": backup_id, "target": str(target),
                "sha256": metadata["target_sha256"]}
    finally:
        os.close(lock_fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preview", "apply", "rollback"))
    parser.add_argument("--rootfs", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--plan-id")
    parser.add_argument("--backup-id")
    parser.add_argument("--json", action="store_true", help="emit the machine-readable operation result")
    args = parser.parse_args(argv)
    try:
        if args.action == "preview":
            result = preview(args.rootfs, args.state_dir)
        elif args.action == "apply":
            if args.plan_id is None:
                raise RetirementError("apply requires --plan-id from the exact preview")
            result = apply(args.rootfs, args.state_dir, args.plan_id)
        else:
            if args.backup_id is None:
                raise RetirementError("rollback requires --backup-id from a completed retirement")
            result = rollback(args.rootfs, args.state_dir, args.backup_id)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, **result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
