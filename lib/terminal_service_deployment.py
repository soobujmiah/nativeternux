"""Preview-first Runit registration for fixed Ternuxx Native services.

The historical module name remains compatible with the terminal CLI. Service
selection is an explicit allowlist; it never accepts arbitrary run definitions
from management clients.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import time

SERVICE_ID = "ternuxx-terminal-broker"
MONITOR_SERVICE_ID = "ternuxx-gui-monitor"
SERVICE_IMPACTS = {
    SERVICE_ID: "Adds only the fixed Ternuxx terminal broker Runit service. Runit keeps the Native broker available; it does not start a PRoot guest, change Termux:Boot, or acquire a Wake Lock.",
    MONITOR_SERVICE_ID: "Adds only the fixed Ternuxx GUI monitor Runit scheduler. It delivers the existing saved monitoring policy; disabled policy stays idle. It does not enable monitoring, alter Activity/focus settings, change Termux:Boot, start a desktop/guest, or acquire a Wake Lock.",
}


class ServiceInstallError(RuntimeError):
    pass


def _service(service_id: str) -> str:
    if service_id not in SERVICE_IMPACTS:
        raise ServiceInstallError("unsupported fixed Ternuxx service")
    return service_id


def _source(source=None, service_id: str = SERVICE_ID) -> Path:
    _service(service_id)
    return Path(source) if source is not None else Path(__file__).resolve().parents[1] / "scripts/termux-services" / service_id / "run"


def _root(prefix) -> Path:
    path = Path(prefix) / "var/service"
    try:
        info = path.lstat()
    except OSError as exc:
        raise ServiceInstallError("Termux Runit service directory is unavailable") from exc
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o022):
        raise ServiceInstallError("Termux Runit service directory identity is unsafe")
    return path


def _read_executable(path: Path) -> bytes:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or info.st_mode & 0o022 or not info.st_mode & 0o100):
                raise ServiceInstallError("service executable identity is unsafe")
            return stream.read()
    except OSError as exc:
        raise ServiceInstallError("service executable is unavailable or unsafe") from exc


def _source_bytes(path: Path) -> bytes:
    content = _read_executable(path)
    if len(content) > 32768:
        raise ServiceInstallError("service source exceeds the supported size")
    syntax = subprocess.run(["bash", "-n"], input=content, capture_output=True, timeout=5, check=False)
    if syntax.returncode:
        raise ServiceInstallError("service source failed shell syntax validation")
    return content


def _target_state(target: Path) -> str:
    try:
        info = target.lstat()
    except FileNotFoundError:
        return "absent"
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o022):
        raise ServiceInstallError("service target identity is unsafe")
    names = {item.name for item in target.iterdir()}
    if names != {"supervise"}:
        raise ServiceInstallError("service target exists and is not an empty Runit supervisor")
    supervise = target / "supervise"
    sup_info = supervise.lstat()
    allowed = {"control", "ok", "lock", "pid", "stat", "status"}
    children = {item.name for item in supervise.iterdir()}
    if (not stat.S_ISDIR(sup_info.st_mode) or sup_info.st_uid != os.getuid()
            or sup_info.st_mode & 0o077 or children - allowed):
        raise ServiceInstallError("Runit supervisor state identity is unsafe")
    if not {"control", "ok"}.issubset(children):
        raise ServiceInstallError("Runit supervisor state is incomplete")
    return "runit-supervise-only"


def preview_install(*, prefix, source=None, service_id: str = SERVICE_ID) -> dict[str, object]:
    service_id = _service(service_id)
    root = _root(prefix)
    source_path = _source(source, service_id)
    content = _source_bytes(source_path)
    target = root / service_id
    state = _target_state(target)
    manager = Path(prefix) / "bin/sv"
    manager_content = _read_executable(manager)
    core = {"service_id": service_id, "target": str(target / "run"),
            "source": str(source_path), "source_sha256": hashlib.sha256(content).hexdigest(),
            "target_state": state, "service_manager_sha256": hashlib.sha256(manager_content).hexdigest()}
    plan_id = hashlib.sha256(json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {**core, "plan_id": plan_id, "requires_confirmation": True, "read_only": True,
            "impact": SERVICE_IMPACTS[service_id]}


@contextmanager
def _install_lock(root: Path, service_id: str):
    fd = os.open(root / ("." + service_id + ".install.lock"),
                 os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_nlink != 1):
            raise ServiceInstallError("service installation lock is unsafe")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ServiceInstallError("another installation holds this service lock") from exc
        yield
    finally:
        os.close(fd)


def _identity(info):
    return info.st_dev, info.st_ino


def _owns_run(target: Path, target_fd: int, owned_run) -> bool:
    if owned_run is None:
        return False
    try:
        current_target = target.lstat()
        current_run = os.stat("run", dir_fd=target_fd, follow_symlinks=False)
        return (stat.S_ISDIR(current_target.st_mode)
                and _identity(current_target) == _identity(os.fstat(target_fd))
                and stat.S_ISREG(current_run.st_mode)
                and _identity(current_run) == owned_run)
    except OSError:
        return False


def install(*, prefix, confirmed: bool, plan_id: str | None, source=None,
            runner=subprocess.run, service_id: str = SERVICE_ID) -> dict[str, object]:
    service_id = _service(service_id)
    if confirmed is not True:
        raise ServiceInstallError("explicit confirmation is required")
    root = _root(prefix)
    with _install_lock(root, service_id):
        plan = preview_install(prefix=prefix, source=source, service_id=service_id)
        if not isinstance(plan_id, str) or plan_id != plan["plan_id"]:
            raise ServiceInstallError("fresh exact service preview and plan ID are required")
        content = _source_bytes(_source(source, service_id))
        if hashlib.sha256(content).hexdigest() != plan["source_sha256"]:
            raise ServiceInstallError("service source changed after preview")
        target = root / service_id
        if _target_state(target) != plan["target_state"]:
            raise ServiceInstallError("service target changed after preview")
        target_fd = None
        owned_run = None
        created_target = None
        start_attempted = False
        try:
            if plan["target_state"] == "absent":
                target.mkdir(mode=0o700)
                created_target = _identity(target.lstat())
            target_fd = os.open(target, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
            info = os.fstat(target_fd)
            if (info.st_uid != os.getuid() or info.st_mode & 0o022
                    or created_target is not None and _identity(info) != created_target):
                raise ServiceInstallError("service target changed during registration")
            # Native Android Python has no os.link. Publish with O_EXCL at mode
            # 0600; Runit cannot execute it before the complete file is fsynced.
            fd = os.open("run", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                         0o600, dir_fd=target_fd)
            owned_run = _identity(os.fstat(fd))
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
                start_attempted = True  # runsv may discover the executable immediately.
                os.fchmod(stream.fileno(), 0o755)
                os.fsync(stream.fileno())
            os.fsync(target_fd)
            if not _owns_run(target, target_fd, owned_run):
                raise ServiceInstallError("published service identity changed")
            manager = Path(prefix) / "bin/sv"
            if hashlib.sha256(_read_executable(manager)).hexdigest() != plan["service_manager_sha256"]:
                raise ServiceInstallError("service manager changed after preview")
            target_path = str(target)
            start_attempted = True
            # runsvdir discovers new directories asynchronously (normally
            # within five seconds). Wait only for registration; a rejected
            # start after the supervisor exists remains a real failure.
            for attempt in range(60):
                result = runner([str(manager), "up", target_path], capture_output=True,
                                text=True, timeout=8, check=False)
                if result.returncode == 0:
                    break
                if (target / "supervise/ok").exists() or attempt == 59:
                    raise ServiceInstallError("Runit did not accept the service start")
                if not _owns_run(target, target_fd, owned_run):
                    raise ServiceInstallError("service identity changed while waiting for Runit")
                time.sleep(0.1)
            for _attempt in range(30):
                result = runner([str(manager), "status", target_path], capture_output=True,
                                text=True, timeout=5, check=False)
                line = (result.stdout or "").splitlines()
                if result.returncode == 0 and line and line[0].startswith(f"run: {target_path}:"):
                    if not _owns_run(target, target_fd, owned_run):
                        raise ServiceInstallError("running service definition identity changed")
                    return {"service_id": service_id, "status": "installed",
                            "source_sha256": plan["source_sha256"], "service_started": True,
                            "guest_started": False, "wakeup_enabled": False}
                time.sleep(0.1)
            raise ServiceInstallError("service did not reach the running state")
        except Exception as exc:
            # Never signal or remove a competing registration, even if its
            # bytes match ours. If stop fails, retain our definition for recovery.
            if target_fd is not None and _owns_run(target, target_fd, owned_run):
                stopped = not start_attempted
                if start_attempted:
                    try:
                        stopped = runner([str(Path(prefix) / "bin/sv"), "down", str(target)],
                                         capture_output=True, text=True, timeout=5, check=False).returncode == 0
                    except (OSError, subprocess.SubprocessError):
                        stopped = False
                if stopped and _owns_run(target, target_fd, owned_run):
                    os.unlink("run", dir_fd=target_fd)
            if isinstance(exc, ServiceInstallError):
                raise
            raise ServiceInstallError("service registration failed; inspect the exact target before retrying") from exc
        finally:
            if target_fd is not None:
                os.close(target_fd)
            if created_target is not None:
                try:
                    if _identity(target.lstat()) == created_target:
                        target.rmdir()  # Only an empty directory from this attempt.
                except OSError:
                    pass


def status(*, prefix, runner=subprocess.run, service_id: str = SERVICE_ID) -> dict[str, object]:
    service_id = _service(service_id)
    root = _root(prefix)
    target = root / service_id
    try:
        info = target.lstat()
    except FileNotFoundError:
        return {"service_id": service_id, "installed": False, "status": "not-installed"}
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise ServiceInstallError("installed service target identity is unsafe")
    digest = hashlib.sha256(_read_executable(target / "run")).hexdigest()
    manager = Path(prefix) / "bin/sv"
    _read_executable(manager)
    target_path = str(target)
    result = runner([str(manager), "status", target_path], capture_output=True,
                    text=True, timeout=5, check=False)
    line = (result.stdout or "").splitlines()
    live = "running" if result.returncode == 0 and line and line[0].startswith(f"run: {target_path}:") else "stopped" if line and line[0].startswith(f"down: {target_path}:") else "unknown"
    source_digest = hashlib.sha256(_source_bytes(_source(service_id=service_id))).hexdigest()
    return {"service_id": service_id, "installed": True, "status": live,
            "run_sha256": digest, "source_matches": digest == source_digest}
