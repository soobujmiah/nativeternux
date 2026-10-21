#!/usr/bin/env python3
"""Preview, remove, and restore the old native Ternux CLI and its libraries."""
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

_ID = re.compile(r"^plan-[0-9a-f]{64}$")
_MAX_TOTAL = 4 * 1024 * 1024


class RetirementError(ValueError):
    pass


def _private_dir(path: Path, *, create: bool = False) -> Path:
    path = path.absolute()
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise RetirementError("private state path contains a symlink")
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077):
        raise RetirementError("private state directory is not owned and mode 0700")
    return path


def _no_symlink_path(path: Path) -> Path:
    path = path.absolute()
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise RetirementError("legacy CLI path contains a symlink")
    return path


def _tree_manifest(path: Path) -> list[dict[str, object]]:
    path = _no_symlink_path(path)
    root = path.lstat()
    entries: list[Path] = [path]
    if stat.S_ISDIR(root.st_mode):
        for base, dirs, files in os.walk(path, followlinks=False):
            base_path = Path(base)
            for name in dirs + files:
                entries.append(base_path / name)
    manifest = []
    total = 0
    for item in sorted(entries, key=lambda p: str(p.relative_to(path.parent))):
        info = item.lstat()
        if stat.S_ISDIR(info.st_mode):
            kind, digest, size = "directory", None, 0
        elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
            kind, size = "file", info.st_size
            total += size
            if total > _MAX_TOTAL:
                raise RetirementError("legacy CLI library tree exceeds the reviewed snapshot bound")
            digest = hashlib.sha256(item.read_bytes()).hexdigest()
        else:
            raise RetirementError("legacy CLI tree contains a link or unsupported file type")
        if info.st_uid != os.getuid():
            raise RetirementError("legacy CLI tree has an unexpected owner")
        manifest.append({
            "relative_path": "." if item == path else str(item.relative_to(path)),
            "kind": kind, "device": info.st_dev, "inode": info.st_ino,
            "uid": info.st_uid, "gid": info.st_gid,
            "mode": stat.S_IMODE(info.st_mode), "mtime_ns": info.st_mtime_ns,
            "size": size, "sha256": digest,
        })
    return manifest


def _inspect(prefix: Path, state_dir: Path) -> dict[str, object]:
    prefix = _no_symlink_path(prefix)
    prefix_info = prefix.lstat()
    if not stat.S_ISDIR(prefix_info.st_mode):
        raise RetirementError("Termux PREFIX is not a directory")
    state = _private_dir(state_dir)
    if state.stat().st_dev != prefix_info.st_dev:
        raise RetirementError("backup state and Termux PREFIX must share a filesystem for atomic retirement")
    command = _no_symlink_path(prefix / "bin/ternux")
    library = _no_symlink_path(prefix / "lib/ternux")
    command_manifest = _tree_manifest(command)
    library_manifest = _tree_manifest(library)
    command_data = command.read_bytes()
    if "ternux — Linux desktop CLI".encode() not in command_data or b"_TNX_LIB_DIR" not in command_data:
        raise RetirementError("PREFIX/bin/ternux is not the expected legacy host CLI")
    if not (library / "core.sh").is_file():
        raise RetirementError("PREFIX/lib/ternux is missing its legacy CLI core")
    parents = {str(path): {"device": path.parent.stat().st_dev,
                           "inode": path.parent.stat().st_ino}
               for path in (command, library)}
    if any(parent["device"] != prefix_info.st_dev for parent in parents.values()):
        raise RetirementError("legacy CLI paths are not on the Termux PREFIX filesystem")
    return {
        "operation": "retire-legacy-native-ternux-cli",
        "prefix": str(prefix), "prefix_device": prefix_info.st_dev,
        "prefix_inode": prefix_info.st_ino,
        "state_dir": str(state),
        "backup_root": str(state / "legacy-cli-backups"),
        "backup_filesystem_device": state.stat().st_dev,
        "targets": {"command": str(command), "library": str(library)},
        "parent_identities": parents,
        "command_manifest": command_manifest,
        "library_manifest": library_manifest,
        "confirmation_required": True,
        "impact": "Atomically moves only the prior host CLI command and module directory into a private same-filesystem rollback snapshot. The supported tx entrypoint and canonical module tree remain untouched; no PRoot process or Native service is stopped.",
    }


