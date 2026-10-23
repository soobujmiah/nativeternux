"""Ternuxx-owned adoption metadata for the existing Debian PRoot.

Adoption records only the selected rootfs identity in private Native state.
It never writes to the guest or consults the legacy Ternux CLI.
"""
from __future__ import annotations

import argparse
import hashlib
import getpass
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


def _read_stable_regular_file(path: Path, *, max_bytes: int, mode: int | None = None) -> bytes:
    flags = os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
                or before.st_size > max_bytes
                or (mode is not None and stat.S_IMODE(before.st_mode) != mode)):
            raise SetupError("file identity or permissions are unsafe")
        chunks = []
        remaining = max_bytes + 1
        while remaining:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        after = os.fstat(fd)
        identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
        identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        data = b"".join(chunks)
        if identity_before != identity_after or len(data) > max_bytes:
            raise SetupError("file changed while it was being inspected")
        return data
    finally:
        os.close(fd)


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


def _observe_guest_file(root: Path, guest_path: str) -> dict[str, object]:
    if (not isinstance(guest_path, str) or len(guest_path) > 512
            or not guest_path.startswith("/") or "\x00" in guest_path):
        raise SetupError("managed guest graphics path is invalid")
    relative = Path(guest_path)
    if any(part in {".", ".."} for part in relative.parts[1:]):
        raise SetupError("managed guest graphics path escapes the rootfs")
    current = root
    parts = relative.parts[1:]
    if not parts or str(relative) != guest_path:
        raise SetupError("managed guest graphics path is not canonical")
    for index, part in enumerate(parts):
        current = current / part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            return {"path": guest_path, "status": "missing"}
        if stat.S_ISLNK(metadata.st_mode):
            raise SetupError(f"guest graphics path contains a symlink: {guest_path}")
        if index < len(parts) - 1 and not stat.S_ISDIR(metadata.st_mode):
            raise SetupError(f"guest graphics path parent is not a directory: {guest_path}")
    try:
        content = _read_stable_regular_file(current, max_bytes=64 * 1024 * 1024)
    except (OSError, SetupError) as exc:
        raise SetupError(f"guest graphics file is unsafe: {guest_path}") from exc
    return {"path": guest_path, "status": "present",
            "sha256": hashlib.sha256(content).hexdigest()}


def _guest_packages(root: Path, manifest: dict[str, object]) -> dict[str, object]:
    database_dir = root / "var/lib/dpkg"
    status_path = database_dir / "status"
    try:
        for directory in (root / "var", root / "var/lib", database_dir):
            metadata = directory.lstat()
            if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
                raise SetupError("guest dpkg database path is unsafe")
        try:
            raw = _read_stable_regular_file(status_path, max_bytes=64 * 1024 * 1024)
        except OSError as exc:
            raise SetupError("guest dpkg status database is unsafe or unavailable") from exc
        text = raw.decode("utf-8", "strict")
    except SetupError:
        raise
    except (OSError, UnicodeError) as exc:
        raise SetupError("guest dpkg package inventory is unavailable") from exc

    installed: dict[str, list[dict[str, str]]] = {}
    for paragraph in text.split("\n\n"):
        fields: dict[str, str] = {}
        for line in paragraph.splitlines():
            if line and not line[0].isspace() and ":" in line:
                key, value = line.split(":", 1)
                fields[key] = value.strip()
        state = fields.get("Status", "").split()
        package = fields.get("Package", "")
        architecture = fields.get("Architecture", "")
        if (len(state) != 3 or state[1] != "ok" or state[2] != "installed"
                or state[0] not in {"install", "hold"}
                or not re.fullmatch(r"[a-z0-9][a-z0-9+.-]{0,127}", package.split(":", 1)[0])
                or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,31}", architecture)):
            continue
        name = package.split(":", 1)[0]
        installed.setdefault(name, []).append({"architecture": architecture,
            "version": fields.get("Version", "unknown"), "held": "true" if state[0] == "hold" else "false"})

    architecture = manifest.get("architecture")
    expected_arch = {"aarch64": "arm64", "x86_64": "amd64"}.get(architecture, architecture)
    groups = manifest.get("packages")
    if not isinstance(groups, dict) or not isinstance(expected_arch, str):
        raise SetupError("guest package profile is invalid")
    inventory: dict[str, object] = {}
    for group, requested in groups.items():
        if (not isinstance(group, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,31}", group)
                or not isinstance(requested, list) or len(requested) > 512):
            raise SetupError("guest package groups are malformed")
        present: dict[str, dict[str, str]] = {}
        missing: list[str] = []
        held: list[str] = []
        for package in requested:
            if not isinstance(package, str) or not re.fullmatch(r"[a-z0-9][a-z0-9+.-]{0,127}", package):
                raise SetupError("guest package name is invalid")
            candidates = installed.get(package, [])
            candidates = [item for item in candidates if item["architecture"] in {expected_arch, "all"}]
            if not candidates:
                missing.append(package)
                continue
            selected = next((item for item in candidates if item["architecture"] == expected_arch), candidates[0])
            present[package] = {"version": selected["version"], "architecture": selected["architecture"]}
            if selected["held"] == "true":
                held.append(package)
        inventory[group] = {"requested": len(requested), "installed": len(present),
                            "missing": missing, "held": held, "versions": present}
    return {"groups": inventory, "dpkg_status_sha256": hashlib.sha256(raw).hexdigest()}


