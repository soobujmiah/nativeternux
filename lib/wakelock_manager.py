"""Persistent owner coordination for Termux's app-global Wake Lock command.

The Android lock itself remains global. This module coordinates only Ternuxx
workloads that register a lease; it cannot observe or arbitrate unrelated
Termux clients.
"""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
from typing import Callable

import continuity


OWNER_RE = re.compile(r"^[a-z][a-z0-9_.-]{1,63}$")
PERSISTENT_OWNERS = {"native.sshd"}
MAX_OWNERS = 64


class WakeLockError(Exception):
    """Safe-to-report state, validation, or platform-command failure."""


def _root(state_dir: str | os.PathLike[str]) -> Path:
    base = Path(state_dir).expanduser()
    if base.is_symlink():
        raise WakeLockError("Wake Lock state path must not be a symbolic link")
    return base / "wakelock"


def _boot_id() -> str | None:
    return continuity.read_boot_id()


def _pid_is_absent(pid: int) -> bool:
    """Confirm absence through the kernel before pruning an unreadable lease."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except OSError:
        return False
    return False


def _process_start(pid: int) -> str | None:
    try:
        data = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
        closing = data.rfind(")")
        if closing < 0:
            return None
        fields_from_state = data[closing + 2 :].split()
        return fields_from_state[19]
    except (OSError, IndexError, UnicodeError):
        return None


def _parent_pid(pid: int) -> int | None:
    try:
        data = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
        closing = data.rfind(")")
        if closing < 0:
            return None
        return int(data[closing + 2 :].split()[1])
    except (OSError, IndexError, ValueError, UnicodeError):
        return None


def is_ancestor(candidate_pid: int, process_pid: int) -> bool:
    """Return true only when candidate is in the caller's live parent chain."""
    if type(candidate_pid) is not int or candidate_pid <= 1:
        return False
    current = process_pid
    for _ in range(8):
        current = _parent_pid(current)
        if current is None or current <= 1:
            return False
        if current == candidate_pid:
            return True
    return False


def _validate_owner(owner: object) -> str:
    if not isinstance(owner, str) or not OWNER_RE.fullmatch(owner):
        raise WakeLockError("owner ID is malformed")
    return owner


def _ensure_root(root: Path) -> None:
    continuity._ensure_private_dir(root)


@contextmanager
def _locked(root: Path):
    _ensure_root(root)
    path = root / ".manager.lock"
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o077:
            raise WakeLockError("Wake Lock state lock is not a private regular file")
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _read(root: Path) -> dict[str, object]:
    path = root / "owners.json"
    if not path.exists():
        return {"schema_version": 1, "boot_id": _boot_id(), "owners": {}, "last_error": None}
    try:
        if path.is_symlink() or stat.S_IMODE(path.stat(follow_symlinks=False).st_mode) & 0o077:
            raise WakeLockError("Wake Lock state is not private")
        if path.stat().st_size > 32 * 1024:
            raise WakeLockError("Wake Lock state exceeds its size limit")
        value = json.loads(path.read_text(encoding="utf-8"))
    except WakeLockError:
        raise
    except (OSError, ValueError, TypeError) as exc:
        raise WakeLockError("Wake Lock state is unavailable or invalid") from exc
    if not isinstance(value, dict) or set(value) != {"schema_version", "boot_id", "owners", "last_error"}:
        raise WakeLockError("Wake Lock state schema is unsupported")
    if value["schema_version"] != 1 or not isinstance(value["owners"], dict) or len(value["owners"]) > MAX_OWNERS:
        raise WakeLockError("Wake Lock state schema is unsupported")
    for owner, lease in value["owners"].items():
        _validate_owner(owner)
        if not isinstance(lease, dict) or set(lease) != {"pid", "process_start", "persistent", "reason"}:
            raise WakeLockError("Wake Lock owner record is invalid")
        if lease["persistent"] is True:
            if owner not in PERSISTENT_OWNERS or type(lease["pid"]) is not int or lease["pid"] <= 1 or not isinstance(lease["process_start"], str):
                raise WakeLockError("persistent Wake Lock owner is invalid")
        elif type(lease["pid"]) is not int or lease["pid"] <= 1 or not isinstance(lease["process_start"], str):
            raise WakeLockError("process Wake Lock owner is invalid")
        if not isinstance(lease["reason"], str) or len(lease["reason"]) > 120:
            raise WakeLockError("Wake Lock owner reason is invalid")
    if value["boot_id"] is not None and not isinstance(value["boot_id"], str):
        raise WakeLockError("Wake Lock boot identity is invalid")
    return value