def preview(prefix: Path, state_dir: Path) -> dict[str, object]:
    payload = _inspect(prefix, state_dir)
    plan_id = "plan-" + hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"plan_id": plan_id, **payload}


def _lock(state_dir: Path) -> int:
    state = _private_dir(state_dir)
    lock_dir = state / "proot"
    if lock_dir.exists():
        _private_dir(lock_dir)
    else:
        lock_dir.mkdir(mode=0o700)
    path = lock_dir / ".legacy-cli-retirement.lock"
    fd = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    info = os.fstat(fd)
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600):
        os.close(fd)
        raise RetirementError("legacy CLI retirement lock is unsafe")
    fcntl.flock(fd, fcntl.LOCK_EX)
    return fd


def _write_json(path: Path, data: dict[str, object]) -> None:
    temp = path.with_name(path.name + ".tmp-" + str(os.getpid()))
    fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        encoded = json.dumps(data, sort_keys=True, indent=2).encode() + b"\n"
        view = memoryview(encoded)
        while view:
            view = view[os.write(fd, view):]
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temp, path)
    os.chmod(path, 0o600)


def _backup_dir(state_dir: Path, plan_id: str, *, create: bool = False) -> Path:
    if not isinstance(plan_id, str) or not _ID.fullmatch(plan_id):
        raise RetirementError("legacy CLI backup plan ID is invalid")
    state = _private_dir(state_dir)
    root = state / "legacy-cli-backups"
    if root.exists() or root.is_symlink():
        _private_dir(root)
    elif create:
        root.mkdir(mode=0o700)
    return root / plan_id


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def apply(prefix: Path, state_dir: Path, plan_id: str) -> dict[str, object]:
    if not isinstance(plan_id, str) or not _ID.fullmatch(plan_id):
        raise RetirementError("an exact legacy CLI preview ID is required")
    lock_fd = _lock(state_dir)
    try:
        plan = preview(prefix, state_dir)
        if plan["plan_id"] != plan_id:
            raise RetirementError("legacy host CLI preview is stale; review a fresh preview")
        backup_dir = _backup_dir(state_dir, plan_id, create=True)
        if backup_dir.exists() or backup_dir.is_symlink():
            raise RetirementError("legacy host CLI backup ID already exists")
        backup_dir.mkdir(mode=0o700)
        (backup_dir / "library").mkdir(mode=0o700)
        metadata = {**plan, "backup_id": plan_id, "state": "prepared",
                    "moved": [], "created_at_ns": time.time_ns()}
        _write_json(backup_dir / "metadata.json", metadata)
        current = preview(prefix, state_dir)
        if current["plan_id"] != plan_id:
            raise RetirementError("legacy host CLI changed after preview; nothing moved")
        targets = plan["targets"]
        command_src, library_src = Path(targets["command"]), Path(targets["library"])
        command_dst, library_dst = backup_dir / "ternux", backup_dir / "library" / "ternux"
        moved = []
        for name, src, dst, expected in (
                ("command", command_src, command_dst, plan["command_manifest"]),
                ("library", library_src, library_dst, plan["library_manifest"])):
            if _tree_manifest(src) != expected:
                raise RetirementError("legacy CLI identity changed during apply")
            os.rename(src, dst)
            if stat.S_ISDIR(dst.lstat().st_mode):
                root_entry = next(entry for entry in expected if entry["relative_path"] == ".")
                os.utime(dst, ns=(dst.stat().st_atime_ns, root_entry["mtime_ns"]))
            _fsync_dir(src.parent)
            _fsync_dir(dst.parent)
            moved.append(name)
            metadata = {**metadata, "moved": moved, "state": "partial" if len(moved) == 1 else "retired"}
            _write_json(backup_dir / "metadata.json", metadata)
            actual = _tree_manifest(dst)
            if actual != expected:
                if not src.exists() and not src.is_symlink():
                    os.rename(dst, src)
                    _fsync_dir(src.parent)
                    _fsync_dir(dst.parent)
                raise RetirementError("moved legacy CLI identity differs from preview; restored when safe")
        return {"retired": True, "backup_id": plan_id,
                "backup_path": str(backup_dir), "targets": targets}
    finally:
        os.close(lock_fd)


