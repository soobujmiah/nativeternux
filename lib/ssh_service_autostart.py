"""Preview-first Termux runit autostart policy for the owned SSH unit."""
from __future__ import annotations

import fcntl
import hashlib
import os
from pathlib import Path
import stat

import ssh_diagnostics


_PREFIX = "/data/data/com.termux/files/usr"
_SERVICE = "ternuxx-sshd"


class AutostartPolicyError(RuntimeError):
    pass


def _inspect_state(home: str | os.PathLike[str], state_dir: str | os.PathLike[str],
           prefix: str, uid: int) -> tuple[Path, Path, Path, tuple[object, ...]]:
    if prefix != _PREFIX:
        raise AutostartPolicyError("Native Termux prefix is not verified")
    home_path = Path(home)
    state_path = Path(state_dir)
    service_dir = Path(prefix) / "var/service" / _SERVICE
    try:
        home_info = home_path.lstat()
        service_info = service_dir.lstat()
        parent_info = service_dir.parent.lstat()
        state_info = state_path.lstat()
    except OSError as exc:
        raise AutostartPolicyError("Native SSH service or state directory is unavailable") from exc
    if not home_path.is_absolute() or stat.S_ISLNK(home_info.st_mode) or not stat.S_ISDIR(home_info.st_mode) or home_info.st_uid != uid:
        raise AutostartPolicyError("Native home identity is not verified")
    if (stat.S_ISLNK(parent_info.st_mode) or not stat.S_ISDIR(parent_info.st_mode)
            or parent_info.st_uid != uid):
        raise AutostartPolicyError("Native Runit service directory identity is not verified")
    if (stat.S_ISLNK(service_info.st_mode) or not stat.S_ISDIR(service_info.st_mode)
            or service_info.st_uid != uid or stat.S_IMODE(service_info.st_mode) & 0o077):
        raise AutostartPolicyError("Ternuxx SSH service directory identity is not verified")
    if (stat.S_ISLNK(state_info.st_mode) or not stat.S_ISDIR(state_info.st_mode)
            or state_info.st_uid != uid or stat.S_IMODE(state_info.st_mode) & 0o077):
        raise AutostartPolicyError("Ternuxx private state directory identity is not verified")
    run = service_dir / "run"
    try:
        run_info = run.lstat()
    except OSError as exc:
        raise AutostartPolicyError("Ternuxx SSH service run definition is missing") from exc
    if (stat.S_ISLNK(run_info.st_mode) or not stat.S_ISREG(run_info.st_mode)
            or run_info.st_uid != uid or stat.S_IMODE(run_info.st_mode) & 0o077):
        raise AutostartPolicyError("Ternuxx SSH run definition identity is not verified")
    definition = ssh_diagnostics._managed_service_definition_identity(Path(prefix))
    if definition.get("status") != "verified":
        raise AutostartPolicyError("Installed Ternuxx SSH service definition does not match Native source")
    down = service_dir / "down"
    try:
        down_info = down.lstat()
        if (stat.S_ISLNK(down_info.st_mode) or not stat.S_ISREG(down_info.st_mode)
                or down_info.st_uid != uid or down_info.st_size != 0):
            raise AutostartPolicyError("Runit down marker is not an owned empty regular file")
        down_identity: tuple[object, ...] = ("present", down_info.st_dev, down_info.st_ino,
                                             down_info.st_mode, down_info.st_uid, down_info.st_size)
    except FileNotFoundError:
        down_identity = ("absent",)
    except OSError as exc:
        raise AutostartPolicyError("Runit down marker cannot be inspected safely") from exc
    identity = (home_info.st_dev, home_info.st_ino, parent_info.st_dev, parent_info.st_ino,
                service_info.st_dev, service_info.st_ino, run_info.st_dev, run_info.st_ino,
                down_identity, definition.get("source_sha256"), definition.get("installed_sha256"))
    return service_dir, down, state_path, identity