def _write(root: Path, state: dict[str, object]) -> None:
    _ensure_root(root)
    fd = -1
    temporary = ""
    try:
        fd, temporary = tempfile.mkstemp(prefix=".owners-", dir=root)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            fd = -1
            json.dump(state, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, root / "owners.json")
        temporary = ""
        directory_fd = os.open(root, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError as exc:
        raise WakeLockError(f"cannot persist Wake Lock ownership ({exc.__class__.__name__})") from exc
    finally:
        if fd >= 0:
            os.close(fd)
        if temporary:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def _run(command: str, runner: Callable[..., subprocess.CompletedProcess[str]]) -> None:
    try:
        result = runner([command], capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WakeLockError(f"Termux Wake Lock command failed ({exc.__class__.__name__})") from exc
    if result.returncode != 0:
        raise WakeLockError("Termux Wake Lock command returned failure")



_SERVICE_POLICY_FILE = "service-policy.json"


def _service_policy_snapshot(root: Path) -> tuple[bool, tuple[object, ...]]:
    path = root / _SERVICE_POLICY_FILE
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(path, flags)
    except FileNotFoundError:
        return True, ("absent-default-enabled",)
    except OSError as exc:
        raise WakeLockError("managed SSH Wake Lock policy cannot be opened safely") from exc
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) & 0o077 or info.st_size > 4096):
            raise WakeLockError("managed SSH Wake Lock policy file identity is not verified")
        raw = os.read(fd, 4097)
        if len(raw) > 4096:
            raise WakeLockError("managed SSH Wake Lock policy file exceeds its size limit")
    finally:
        os.close(fd)
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError, TypeError) as exc:
        raise WakeLockError("managed SSH Wake Lock policy is invalid") from exc
    if (not isinstance(value, dict) or set(value) != {"schema_version", "native_sshd_enabled"}
            or value["schema_version"] != 1 or type(value["native_sshd_enabled"]) is not bool):
        raise WakeLockError("managed SSH Wake Lock policy schema is unsupported")
    identity = ("present", info.st_dev, info.st_ino, info.st_mode, info.st_uid,
                info.st_size, info.st_mtime_ns, hashlib.sha256(raw).hexdigest())
    return value["native_sshd_enabled"], identity


def _service_policy_plan_id(root: Path, enabled: bool, identity: tuple[object, ...]) -> str:
    material = repr(("native-sshd-wakelock-policy-v1", os.getuid(), str(root), identity, enabled)).encode()
    return hashlib.sha256(material).hexdigest()[:32]


def service_policy_status(*, state_dir: str | os.PathLike[str]) -> dict[str, object]:
    root = _root(state_dir)
    if root.is_symlink():
        raise WakeLockError("Wake Lock state directory must not be a symbolic link")
    if not root.exists():
        enabled = True
        identity = ("absent-default-enabled",)
    else:
        with _locked(root):
            enabled, identity = _service_policy_snapshot(root)
    return {"component": "wakelock_manager", "service": "native.sshd",
            "persistent_lease_enabled": enabled,
            "configured": identity[0] == "present",
            "default": True, "applies_at": "next managed SSH service start",
            "current_service_lease_changed": False,
            "platform_lock_state": "unknown"}


def service_policy_preview(*, state_dir: str | os.PathLike[str], enabled: bool) -> dict[str, object]:
    if type(enabled) is not bool:
        raise WakeLockError("enabled must be a boolean")
    root = _root(state_dir)
    if root.is_symlink():
        raise WakeLockError("Wake Lock state directory must not be a symbolic link")
    if not root.exists():
        current, identity = True, ("absent-default-enabled",)
    else:
        with _locked(root):
            current, identity = _service_policy_snapshot(root)
    changed = current != enabled
    return {"component": "wakelock_manager", "service": "native.sshd",
            "currently_enabled": current, "requested_enabled": enabled,
            "changed": changed, "requires_confirmation": changed,
            "plan_id": _service_policy_plan_id(root, enabled, identity) if changed else None,
            "effect": "The managed SSH service will acquire or skip its persistent Wake Lock lease on its next start. The running service and its current lease are unchanged.",
            "platform_lock_state": "unknown"}