def _guest_profile(root: Path, user: str, manifest: dict[str, object]) -> dict[str, object]:
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

    packages = _guest_packages(root, manifest)
    try:
        paths = manifest["graphics"]["managed_install_paths"]
        graphics = {
            "turnip_driver": _observe_guest_file(root, paths["driver"]),
            "turnip_icd": _observe_guest_file(root, paths["icd"]),
        }
    except (KeyError, TypeError) as exc:
        raise SetupError("manifest managed graphics paths are invalid") from exc

    other_icd_configs = []
    icd_dir = root / "usr/local/share/vulkan/icd.d"
    try:
        directory_info = icd_dir.lstat()
    except FileNotFoundError:
        directory_info = None
    if directory_info is not None:
        if not stat.S_ISDIR(directory_info.st_mode) or stat.S_ISLNK(directory_info.st_mode):
            raise SetupError("guest ICD directory is unsafe")
        managed_name = Path(paths["icd"]).name
        for index, candidate in enumerate(sorted(icd_dir.iterdir())):
            if index >= 256:
                raise SetupError("guest ICD directory has too many entries")
            if candidate.name == managed_name or not candidate.name.endswith(".json"):
                continue
            info = candidate.lstat()
            if stat.S_ISREG(info.st_mode) and info.st_size <= 64 * 1024:
                other_icd_configs.append({"name": candidate.name,
                    "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest()})
            elif stat.S_ISLNK(info.st_mode):
                other_icd_configs.append({"name": candidate.name, "status": "symlink"})
    return {"release": release_values, "account": accounts[0], "graphics_files": graphics,
            "other_icd_configs": other_icd_configs, "packages": packages}


def _existing_adoption(path: Path) -> tuple[bytes | None, dict[str, object] | None]:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None, None
    try:
        raw = _read_stable_regular_file(path, max_bytes=1024 * 1024, mode=0o600)
    except (OSError, SetupError) as exc:
        raise SetupError("existing adoption record identity or permissions are unsafe") from exc
    try:
        record = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SetupError("existing adoption record is invalid; it was preserved") from exc
    if not isinstance(record, dict):
        raise SetupError("existing adoption record is invalid; it was preserved")
    return raw, record


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
    guest = _guest_profile(root, user, manifest)
    _state_root, _previews, record_path = _state_paths(state_dir, home, create=True)
    prior_bytes, prior_record = _existing_adoption(record_path)
    prior_hash = hashlib.sha256(prior_bytes).hexdigest() if prior_bytes is not None else None
    prior_matches = bool(prior_record and prior_record.get("profile_id") == manifest["profile_id"]
        and prior_record.get("manifest_sha256") == manifest_hash
        and prior_record.get("rootfs_device") == identity.st_dev
        and prior_record.get("rootfs_inode") == identity.st_ino
        and prior_record.get("guest_user") == user)
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
        "observed_other_icd_configs": guest["other_icd_configs"],
        "observed_package_groups": guest["packages"]["groups"],
        "dpkg_status_sha256": guest["packages"]["dpkg_status_sha256"],
        "prior_adoption_record_sha256": prior_hash,
        "apply_blocked_reason": ("an existing adoption record belongs to a different manifest, rootfs, or account; preserve it until an exact rollback path is available"
                                 if prior_bytes is not None and not prior_matches else None),
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
        raise SetupError("current rootfs, manifest, package state, or prior adoption record differs from the reviewed preview")
    operation = current["operation"]
    if operation.get("apply_blocked_reason"):
        raise SetupError(operation["apply_blocked_reason"])
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
    prior_bytes, prior_record = _existing_adoption(record)
    if prior_bytes is not None:
        if (prior_record.get("profile_id") == reviewed.get("profile_id")
                and prior_record.get("manifest_sha256") == reviewed.get("manifest_sha256")
                and prior_record.get("rootfs_device") == reviewed.get("rootfs_device")
                and prior_record.get("rootfs_inode") == reviewed.get("rootfs_inode")
                and prior_record.get("guest_user") == reviewed.get("guest_user")):
            return {"status": "adopted", "record": prior_record,
                    "guest_mutations": False, "native_metadata_changed": False}
        raise SetupError("an existing adoption record cannot be replaced without a tested rollback path")
    payload = {
        "schema_version": 1,
        "profile_id": "ternuxx-debian-trixie-workstation",
        "manifest_sha256": reviewed["manifest_sha256"],
        "rootfs": reviewed["rootfs"],
        "rootfs_device": reviewed["rootfs_device"],
        "rootfs_inode": reviewed["rootfs_inode"],
        "guest_user": reviewed["guest_user"],
        "guest_release": reviewed["guest_release"],
        "package_groups": reviewed["observed_package_groups"],
        "dpkg_status_sha256": reviewed["dpkg_status_sha256"],
        "adopted_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "origin": "existing-rootfs-adoption",
    }
    _atomic_private_json(record, payload)
    preview_path.unlink()
    return {"status": "adopted", "record": payload, "guest_mutations": False}


def status(*, repo_root: str, prefix: str, home: str, state_dir: str) -> dict[str, object]:
    manifest, manifest_hash = _manifest(Path(repo_root))
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
                    "manifest_sha256": manifest_hash,
                    "recorded_manifest_sha256": adoption.get("manifest_sha256"),
                    "saved_profile": adoption.get("profile_id"),
                    "detail": "setup manifest differs from the adoption record; guest drift is not inferred",
                    "next_action": "review the recorded and current manifest hashes; status does not refresh adoption metadata or change guest files"}
    package_baseline = {"status": "not_recorded", "changed_groups": []}
    if adoption and isinstance(adoption.get("package_groups"), dict):
        current_profile = _guest_profile(rootfs, adoption.get("guest_user", ""), manifest)
        current_groups = current_profile["packages"]["groups"]
        recorded_groups = adoption["package_groups"]
        changed_groups = []
        for group in manifest["packages"]:
            recorded = recorded_groups.get(group)
            current = current_groups.get(group)
            if not isinstance(recorded, dict) or not isinstance(current, dict):
                changed_groups.append(group)
                continue
            if (recorded.get("versions") != current.get("versions")
                    or recorded.get("missing") != current.get("missing")
                    or recorded.get("held") != current.get("held")):
                changed_groups.append(group)
        package_baseline = {"status": "matches" if not changed_groups else "changed",
                            "changed_groups": changed_groups,
                            "dpkg_status_sha256": current_profile["packages"]["dpkg_status_sha256"]}
    return {"status": "adopted" if adoption else "needs_adoption",
            "rootfs": str(rootfs), "rootfs_device": identity.st_dev, "rootfs_inode": identity.st_ino,
            "manifest_sha256": manifest_hash, "profile_id": "ternuxx-debian-trixie-workstation",
            "recorded_guest_user": adoption.get("guest_user") if adoption else None,
            "package_baseline": package_baseline,
            "ternux_cli_dependency": False,
            "next_action": "none" if adoption else "preview and confirm read-only adoption"}


def main() -> int:
    parser = argparse.ArgumentParser(prog="tx proot setup")
    parser.add_argument("action", choices=("status", "adopt-preview", "adopt", "fresh-preview", "fresh-resume-preview", "fresh-install"))
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--prefix", default=os.environ.get("PREFIX", ""))
    parser.add_argument("--home", default=os.environ.get("HOME", ""))
    parser.add_argument("--state-dir", default=os.environ.get("TERNUXX_STATE_DIR", ""))
    parser.add_argument("--user", default="")
    parser.add_argument("--alias", help="fresh-only debian or ternuxx-replay-NAME target")
    parser.add_argument("--plan-id", default="")
    parser.add_argument("--groups", help="comma-separated fresh Debian package groups; base is required")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not args.prefix or not args.home or not args.state_dir:
        parser.error("Native Termux PREFIX, HOME, and Ternuxx state directory are required")
    try:
        if args.alias is not None and args.action not in {"fresh-preview", "fresh-resume-preview", "fresh-install"}:
            parser.error("--alias is supported only by fresh setup")
        if args.groups is not None and args.action not in {"fresh-preview", "fresh-resume-preview"}:
            parser.error("--groups is supported only by fresh preview actions")
        groups = None if args.groups is None else args.groups.split(",")
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
                                               home=args.home, state_dir=args.state_dir, user=args.user,
                                               alias=args.alias if args.alias is not None else proot_fresh_setup.ALIAS,
                                               groups=groups)
        elif args.action == "fresh-resume-preview":
            if not args.user or not args.plan_id or args.yes:
                parser.error("fresh-resume-preview requires --user NAME --plan-id FAILED_PLAN_ID")
            result = proot_fresh_setup.preview(repo_root=args.repo_root, prefix=args.prefix,
                                               home=args.home, state_dir=args.state_dir, user=args.user,
                                               alias=args.alias if args.alias is not None else proot_fresh_setup.ALIAS,
                                               resume_plan_id=args.plan_id, groups=groups)
        elif args.action == "fresh-install":
            if not args.user or not args.plan_id or not args.yes:
                parser.error("fresh-install requires --user NAME --yes --plan-id ID")
            password = getpass.getpass("Create Debian sudo password: ")
            confirm_password = getpass.getpass("Confirm Debian sudo password: ")
            if password != confirm_password:
                raise proot_fresh_setup.FreshSetupError("password entries did not match")
            result = proot_fresh_setup.apply(repo_root=args.repo_root, prefix=args.prefix,
                                             home=args.home, state_dir=args.state_dir, user=args.user,
                                             plan_id=args.plan_id, confirmed=True, password=password,
                                             alias=args.alias if args.alias is not None else proot_fresh_setup.ALIAS)
            password = confirm_password = ""
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