def status(*, home: str | os.PathLike[str], state_dir: str | os.PathLike[str],
           prefix: str, uid: int) -> dict[str, object]:
    _service_dir, _down, _state, identity = _inspect_state(home, state_dir, prefix, uid)
    enabled = identity[-3][0] == "absent"
    return {"component": "ssh_service_autostart", "status": "enabled" if enabled else "disabled",
            "enabled": enabled, "service": _SERVICE, "policy_source": "Runit down marker",
            "runtime_effect": "none; existing SSH process state is unchanged",
            "next_supervisor_start": "start service" if enabled else "keep service down"}


def preview(*, enabled: bool, home: str | os.PathLike[str],
            state_dir: str | os.PathLike[str], prefix: str, uid: int) -> dict[str, object]:
    if type(enabled) is not bool:
        raise AutostartPolicyError("enabled must be a boolean")
    service_dir, down, _state_path, identity = _inspect_state(home, state_dir, prefix, uid)
    current = identity[-3][0] == "absent"
    changed = current != enabled
    material = repr(("ssh-autostart-v1", uid, str(service_dir), identity, enabled)).encode()
    plan_id = hashlib.sha256(material).hexdigest()[:32] if changed else None
    return {"component": "ssh_service_autostart", "status": "ready" if changed else "unchanged",
            "service": _SERVICE, "currently_enabled": current, "requested_enabled": enabled,
            "changed": changed, "requires_confirmation": changed, "plan_id": plan_id,
            "target": str(down), "effect": "changes only whether Runit starts this service at the next supervisor start; current service state is unchanged",
            "secret_values_returned": False}


def apply(*, enabled: bool, confirmed: bool, plan_id: str,
          home: str | os.PathLike[str], state_dir: str | os.PathLike[str],
          prefix: str, uid: int) -> dict[str, object]:
    if type(enabled) is not bool:
        raise AutostartPolicyError("enabled must be a boolean")
    state_path = Path(state_dir)
    lock_path = state_path / "ssh-autostart.lock"
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        lock_fd = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise AutostartPolicyError("could not acquire the private SSH startup-policy lock") from exc
    try:
        lock_info = os.fstat(lock_fd)
        if not stat.S_ISREG(lock_info.st_mode) or lock_info.st_uid != uid:
            raise AutostartPolicyError("SSH startup-policy lock identity is not verified")
        os.fchmod(lock_fd, 0o600)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        plan = preview(enabled=enabled, home=home, state_dir=state_dir, prefix=prefix, uid=uid)
        if not plan["changed"]:
            return plan
        if not confirmed:
            return {**plan, "status": "confirmation_required"}
        if not isinstance(plan_id, str) or plan_id != plan["plan_id"]:
            return {**plan, "status": "stale_plan", "changed": False}
        service_dir, down, _state, current_identity = _inspect_state(home, state_dir, prefix, uid)
        expected_down = current_identity[-3]
        dir_fd = os.open(service_dir, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
        try:
            opened_dir = os.fstat(dir_fd)
            if (opened_dir.st_dev, opened_dir.st_ino) != current_identity[4:6]:
                raise AutostartPolicyError("Runit service directory changed during the operation")
            if enabled:
                marker_info = os.stat("down", dir_fd=dir_fd, follow_symlinks=False)
                marker_now = ("present", marker_info.st_dev, marker_info.st_ino,
                              marker_info.st_mode, marker_info.st_uid, marker_info.st_size)
                if marker_now != expected_down:
                    raise AutostartPolicyError("Runit down marker changed during the operation")
                # Removing Runit's fixed down sentinel permits autostart on the
                # next supervisor start. No current service is signalled here.
                os.unlink("down", dir_fd=dir_fd)
            else:
                if expected_down != ("absent",):
                    raise AutostartPolicyError("Runit down marker changed during the operation")
                marker_fd = os.open("down", os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                                    getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
                                    0o600, dir_fd=dir_fd)
                try:
                    os.fsync(marker_fd)
                finally:
                    os.close(marker_fd)
            os.fsync(dir_fd)
        except OSError as exc:
            raise AutostartPolicyError("Runit startup policy could not be changed safely") from exc
        finally:
            os.close(dir_fd)
        result = status(home=home, state_dir=state_dir, prefix=prefix, uid=uid)
        result.update({"changed": True, "status": "enabled" if enabled else "disabled",
                       "runtime_effect": "none; existing SSH process state was not signalled"})
        return result
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)