def _write_service_policy(root: Path, enabled: bool) -> None:
    fd = -1
    temporary = ""
    try:
        fd, temporary = tempfile.mkstemp(prefix=".service-policy-", dir=root)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            fd = -1
            json.dump({"schema_version": 1, "native_sshd_enabled": enabled}, stream,
                      sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, root / _SERVICE_POLICY_FILE)
        temporary = ""
        directory_fd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError as exc:
        raise WakeLockError(f"cannot persist managed SSH Wake Lock policy ({exc.__class__.__name__})") from exc
    finally:
        if fd >= 0:
            os.close(fd)
        if temporary:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def service_policy_apply(*, state_dir: str | os.PathLike[str], enabled: bool,
                         confirmed: bool, plan_id: str) -> dict[str, object]:
    if type(enabled) is not bool:
        raise WakeLockError("enabled must be a boolean")
    root = _root(state_dir)
    with _locked(root):
        current, identity = _service_policy_snapshot(root)
        changed = current != enabled
        plan = {"component": "wakelock_manager", "service": "native.sshd",
                "currently_enabled": current, "requested_enabled": enabled,
                "changed": changed, "requires_confirmation": changed,
                "plan_id": _service_policy_plan_id(root, enabled, identity) if changed else None,
                "effect": "The managed SSH service will acquire or skip its persistent Wake Lock lease on its next start. The running service and its current lease are unchanged.",
                "platform_lock_state": "unknown"}
        if not changed:
            return plan
        if not confirmed:
            return {**plan, "status": "confirmation_required"}
        if not isinstance(plan_id, str) or plan_id != plan["plan_id"]:
            return {**plan, "changed": False, "status": "stale_plan"}
        _write_service_policy(root, enabled)
        return {**plan, "status": "updated", "configured": True,
                "current_service_lease_changed": False}


def status(*, state_dir: str | os.PathLike[str], which: Callable[[str], str | None] = shutil.which) -> dict[str, object]:
    root = _root(state_dir)
    if root.is_symlink():
        raise WakeLockError("Wake Lock state directory must not be a symbolic link")
    if not root.exists():
        state = {"schema_version": 1, "boot_id": _boot_id(), "owners": {}, "last_error": None}
    else:
        with _locked(root):
            state = _read(root)
    current_boot = _boot_id()
    owners = state["owners"]
    if state["boot_id"] is None or current_boot is None:
        boot_id_relation = "unknown"
    elif state["boot_id"] == current_boot:
        boot_id_relation = "match"
    else:
        boot_id_relation = "different"
    stale_boot = boot_id_relation == "different"
    active = []
    stale = []
    unknown = []
    for owner, lease in owners.items():
        if stale_boot:
            stale.append(owner)
        else:
            observed_start = _process_start(lease["pid"])
            if observed_start is None:
                unknown.append(owner)
            elif observed_start == lease["process_start"]:
                active.append(owner)
            else:
                stale.append(owner)
    return {
        "component": "wakelock_manager",
        "managed_owners": sorted(active),
        "stale_owners": sorted(stale),
        "unknown_owners": sorted(unknown),
        "owner_count": len(active),
        "coordinator_state": "held_by_registered_owners" if active else "no_active_registered_owners",
        "platform_lock_state": "unknown",
        "ownership_scope": "Ternuxx_registered_owners_only; Android lock remains app_global",
        "boot_id_relation": boot_id_relation,
        "acquire_command_available": which("termux-wake-lock") is not None,
        "release_command_available": which("termux-wake-unlock") is not None,
        "last_error": state["last_error"],
        "safety": {"read_only": True, "acquire_or_release_invoked": False},
    }


