"""Ternuxx-owned adoption metadata for the existing Debian PRoot.

Adoption records only the selected rootfs identity in private Native state.
It never writes to the guest or consults the legacy Ternux CLI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

import desktop_session_state
import proot_fresh_setup


class SetupError(ValueError):
    pass


def _manifest(repo_root: Path) -> tuple[dict[str, object], str]:
    path = repo_root / "config/proot/debian-trixie.json"
    try:
        raw = path.read_bytes()
        data = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SetupError("Ternuxx Debian setup manifest is unavailable or invalid") from exc
    if data.get("schema_version") != 1 or data.get("provider") != "proot-distro":
        raise SetupError("Ternuxx Debian setup manifest schema is unsupported")
    return data, hashlib.sha256(raw).hexdigest()


def _safe_rootfs(prefix: str) -> tuple[Path, os.stat_result]:
    root = Path(prefix) / "var/lib/proot-distro/containers/debian/rootfs"
    try:
        for item in (root.parent.parent, root.parent, root):
            metadata = item.lstat()
            if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
                raise SetupError("Debian rootfs path is not a regular directory tree")
            if metadata.st_uid != os.getuid():
                raise SetupError("Debian rootfs path has an unexpected owner")
        resolved = root.resolve(strict=True)
        if resolved != root.absolute():
            raise SetupError("Debian rootfs resolves through a symbolic link")
        metadata = root.stat()
    except SetupError:
        raise
    except OSError as exc:
        raise SetupError("installed Debian rootfs is unavailable") from exc
    return root, metadata


def _guest_profile(root: Path, user: str) -> dict[str, object]:
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", user):
        raise SetupError("guest username is invalid")
    try:
        release_path = root / "etc/os-release"
        release_resolved = release_path.resolve(strict=True)
        if root.resolve(strict=True) not in release_resolved.parents:
            raise SetupError("Debian release identity resolves outside the rootfs")
        release_meta = release_resolved.stat()
        if not stat.S_ISREG(release_meta.st_mode):
            raise SetupError("Debian release identity file is unsafe")
        release_values = {}
        for line in release_resolved.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator and key in {"ID", "VERSION_ID", "VERSION_CODENAME"}:
                release_values[key] = value.strip().strip('"')
        if release_values.get("ID") != "debian" or release_values.get("VERSION_CODENAME") != "trixie":
            raise SetupError("existing guest is not the Debian Trixie profile supported by this adapter")
        passwd_path = root / "etc/passwd"
        passwd_meta = passwd_path.lstat()
        if not stat.S_ISREG(passwd_meta.st_mode) or stat.S_ISLNK(passwd_meta.st_mode):
            raise SetupError("guest account database is unsafe")
        accounts = []
        for line in passwd_path.read_text(encoding="utf-8").splitlines():
            fields = line.split(":")
            if len(fields) != 7 or fields[0] != user:
                continue
            if not fields[2].isdigit() or not fields[3].isdigit():
                raise SetupError("guest account identity is malformed")
            accounts.append({"name": fields[0], "uid": int(fields[2]), "gid": int(fields[3]),
                             "home": fields[5], "shell": fields[6]})
        if len(accounts) != 1 or accounts[0]["uid"] < 1000:
            raise SetupError("selected guest account is missing or is not an ordinary user")
    except SetupError:
        raise
    except (OSError, UnicodeError) as exc:
        raise SetupError("could not read the fixed Debian profile files") from exc

    graphics = {}
    for key, relative in (
        ("turnip_driver", "usr/local/lib/aarch64-linux-gnu/libvulkan_freedreno.so"),
        ("turnip_icd", "usr/local/share/vulkan/icd.d/ternux_freedreno_icd.json"),
    ):
        path = root / relative
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            graphics[key] = {"status": "missing"}
            continue
        if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
            raise SetupError(f"guest graphics path is unsafe: {relative}")
        graphics[key] = {"status": "present", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    return {"release": release_values, "account": accounts[0], "graphics_files": graphics}


def _state_paths(state_dir: str, home: str, *, create: bool) -> tuple[Path, Path, Path]:
    state = Path(state_dir)
    desktop_session_state.ensure_state_dir(Path(home), state)
    root = state / "proot-setup"
    if not root.exists():
        if not create:
            return root, root / "previews", root / "provider.json"
        root.mkdir(mode=0o700)
    metadata = root.lstat()
    if (stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o077):
        raise SetupError("private PRoot setup state directory is unsafe")
    previews = root / "previews"
    if create:
        previews.mkdir(mode=0o700, exist_ok=True)
    if previews.exists():
        info = previews.lstat()
        if (stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode)
                or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077):
            raise SetupError("private PRoot setup preview directory is unsafe")
    return root, previews, root / "provider.json"


def _atomic_private_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".setup-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, sort_keys=True, separators=(",", ":"), allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass


def preview_adoption(*, repo_root: str, prefix: str, home: str,
                     state_dir: str, user: str) -> dict[str, object]:
    manifest, manifest_hash = _manifest(Path(repo_root))
    root, identity = _safe_rootfs(prefix)
    guest = _guest_profile(root, user)
    operation = {
        "schema_version": 1,
        "operation": "adopt-existing-debian",
        "manifest_sha256": manifest_hash,
        "rootfs": str(root),
        "rootfs_device": identity.st_dev,
        "rootfs_inode": identity.st_ino,
        "guest_user": user,
        "guest_release": guest["release"],
        "observed_graphics_files": guest["graphics_files"],
        "guest_mutations": [],
        "package_changes": [],
        "service_changes": [],
        "ternux_cli_required": False,
    }
    plan_id = hashlib.sha256(json.dumps(operation, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    operation["plan_id"] = plan_id
    _, previews, _ = _state_paths(state_dir, home, create=True)
    _atomic_private_json(previews / f"{plan_id}.json", operation)
    return {"status": "preview", "plan_id": plan_id, "operation": operation}


def apply_adoption(*, repo_root: str, prefix: str, home: str,
                   state_dir: str, user: str, plan_id: str, confirmed: bool) -> dict[str, object]:
    if not confirmed:
        raise SetupError("adoption requires explicit confirmation")
    if not re.fullmatch(r"[0-9a-f]{64}", plan_id):
        raise SetupError("a valid preview plan ID is required")
    current = preview_adoption(repo_root=repo_root, prefix=prefix, home=home,
                               state_dir=state_dir, user=user)
    if current["plan_id"] != plan_id:
        raise SetupError("current rootfs or manifest differs from the reviewed preview")
    root, previews, record = _state_paths(state_dir, home, create=True)
    preview_path = previews / f"{plan_id}.json"
    try:
        info = preview_path.lstat()
        if (not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode)
                or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600):
            raise SetupError("saved preview identity or permissions are unsafe")
        reviewed = json.loads(preview_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SetupError("saved adoption preview is unavailable") from exc
    if reviewed.get("plan_id") != plan_id:
        raise SetupError("saved adoption preview does not match its ID")
    payload = {
        "schema_version": 1,
        "profile_id": "ternuxx-debian-trixie-workstation",
        "manifest_sha256": reviewed["manifest_sha256"],
        "rootfs": reviewed["rootfs"],
        "rootfs_device": reviewed["rootfs_device"],
        "rootfs_inode": reviewed["rootfs_inode"],
        "guest_user": reviewed["guest_user"],
        "guest_release": reviewed["guest_release"],
        "adopted_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "origin": "existing-rootfs-adoption",
    }
    _atomic_private_json(record, payload)
    preview_path.unlink()
    return {"status": "adopted", "record": payload, "guest_mutations": False}


def status(*, repo_root: str, prefix: str, home: str, state_dir: str) -> dict[str, object]:
    _, manifest_hash = _manifest(Path(repo_root))
    root, previews, record_path = _state_paths(state_dir, home, create=False)
    try:
        rootfs, identity = _safe_rootfs(prefix)
    except SetupError as exc:
        return {"status": "missing_or_unavailable", "detail": str(exc),
                "manifest_sha256": manifest_hash, "fresh_setup_profile": "debian-trixie-workstation"}
    adoption = None
    if record_path.exists():
        info = record_path.lstat()
        if (not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode)
                or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600):
            raise SetupError("saved Ternuxx PRoot setup record is unsafe")
        adoption = json.loads(record_path.read_text(encoding="utf-8"))
        if (adoption.get("rootfs_device"), adoption.get("rootfs_inode")) != (identity.st_dev, identity.st_ino):
            return {"status": "adoption_stale", "rootfs": str(rootfs),
                    "manifest_sha256": manifest_hash, "saved_profile": adoption.get("profile_id")}
        if adoption.get("manifest_sha256") != manifest_hash:
            return {"status": "profile_changed", "rootfs": str(rootfs),
                    "manifest_sha256": manifest_hash, "saved_profile": adoption.get("profile_id")}
    return {"status": "adopted" if adoption else "needs_adoption",
            "rootfs": str(rootfs), "rootfs_device": identity.st_dev, "rootfs_inode": identity.st_ino,
            "manifest_sha256": manifest_hash, "profile_id": "ternuxx-debian-trixie-workstation",
            "recorded_guest_user": adoption.get("guest_user") if adoption else None,
            "ternux_cli_dependency": False,
            "next_action": "none" if adoption else "preview and confirm read-only adoption"}


def main() -> int:
    parser = argparse.ArgumentParser(prog="tx proot setup")
    parser.add_argument("action", choices=("status", "adopt-preview", "adopt", "fresh-preview", "fresh-install"))
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--prefix", default=os.environ.get("PREFIX", ""))
    parser.add_argument("--home", default=os.environ.get("HOME", ""))
    parser.add_argument("--state-dir", default=os.environ.get("TERNUXX_STATE_DIR", ""))
    parser.add_argument("--user", default="")
    parser.add_argument("--plan-id", default="")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not args.prefix or not args.home or not args.state_dir:
        parser.error("Native Termux PREFIX, HOME, and Ternuxx state directory are required")
    try:
        if args.action == "status":
            result = status(repo_root=args.repo_root, prefix=args.prefix, home=args.home, state_dir=args.state_dir)
        elif args.action == "adopt-preview":
            if not args.user:
                parser.error("adopt-preview requires --user NAME")
            result = preview_adoption(repo_root=args.repo_root, prefix=args.prefix, home=args.home,
                                      state_dir=args.state_dir, user=args.user)
        elif args.action == "fresh-preview":
            if not args.user or args.plan_id or args.yes:
                parser.error("fresh-preview requires --user NAME")
            result = proot_fresh_setup.preview(repo_root=args.repo_root, prefix=args.prefix,
                                               home=args.home, state_dir=args.state_dir, user=args.user)
        elif args.action == "fresh-install":
            if not args.user or not args.plan_id or not args.yes:
                parser.error("fresh-install requires --user NAME --yes --plan-id ID")
            result = proot_fresh_setup.apply(repo_root=args.repo_root, prefix=args.prefix,
                                             home=args.home, state_dir=args.state_dir, user=args.user,
                                             plan_id=args.plan_id, confirmed=True)
        else:
            if not args.user or not args.plan_id or not args.yes:
                parser.error("adopt requires --user NAME --yes --plan-id ID")
            result = apply_adoption(repo_root=args.repo_root, prefix=args.prefix, home=args.home,
                                    state_dir=args.state_dir, user=args.user,
                                    plan_id=args.plan_id, confirmed=True)
    except (SetupError, proot_fresh_setup.FreshSetupError, OSError, ValueError) as exc:
        result = {"status": "failed", "error": str(exc)}
        print(json.dumps(result, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
