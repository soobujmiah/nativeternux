"""Preview-first Runit registration for the fixed Native terminal broker."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import time

SERVICE_ID = "ternuxx-terminal-broker"


class ServiceInstallError(RuntimeError):
    pass


def _source(source: str | os.PathLike[str] | None = None) -> Path:
    return Path(source) if source is not None else Path(__file__).resolve().parents[1] / "scripts/termux-services" / SERVICE_ID / "run"


def _root(prefix: str | os.PathLike[str]) -> Path:
    path = Path(prefix) / "var/service"
    try:
        info = path.lstat()
    except OSError as exc:
        raise ServiceInstallError("Termux Runit service directory is unavailable") from exc
    if (stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid() or info.st_mode & 0o022):
        raise ServiceInstallError("Termux Runit service directory identity is unsafe")
    return path


def _source_bytes(path: Path) -> bytes:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ServiceInstallError("broker service source is unavailable") from exc
    if (stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid() or info.st_mode & 0o022
            or not info.st_mode & 0o100 or info.st_size > 32768):
        raise ServiceInstallError("broker service source identity is unsafe")
    content = path.read_bytes()
    syntax = subprocess.run(["bash", "-n", str(path)], capture_output=True, timeout=5, check=False)
    if syntax.returncode:
        raise ServiceInstallError("broker service source failed shell syntax validation")
    return content


def _target_state(target: Path) -> str:
    try:
        info = target.lstat()
    except FileNotFoundError:
        return "absent"
    if (stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid() or info.st_mode & 0o022):
        raise ServiceInstallError("broker service target identity is unsafe")
    names = {item.name for item in target.iterdir()}
    if names != {"supervise"}:
        raise ServiceInstallError("broker service target exists and is not an empty Runit supervisor")
    supervise = target / "supervise"
    sup_info = supervise.lstat()
    allowed = {"control", "ok", "lock", "pid", "stat", "status"}
    if (stat.S_ISLNK(sup_info.st_mode) or not stat.S_ISDIR(sup_info.st_mode)
            or sup_info.st_uid != os.getuid() or sup_info.st_mode & 0o077
            or {item.name for item in supervise.iterdir()} - allowed):
        raise ServiceInstallError("Runit supervisor state identity is unsafe")
    if not {"control", "ok"}.issubset({item.name for item in supervise.iterdir()}):
        raise ServiceInstallError("Runit supervisor state is incomplete")
    return "runit-supervise-only"


def preview_install(*, prefix: str | os.PathLike[str], source: str | os.PathLike[str] | None = None) -> dict[str, object]:
    root = _root(prefix)
    source_path = _source(source)
    content = _source_bytes(source_path)
    target = root / SERVICE_ID
    state = _target_state(target)
    if state not in {"absent", "runit-supervise-only"}:
        raise ServiceInstallError("broker service target already exists; it will not be adopted or overwritten")
    manager = Path(prefix) / "bin/sv"
    try:
        metadata = manager.lstat()
    except OSError as exc:
        raise ServiceInstallError("Termux Runit control command is unavailable") from exc
    if (stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid() or metadata.st_mode & 0o022
            or not metadata.st_mode & 0o100):
        raise ServiceInstallError("Termux Runit control command identity is unsafe")
    core = {"service_id": SERVICE_ID, "target": str(target / "run"),
            "source": str(source_path), "source_sha256": hashlib.sha256(content).hexdigest(),
            "target_state": state, "service_manager_sha256": hashlib.sha256(manager.read_bytes()).hexdigest()}
    plan_id = hashlib.sha256(json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {**core, "plan_id": plan_id, "requires_confirmation": True, "read_only": True,
            "impact": "Adds only the fixed Ternuxx terminal broker Runit service. Runit will keep the Native broker available; it does not start a PRoot guest, change Termux:Boot, or acquire a Wake Lock."}


def install(*, prefix: str | os.PathLike[str], confirmed: bool, plan_id: str | None,
            source: str | os.PathLike[str] | None = None,
            runner=subprocess.run) -> dict[str, object]:
    if confirmed is not True:
        raise ServiceInstallError("explicit confirmation is required")
    plan = preview_install(prefix=prefix, source=source)
    if not isinstance(plan_id, str) or plan_id != plan["plan_id"]:
        raise ServiceInstallError("fresh exact broker service preview and plan ID are required")
    root = _root(prefix)
    content = _source_bytes(_source(source))
    target = root / SERVICE_ID
    state = _target_state(target)
    if state != plan["target_state"]:
        raise ServiceInstallError("broker service target changed after preview")
    staged_fd, staged_name = tempfile.mkstemp(prefix=".ternuxx-terminal-broker-run.", dir=root)
    staged = Path(staged_name)
    created_target = False
    try:
        with os.fdopen(staged_fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(staged, 0o755)
        if hashlib.sha256(staged.read_bytes()).hexdigest() != plan["source_sha256"]:
            raise ServiceInstallError("staged broker service definition did not verify")
        if state == "absent":
            temporary = Path(tempfile.mkdtemp(prefix=".ternuxx-terminal-broker.", dir=root))
            staged_inside = temporary / "run"
            os.replace(staged, staged_inside)
            if target.exists() or target.is_symlink():
                raise ServiceInstallError("broker service target appeared after preview")
            os.rename(temporary, target)
            created_target = True
        else:
            run_file = target / "run"
            if run_file.exists() or run_file.is_symlink():
                raise ServiceInstallError("broker service run file appeared after preview")
            os.replace(staged, run_file)
        manager = Path(prefix) / "bin/sv"
        target_path = str(target)
        result = runner([str(manager), "up", target_path], capture_output=True,
                        text=True, timeout=8, check=False)
        if result.returncode:
            raise ServiceInstallError("Runit did not accept the broker service start")
        line: list[str] = []
        for _attempt in range(30):
            status_result = runner([str(manager), "status", target_path], capture_output=True,
                                   text=True, timeout=5, check=False)
            line = (status_result.stdout or "").splitlines()
            if line and line[0].startswith(f"run: {target_path}:"):
                break
            time.sleep(0.1)
        if not line or not line[0].startswith(f"run: {target_path}:"):
            raise ServiceInstallError("broker service did not reach the running state")
        return {"service_id": SERVICE_ID, "status": "installed", "source_sha256": plan["source_sha256"],
                "service_started": True, "guest_started": False, "wakeup_enabled": False}
    except Exception:
        if target.exists() and not target.is_symlink():
            run_file = target / "run"
            try:
                info = run_file.lstat()
                same = stat.S_ISREG(info.st_mode) and hashlib.sha256(run_file.read_bytes()).hexdigest() == plan["source_sha256"]
            except OSError:
                same = False
            if same:
                manager = Path(prefix) / "bin/sv"
                try:
                    runner([str(manager), "down", str(target)], capture_output=True,
                           text=True, timeout=5, check=False)
                except (OSError, subprocess.TimeoutExpired):
                    pass
                try:
                    run_file.unlink()
                except OSError:
                    pass
        if staged.exists():
            staged.unlink()
        raise


def status(*, prefix: str | os.PathLike[str], runner=subprocess.run) -> dict[str, object]:
    root = _root(prefix)
    target = root / SERVICE_ID
    if not target.exists():
        return {"service_id": SERVICE_ID, "installed": False, "status": "not-installed"}
    run_file = target / "run"
    try:
        info = run_file.lstat()
        digest = hashlib.sha256(run_file.read_bytes()).hexdigest()
    except OSError as exc:
        raise ServiceInstallError("broker service definition is unavailable") from exc
    if (stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid() or info.st_mode & 0o022
            or not info.st_mode & 0o100):
        raise ServiceInstallError("installed broker service definition identity is unsafe")
    target_path = str(target)
    result = runner([str(Path(prefix) / "bin/sv"), "status", target_path],
                    capture_output=True, text=True, timeout=5, check=False)
    line = (result.stdout or "").splitlines()
    live = "running" if line and line[0].startswith(f"run: {target_path}:") else "stopped" if line and line[0].startswith(f"down: {target_path}:") else "unknown"
    source_digest = hashlib.sha256(_source_bytes(_source())).hexdigest()
    return {"service_id": SERVICE_ID, "installed": True, "status": live,
            "run_sha256": digest, "source_matches": digest == source_digest}