def acquire(
    *, state_dir: str | os.PathLike[str], owner: str, persistent: bool = False,
    caller_pid: int | None = None, prefix: str, runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    owner = _validate_owner(owner)
    if type(persistent) is not bool or (persistent and owner not in PERSISTENT_OWNERS):
        raise WakeLockError("persistent leases are restricted to approved native services")
    pid = os.getppid() if caller_pid is None else caller_pid
    process_start = _process_start(pid)
    if type(pid) is not int or pid <= 1 or process_start is None:
        raise WakeLockError("caller process identity could not be verified")
    root = _root(state_dir)
    wake_command = str(Path(prefix) / "bin/termux-wake-lock")
    unlock_command = str(Path(prefix) / "bin/termux-wake-unlock")
    with _locked(root):
        state = _read(root)
        if persistent and owner == "native.sshd":
            policy_enabled, _policy_identity = _service_policy_snapshot(root)
            if not policy_enabled:
                return {"owner": owner, "state": "policy_disabled", "owner_count": len(state["owners"])}
        current_boot = _boot_id()
        if state["boot_id"] is not None and current_boot is not None and state["boot_id"] != current_boot:
            state = {"schema_version": 1, "boot_id": current_boot, "owners": {}, "last_error": None}
        owners = state["owners"]
        existing = owners.get(owner)
        if existing is not None:
            observed_start = _process_start(existing["pid"])
            if observed_start is None:
                if _pid_is_absent(existing["pid"]):
                    del owners[owner]
                    existing = None
                else:
                    raise WakeLockError("existing owner process identity is unavailable")
            if existing is not None:
                existing_alive = observed_start == existing["process_start"]
                if existing["persistent"] == persistent and existing["pid"] == pid and existing["process_start"] == process_start:
                    return {"owner": owner, "state": "already_acquired", "owner_count": len(owners)}
                if not existing_alive:
                    del owners[owner]
                else:
                    raise WakeLockError("owner ID is already leased by another process")
        # Remove dead process leases. Persistent service leases survive process
        # restarts until the service manager explicitly releases them.
        for old_owner, lease in list(owners.items()):
            observed_start = _process_start(lease["pid"])
            if observed_start is None:
                if _pid_is_absent(lease["pid"]):
                    del owners[old_owner]
                    continue
                raise WakeLockError("an existing owner process could not be inspected")
            if observed_start != lease["process_start"]:
                del owners[old_owner]
        if len(owners) >= MAX_OWNERS:
            raise WakeLockError("Wake Lock owner limit reached")
        if not owners:
            _run(wake_command, runner)
        owners[owner] = {"pid": pid,
                         "process_start": process_start,
                         "persistent": persistent,
                         "reason": "native_sshd" if persistent else owner}
        state["boot_id"] = current_boot
        state["owners"] = owners
        state["last_error"] = None
        _write(root, state)
    return {"owner": owner, "state": "acquired", "owner_count": len(owners)}


def release(
    *, state_dir: str | os.PathLike[str], owner: str, persistent: bool = False,
    caller_pid: int | None = None, prefix: str, runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    owner = _validate_owner(owner)
    if type(persistent) is not bool or (persistent and owner not in PERSISTENT_OWNERS):
        raise WakeLockError("persistent leases are restricted to approved native services")
    pid = os.getppid() if caller_pid is None else caller_pid
    process_start = _process_start(pid)
    root = _root(state_dir)
    with _locked(root):
        state = _read(root)
        current_boot = _boot_id()
        if state["boot_id"] is not None and current_boot is not None and state["boot_id"] != current_boot:
            state = {"schema_version": 1, "boot_id": current_boot, "owners": {}, "last_error": None}
            _write(root, state)
            return {"owner": owner, "state": "stale_boot_lease_cleared", "owner_count": 0}
        for old_owner, old_lease in list(state["owners"].items()):
            observed_start = _process_start(old_lease["pid"])
            if observed_start is None:
                raise WakeLockError("an existing owner process could not be inspected")
            if observed_start != old_lease["process_start"]:
                del state["owners"][old_owner]
        lease = state["owners"].get(owner)
        if lease is None:
            return {"owner": owner, "state": "not_owned", "owner_count": len(state["owners"])}
        if lease["persistent"] != persistent or lease["pid"] != pid or lease["process_start"] != process_start:
            raise WakeLockError("caller does not own this Wake Lock lease")
        del state["owners"][owner]
        if state["owners"]:
            _write(root, state)
            return {"owner": owner, "state": "released_lease_lock_retained", "owner_count": len(state["owners"])}
        _write(root, state)
        _run(str(Path(prefix) / "bin/termux-wake-unlock"), runner)
        return {"owner": owner, "state": "released_last_registered_lease", "owner_count": 0}