def rollback(prefix: Path, state_dir: Path, backup_id: str) -> dict[str, object]:
    lock_fd = _lock(state_dir)
    try:
        backup_dir = _backup_dir(state_dir, backup_id)
        metadata_path = backup_dir / "metadata.json"
        if metadata_path.is_symlink() or not metadata_path.is_file():
            raise RetirementError("legacy host CLI backup metadata is missing or unsafe")
        metadata = json.loads(metadata_path.read_text())
        prefix = _no_symlink_path(prefix)
        prefix_info = prefix.lstat()
        if (metadata.get("prefix") != str(prefix)
                or metadata.get("prefix_device") != prefix_info.st_dev
                or metadata.get("prefix_inode") != prefix_info.st_ino):
            raise RetirementError("rollback PREFIX identity changed")
        _private_dir(state_dir)
        if Path(state_dir).stat().st_dev != prefix_info.st_dev:
            raise RetirementError("rollback state filesystem changed")
        for target in metadata["targets"].values():
            target_path = Path(target)
            parent = _no_symlink_path(target_path.parent)
            expected_parent = metadata["parent_identities"][str(target_path)]
            parent_info = parent.stat()
            if (parent_info.st_dev, parent_info.st_ino) != (expected_parent["device"], expected_parent["inode"]):
                raise RetirementError("rollback target directory identity changed")
        outcomes = []
        for name, src_key, manifest_key, backup in (
                ("command", "command", "command_manifest", backup_dir / "ternux"),
                ("library", "library", "library_manifest", backup_dir / "library" / "ternux")):
            target = Path(metadata["targets"][src_key])
            backup_exists = backup.exists() or backup.is_symlink()
            target_exists = target.exists() or target.is_symlink()
            if target_exists:
                if backup_exists:
                    raise RetirementError("rollback target exists; refusing to overwrite it")
                if _tree_manifest(target) == metadata[manifest_key]:
                    outcomes.append(name + ":already-restored-or-not-moved")
                    continue
                raise RetirementError("rollback target exists with unrecognized contents")
            if not backup_exists:
                raise RetirementError("both original and backup are missing; cannot claim rollback")
            if _tree_manifest(backup) != metadata[manifest_key]:
                raise RetirementError("legacy host CLI backup content or identity changed")
            os.rename(backup, target)
            if stat.S_ISDIR(target.lstat().st_mode):
                root_entry = next(entry for entry in metadata[manifest_key] if entry["relative_path"] == ".")
                os.utime(target, ns=(target.stat().st_atime_ns, root_entry["mtime_ns"]))
            if _tree_manifest(target) != metadata[manifest_key]:
                raise RetirementError("restored legacy CLI identity differs from its backup manifest")
            _fsync_dir(target.parent)
            _fsync_dir(backup.parent)
            outcomes.append(name + ":restored")
        _write_json(metadata_path, {**metadata, "state": "restored",
                                    "rollback": outcomes, "restored_at_ns": time.time_ns()})
        return {"restored": True, "backup_id": backup_id, "outcomes": outcomes,
                "targets": metadata["targets"]}
    finally:
        os.close(lock_fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preview", "apply", "rollback"))
    parser.add_argument("--prefix", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--plan-id")
    parser.add_argument("--backup-id")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.action == "preview":
            result = preview(args.prefix, args.state_dir)
        elif args.action == "apply":
            if args.plan_id is None:
                raise RetirementError("apply requires --plan-id from the exact preview")
            result = apply(args.prefix, args.state_dir, args.plan_id)
        else:
            if args.backup_id is None:
                raise RetirementError("rollback requires --backup-id from the retirement result")
            result = rollback(args.prefix, args.state_dir, args.backup_id)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, **result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
