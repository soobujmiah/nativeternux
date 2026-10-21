"""Opt-in manager for the official Termux:Boot Cron-only entrypoint."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
from typing import Callable

import boot_state_path
import cron_scheduler
import runtime_diagnostics

PREFIX = "/data/data/com.termux/files/usr"
SCRIPT_NAME = "20-ternuxx-cron"
KNOWN_LEGACY_SCRIPT_HASHES = {"49c9fbadeaeb9e2173270606a26f8ad2fa0b76d8891e22645209b39dd0537305"}
_MAX_SCRIPT = 32768
_MAX_LOG = 256 * 1024
_SCRIPT = r'''#!/data/data/com.termux/files/usr/bin/python3
"""Ternuxx Termux:Boot entrypoint: start only the Cron daemon."""
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import shutil

PREFIX = "/data/data/com.termux/files/usr"
HOME = os.environ.get("HOME", "")
SAFE_TEST = os.environ.get("TERNUXX_BOOT_SAFE_TEST") == "1"
if PREFIX != "/data/data/com.termux/files/usr":
    raise SystemExit(2)
os.environ["PREFIX"] = PREFIX
os.environ["PATH"] = PREFIX + "/bin:" + os.environ.get("PATH", "")
os.environ.setdefault("TERMUX_VERSION", "boot")
os.environ.setdefault("TERNUXX_STATE_DIR", HOME + "/.local/share/ternuxx")
try:
    sys.path.insert(0, str(Path(HOME) / "ternuxx" / "lib"))
    from boot_state_path import StatePathError, ensure_private_tree, resolve_private_state
    home, state = resolve_private_state(
        HOME, os.environ["TERNUXX_STATE_DIR"],
        allowed_home_root=None if SAFE_TEST else "/data/data/com.termux/files/home")
    if SAFE_TEST:
        marker = home / ".ternuxx-termux-boot-safe-test"
        marker_stat = marker.lstat()
        if marker.is_symlink() or not stat.S_ISREG(marker_stat.st_mode) or marker_stat.st_mode & 0o077:
            raise StatePathError("safe-test marker identity or permissions are unsafe")
        if marker.read_text(encoding="utf-8") != "isolated-empty-cron-state-v1\n":
            raise StatePathError("safe-test marker is absent or invalid")
    boot_fd = ensure_private_tree(home, state)
except (OSError, ValueError, StatePathError):
    raise SystemExit(2)

log_path = "termux-boot-cron.jsonl"
lock_path = "entry.lock"
flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
lock_fd = os.open(lock_path, flags, 0o600, dir_fd=boot_fd)
try:
    lock_stat = os.fstat(lock_fd)
    if not stat.S_ISREG(lock_stat.st_mode) or lock_stat.st_uid != os.getuid() or lock_stat.st_mode & 0o077:
        raise SystemExit(2)
    fcntl.flock(lock_fd, fcntl.LOCK_EX)
    tx = Path(HOME) / "ternuxx" / "tx"
    bash = Path(PREFIX) / "bin" / "bash"
    if not bash.is_file():
        # Allows isolated host fixtures; real Termux uses the fixed prefix path.
        fallback = shutil.which("bash")
        bash = Path(fallback) if fallback else bash
    if (not tx.is_file() or not os.access(tx, os.X_OK)
            or not bash.is_file() or not os.access(bash, os.X_OK)):
        result = {"outcome": "cli_unavailable", "started_by_script": False}
    else:
        try:
            # The checkout entrypoint has a /usr/bin/env shebang, which is
            # absent on Native Termux. Bash can interpret the shell script,
            # but subprocess execve cannot apply Bash's interactive fallback.
            completed = subprocess.run(
                [str(bash), str(tx), "mng", "cron", "start", "--yes"],
                cwd=str(tx.parent), env=os.environ.copy(), stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20,
                check=False,
            )
            try:
                response = json.loads(completed.stdout)
                data = response.get("data", {}) if response.get("ok") is True else {}
                started = data.get("started") is True
                result = {"outcome": "started" if started else "already_running" if data.get("already_running") is True else "start_failed",
                          "started_by_script": started,
                          "scheduler_instance_id": data.get("status", {}).get("instance_id") if isinstance(data.get("status"), dict) else None,
                          "exit_code": completed.returncode}
            except (ValueError, AttributeError):
                result = {"outcome": "start_failed", "started_by_script": False,
                          "exit_code": completed.returncode, "detail": "non-JSON CLI response"}
        except subprocess.TimeoutExpired:
            result = {"outcome": "start_timeout", "started_by_script": False}
        except OSError:
            result = {"outcome": "start_failed", "started_by_script": False,
                      "detail": "CLI could not be executed"}
    record = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(), **result}
    encoded = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
    log_fd = os.open(log_path, flags, 0o600, dir_fd=boot_fd)
    try:
        info = os.fstat(log_fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise SystemExit(2)
        if info.st_size > 262144:
            os.ftruncate(log_fd, 0)
        os.write(log_fd, encoded[:4096])
        os.fsync(log_fd)
    finally:
        os.close(log_fd)
    if result["outcome"] not in {"started", "already_running"}:
        raise SystemExit(1)
finally:
    os.close(lock_fd)
'''


class BootIntegrationError(ValueError):
    pass


def _paths(home: str | os.PathLike[str]) -> tuple[Path, Path]:
    home_path = Path(home).expanduser().resolve()
    termux = home_path / ".termux"
    boot = termux / "boot"
    for path in (termux, boot):
        if path.is_symlink():
            raise BootIntegrationError("Termux:Boot directory path contains a symbolic link")
        resolved = path.resolve()
        if resolved == home_path or home_path not in resolved.parents:
            raise BootIntegrationError("Termux:Boot directory resolves outside HOME")
        if path.exists() and not path.is_dir():
            raise BootIntegrationError("Termux:Boot path component is not a directory")
    return boot, boot / SCRIPT_NAME


def script_bytes() -> bytes:
    return _SCRIPT.encode("utf-8")


def _read_owned_script(path: Path) -> tuple[str, bytes | None]:
    try:
        before = path.lstat()
    except FileNotFoundError:
        return "missing", None
    except OSError:
        return "unsafe", None
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        return "unsafe", None
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0))
        try:
            after = os.fstat(fd)
            if (not stat.S_ISREG(after.st_mode) or after.st_uid != os.getuid()
                    or stat.S_IMODE(after.st_mode) != 0o700
                    or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino)
                    or after.st_size > _MAX_SCRIPT):
                return "unsafe", None
            chunks: list[bytes] = []
            while True:
                part = os.read(fd, min(8192, _MAX_SCRIPT + 1))
                if not part:
                    break
                chunks.append(part)
                if sum(map(len, chunks)) > _MAX_SCRIPT:
                    return "mismatch", None
            data = b"".join(chunks)
        finally:
            os.close(fd)
    except OSError:
        return "unsafe", None
    if data == script_bytes():
        return "match", data
    if hashlib.sha256(data).hexdigest() in KNOWN_LEGACY_SCRIPT_HASHES:
        return "known-legacy", data
    return "mismatch", data


def _save_legacy_snapshot(home: str | os.PathLike[str], state_dir: str | os.PathLike[str],
                          data: bytes) -> dict[str, str]:
    home_path, state = boot_state_path.resolve_private_state(str(home), str(state_dir))
    state_fd = boot_state_path.ensure_private_tree(home_path, state)
    os.close(state_fd)
    snapshots = state / "cron" / "boot" / "snapshots"
    try:
        snapshots.mkdir(mode=0o700)
    except FileExistsError:
        pass
    info = snapshots.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700):
        raise BootIntegrationError("Cron boot snapshot directory is unsafe")
    digest = hashlib.sha256(data).hexdigest()
    snapshot = snapshots / f"{SCRIPT_NAME}-{digest}.bin"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(snapshot, flags, 0o600)
    except FileExistsError:
        existing = snapshot.lstat()
        if (not stat.S_ISREG(existing.st_mode) or existing.st_uid != os.getuid()
                or stat.S_IMODE(existing.st_mode) != 0o600
                or hashlib.sha256(snapshot.read_bytes()).hexdigest() != digest):
            raise BootIntegrationError("existing Cron boot snapshot failed integrity checks")
    else:
        try:
            os.fchmod(fd, 0o600)
            view = memoryview(data)
            while view:
                count = os.write(fd, view)
                if count <= 0:
                    raise OSError("short Cron boot snapshot write")
                view = view[count:]
            os.fsync(fd)
        except Exception:
            os.close(fd)
            snapshot.unlink(missing_ok=True)
            raise
        else:
            os.close(fd)
        directory_fd = os.open(snapshots, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    return {"sha256": digest, "path": str(snapshot.relative_to(home_path))}


def _replace_script_atomically(path: Path, data: bytes) -> None:
    fd, temporary_name = tempfile.mkstemp(prefix=f".{SCRIPT_NAME}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(fd, 0o700)
        view = memoryview(data)
        while view:
            count = os.write(fd, view)
            if count <= 0:
                raise OSError("short Cron boot script write")
            view = view[count:]
        os.fsync(fd)
        os.close(fd)
        fd = -1
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if fd >= 0:
            os.close(fd)
        temporary.unlink(missing_ok=True)


def _latest_run(state_dir: str | os.PathLike[str]) -> dict[str, object] | None:
    path = Path(state_dir) / "cron/boot/termux-boot-cron.jsonl"
    try:
        info = path.lstat()
        if (path.is_symlink() or not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077):
            return None
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            os.lseek(fd, max(0, info.st_size - 8192), os.SEEK_SET)
            text = os.read(fd, 8192).decode("utf-8", "replace")
        finally:
            os.close(fd)
        for line in reversed(text.splitlines()):
            data = json.loads(line)
            if isinstance(data, dict) and data.get("outcome") in {
                    "started", "already_running", "start_failed", "start_timeout", "cli_unavailable"}:
                return data
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return None


def status(*, home: str | os.PathLike[str], state_dir: str | os.PathLike[str],
           boot_inspector: Callable[..., dict[str, object]] = runtime_diagnostics.inspect_boot,
           scheduler_inspector: Callable[[str], dict[str, object]] = cron_scheduler.status) -> dict[str, object]:
    boot_dir, script_path = _paths(home)
    identity, _ = _read_owned_script(script_path)
    app_data = boot_inspector(home=home)
    app = app_data.get("app", "unknown")
    companion = "confirmed_installed" if app == "installed" else "confirmed_not_installed" if app == "not_installed" else "unknown"
    last_run = _latest_run(state_dir)
    try:
        scheduler = scheduler_inspector(str(state_dir))
    except Exception:
        scheduler = {"status": "unknown", "process_alive": None, "dispatch_healthy": None}
    return {
        "component": "termux_boot_cron_integration",
        "integration_state": "script_configured" if identity == "match" else "integration_not_configured" if identity == "missing" else "unsafe_or_mismatched",
        "script_path": str(script_path), "script_identity": identity,
        "companion_app": companion, "companion_package": "com.termux.boot",
        "companion_app_enabled": app_data.get("package_enabled", "unknown"),
        "boot_completed_receiver": app_data.get("boot_completed_receiver", "unknown"),
        "last_script_result": last_run,
        "scheduler_started_by_script": bool(last_run and last_run.get("outcome") == "started"
            and last_run.get("started_by_script") is True
            and scheduler.get("status") == "running"
            and scheduler.get("instance_id") == last_run.get("scheduler_instance_id")),
        "scheduler_state": scheduler.get("status", "unknown"),
        "scheduler_process_alive": scheduler.get("process_alive"),
        "actual_device_boot_delivery": "not_yet_verified",
        "owner_action_required": "Install Termux:Boot from a compatible source and open it once manually if it is not already installed and initialized.",
        "safety": {"read_only": True, "package_changed": False, "unrelated_scripts_changed": False},
        "boot_directory": str(boot_dir),
    }


def validate(*, home: str | os.PathLike[str], state_dir: str | os.PathLike[str],
             prefix: str = PREFIX, boot_inspector: Callable[..., dict[str, object]] = runtime_diagnostics.inspect_boot) -> dict[str, object]:
    boot_dir, script_path = _paths(home)
    identity, _ = _read_owned_script(script_path)
    app_data = boot_inspector(home=home)
    app = app_data.get("app", "unknown")
    blockers: list[str] = []
    if prefix != PREFIX:
        blockers.append("Native Termux prefix is unavailable")
    if not (Path(home) / "ternuxx" / "tx").is_file():
        blockers.append("Ternuxx tx entrypoint is unavailable")
    if identity in {"unsafe", "mismatch"}:
        blockers.append("the dedicated target path is not a verified Ternuxx script")
    if identity == "known-legacy":
        blockers.append("the dedicated script is an older verified Ternuxx version and needs reconciliation")
    if identity == "missing":
        blockers.append("the dedicated script is not configured")
    if app != "installed":
        blockers.append("Termux:Boot is not confirmed installed (package visibility may be denied)")
    return {"component": "termux_boot_cron_validation", "valid": not blockers,
            "script_identity": identity, "companion_app": "confirmed_installed" if app == "installed" else "confirmed_not_installed" if app == "not_installed" else "unknown",
            "blockers": blockers, "actual_device_boot_delivery": "not_yet_verified",
            "side_effects": False, "script_path": str(script_path), "boot_directory": str(boot_dir)}


def _plan(action: str, path: Path, current: bytes | None) -> dict[str, object]:
    desired = script_bytes() if action == "enable" else None
    plan_data = {"action": action, "path": str(path),
                 "current_sha256": hashlib.sha256(current).hexdigest() if current is not None else None,
                 "desired_sha256": hashlib.sha256(desired).hexdigest() if desired is not None else None,
                 "mode": "0700" if desired is not None else None}
    identifier = hashlib.sha256(json.dumps(plan_data, sort_keys=True).encode()).hexdigest()[:24]
    return {"plan_id": identifier, **plan_data}


def preview(action: str, *, home: str | os.PathLike[str],
            boot_inspector: Callable[..., dict[str, object]] = runtime_diagnostics.inspect_boot) -> dict[str, object]:
    if action not in {"enable", "disable"}:
        raise BootIntegrationError("unsupported boot integration action")
    boot_dir, path = _paths(home)
    identity, current = _read_owned_script(path)
    if action == "enable" and identity not in {"missing", "match", "known-legacy"}:
        raise BootIntegrationError("refusing to replace an unsafe or unrecognized startup file")
    if action == "disable" and identity not in {"missing", "match"}:
        raise BootIntegrationError("refusing to remove an unsafe or unrecognized startup file")
    app = boot_inspector(home=home).get("app", "unknown")
    plan = _plan(action, path, current)
    changed = (action == "enable" and identity in {"missing", "known-legacy"}) or (action == "disable" and identity == "match")
    blockers = []
    if action == "enable" and app != "installed":
        blockers.append("Termux:Boot must be positively confirmed installed before enabling")
    return {"component": "termux_boot_cron_preview", "action": action,
            "target": str(path), "boot_directory": str(boot_dir), "changes": ([{"operation": "replace" if identity == "known-legacy" else "create", "path": str(path), "mode": "0700", "current_sha256": plan["current_sha256"], "sha256": plan["desired_sha256"]}] if changed and action == "enable" else [{"operation": "remove", "path": str(path), "sha256": plan["current_sha256"]}] if changed else []),
            "plan_id": plan["plan_id"], "script_identity": identity,
            "companion_app": "confirmed_installed" if app == "installed" else "confirmed_not_installed" if app == "not_installed" else "unknown",
            "requires_confirmation": changed, "changed": False, "ready": not blockers,
            "blockers": blockers, "side_effects": False,
            "preserves_unrelated_boot_scripts": True,
            "actual_device_boot_delivery": "not_yet_verified"}


def _apply_unlocked(action: str, *, home: str | os.PathLike[str], state_dir: str | os.PathLike[str],
                    confirmed: bool, plan_id: str | None,
                    boot_inspector: Callable[..., dict[str, object]] = runtime_diagnostics.inspect_boot) -> dict[str, object]:
    plan = preview(action, home=home, boot_inspector=boot_inspector)
    if not plan["ready"]:
        raise BootIntegrationError("Termux:Boot is not confirmed installed")
    if not confirmed:
        return {**plan, "requires_confirmation": True, "changed": False}
    if not isinstance(plan_id, str) or plan_id != plan["plan_id"]:
        raise BootIntegrationError("preview plan is missing or stale; inspect a fresh preview before confirming")
    path = Path(str(plan["target"]))
    boot_dir = path.parent
    created: list[Path] = []
    if action == "enable" and not boot_dir.exists():
        termux_dir = boot_dir.parent
        if not termux_dir.exists():
            termux_dir.mkdir(mode=0o700)
            created.append(termux_dir)
        boot_dir.mkdir(mode=0o700)
        created.append(boot_dir)
    identity, current = _read_owned_script(path)
    rollback_snapshot = None
    if action == "enable":
        if identity == "match":
            return {**plan, "requires_confirmation": False, "changed": False, "already_configured": True}
        if identity == "known-legacy" and current is not None:
            rollback_snapshot = _save_legacy_snapshot(home, state_dir, current)
            _replace_script_atomically(path, script_bytes())
        elif identity != "missing":
            raise BootIntegrationError("target changed after preview; refusing to overwrite")
        else:
            data = script_bytes()
            try:
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o700)
                try:
                    os.fchmod(fd, 0o700)
                    view = memoryview(data)
                    while view:
                        written = os.write(fd, view)
                        if written <= 0:
                            raise OSError("short boot script write")
                        view = view[written:]
                    os.fsync(fd)
                    created_identity = os.fstat(fd)
                finally:
                    os.close(fd)
            except Exception:
                try:
                    current_meta = path.lstat()
                    if ("created_identity" in locals()
                            and (current_meta.st_dev, current_meta.st_ino) == (created_identity.st_dev, created_identity.st_ino)):
                        path.unlink()
                except OSError:
                    pass
                for directory in reversed(created):
                    try: directory.rmdir()
                    except OSError: pass
                raise
            parent_fd = os.open(boot_dir, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
    else:
        if identity == "missing":
            return {**plan, "requires_confirmation": False, "changed": False, "already_disabled": True}
        if identity != "match" or current != script_bytes():
            raise BootIntegrationError("target changed after preview; refusing to remove")
        before = path.lstat()
        identity_again, current_again = _read_owned_script(path)
        after = path.lstat()
        if (identity_again != "match" or current_again != script_bytes()
                or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino)):
            raise BootIntegrationError("target identity changed before removal; refusing to unlink")
        path.unlink()
    return {**plan, "requires_confirmation": False, "changed": True,
            **({"rollback_snapshot": rollback_snapshot} if rollback_snapshot else {}),
            "actual_device_boot_delivery": "not_yet_verified",
            "safety": {"unrelated_boot_scripts_changed": False, "package_changed": False,
                       "scheduler_started": False}}


def apply(action: str, *, home: str | os.PathLike[str], state_dir: str | os.PathLike[str],
          confirmed: bool, plan_id: str | None,
          boot_inspector: Callable[..., dict[str, object]] = runtime_diagnostics.inspect_boot) -> dict[str, object]:
    """Serialize entrypoint changes with each other and the Termux:Boot runner."""
    if not confirmed:
        return _apply_unlocked(action, home=home, state_dir=state_dir, confirmed=False,
                               plan_id=plan_id, boot_inspector=boot_inspector)
    try:
        home_path, state = boot_state_path.resolve_private_state(str(home), str(state_dir))
        directory_fd = boot_state_path.ensure_private_tree(home_path, state)
    except (OSError, ValueError) as exc:
        raise BootIntegrationError("private boot state is unavailable or unsafe") from exc
    lock_fd = -1
    try:
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        lock_fd = os.open("entry.lock", flags, 0o600, dir_fd=directory_fd)
        info = os.fstat(lock_fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600):
            raise BootIntegrationError("Cron boot entry lock identity or permissions are unsafe")
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        return _apply_unlocked(action, home=home_path, state_dir=state, confirmed=confirmed,
                               plan_id=plan_id, boot_inspector=boot_inspector)
    except OSError as exc:
        raise BootIntegrationError("could not safely acquire the Cron boot entry lock") from exc
    finally:
        if lock_fd >= 0:
            os.close(lock_fd)
        os.close(directory_fd)
