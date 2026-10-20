#!/usr/bin/env python3
"""Shared, opt-in Termux:X11 Android Activity monitoring policy.

Linux GUI lifecycle status is intentionally independent. Read-only policy/status
calls never launch Android Activities and never poll Android focus.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import uuid

SCHEMA_VERSION = 1
MIN_INTERVAL_SECONDS = 30
MAX_INTERVAL_SECONDS = 86400
DEFAULT_INTERVAL_SECONDS = 300
UNITS = {"seconds": 1, "minutes": 60, "hours": 3600}


class MonitoringError(ValueError):
    pass


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _paths(state_dir: str | os.PathLike[str]) -> tuple[Path, Path, Path]:
    root = Path(state_dir).absolute()
    return root, root / "gui-monitoring.json", root / ".gui-monitoring.lock"


def _check_root(root: Path, *, create: bool) -> None:
    if create:
        root.mkdir(parents=True, mode=0o700, exist_ok=True)
    if root.resolve(strict=False) != root:
        raise MonitoringError("monitor state path contains a symbolic link")
    info = root.lstat()
    if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)
            or info.st_uid != os.getuid() or info.st_mode & 0o077):
        raise MonitoringError("monitor state directory is unsafe")


def _default() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "enabled": False,
        "interval_seconds": DEFAULT_INTERVAL_SECONDS,
        "activity_launch": False,
        "focus_check": False,
        "updated_at": None,
        "last_check_at": None,
        "last_result": "never",
        "last_error": None,
        "activity_availability": "not_checked",
        "activity_request_status": "not_requested",
        "focus_status": "not_checked",
    }


def _validate(data: object) -> dict[str, object]:
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise MonitoringError("monitor policy schema is invalid")
    for key in ("enabled", "activity_launch", "focus_check"):
        if type(data.get(key)) is not bool:
            raise MonitoringError(f"monitor policy {key} must be boolean")
    interval = data.get("interval_seconds")
    if type(interval) is not int or not MIN_INTERVAL_SECONDS <= interval <= MAX_INTERVAL_SECONDS:
        raise MonitoringError("monitor interval is outside the supported 30..86400 second range")
    for key in ("updated_at", "last_check_at", "last_result", "last_error", "activity_availability", "activity_request_status", "focus_status"):
        if key in data and data[key] is not None and not isinstance(data[key], str):
            raise MonitoringError(f"monitor policy {key} has an invalid value")
    merged = {**_default(), **data}
    if merged["activity_launch"] and not merged["focus_check"]:
        raise MonitoringError("Activity launch requires focus checking to avoid unnecessary foreground requests")
    return merged


def _read(root: Path, path: Path) -> dict[str, object]:
    _check_root(root, create=False)
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except FileNotFoundError:
        return _default()
    except OSError as exc:
        raise MonitoringError("monitor policy cannot be opened safely") from exc
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_size > 65536):
            raise MonitoringError("monitor policy file identity or permissions are unsafe")
        with os.fdopen(fd, "r", encoding="utf-8", closefd=False) as stream:
            raw = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MonitoringError("monitor policy is unreadable or malformed") from exc
    finally:
        os.close(fd)
    return _validate(raw)


def status(state_dir: str | os.PathLike[str], *, home: str | os.PathLike[str] | None = None,
           tmp_root: str | os.PathLike[str] | None = None, now: dt.datetime | None = None) -> dict[str, object]:
    """Return policy and freshness information without writing or probing Android."""
    root, path, _ = _paths(state_dir)
    try:
        data = _read(root, path)
    except FileNotFoundError:
        data = _default()
    now = now or dt.datetime.now(dt.timezone.utc)
    last = data.get("last_check_at")
    next_check = now.isoformat(timespec="seconds") if data["enabled"] else None
    fresh = "never"
    if isinstance(last, str):
        try:
            last_dt = dt.datetime.fromisoformat(last)
            due = last_dt + dt.timedelta(seconds=int(data["interval_seconds"]))
            next_check = due.isoformat(timespec="seconds")
            fresh = "fresh" if now < due else "due"
        except (ValueError, OverflowError):
            fresh = "unknown"
    linux_health = "unknown"
    if home is not None:
        try:
            linux_health = _linux_gui_state(str(home), str(root), str(tmp_root or "/data/data/com.termux/files/usr/tmp"))
        except (OSError, ValueError, RuntimeError):
            linux_health = "unknown"
    return {
        "schema_version": SCHEMA_VERSION,
        "read_only": True,
        "enabled": data["enabled"],
        "interval_seconds": data["interval_seconds"],
        "interval_bounds_seconds": [MIN_INTERVAL_SECONDS, MAX_INTERVAL_SECONDS],
        "activity_launch": data["activity_launch"],
        "focus_check": data["focus_check"],
        "linux_gui_health": linux_health,
        "android_activity_availability": data["activity_availability"],
        "activity_request_status": data["activity_request_status"],
        "activity_focus_status": data["focus_status"],
        "last_check_at": last,
        "last_result": data["last_result"],
        "freshness": fresh,
        "next_check_at": next_check if data["enabled"] else None,
        "last_error": data["last_error"],
        "log_path": str(root / "log" / "gui-monitoring.log"),
        "scheduler": _scheduler_state(root, bool(data["enabled"])),
        "activity_requests_performed": False,
        "focus_probe_performed": False,
    }


def configure(
    state_dir: str | os.PathLike[str], *, enabled: bool | None = None,
    interval_value: int | None = None, unit: str | None = None,
    activity_launch: bool | None = None, focus_check: bool | None = None,
) -> dict[str, object]:
    """Atomically update only explicitly supplied policy fields."""
    root, path, lock = _paths(state_dir)
    _check_root(root, create=True)
    if lock.exists() or lock.is_symlink():
        raise MonitoringError("another GUI monitoring policy update holds the lock")
    try:
        lock.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise MonitoringError("another GUI monitoring policy update holds the lock") from exc
    try:
        lock_info = lock.lstat()
        if not stat.S_ISDIR(lock_info.st_mode) or lock_info.st_uid != os.getuid() or lock_info.st_mode & 0o077:
            raise MonitoringError("GUI monitoring policy lock is unsafe")
        data = _read(root, path)
        if enabled is not None:
            if type(enabled) is not bool:
                raise MonitoringError("enabled must be boolean")
            data["enabled"] = enabled
        if activity_launch is not None:
            if type(activity_launch) is not bool:
                raise MonitoringError("activity_launch must be boolean")
            data["activity_launch"] = activity_launch
        if focus_check is not None:
            if type(focus_check) is not bool:
                raise MonitoringError("focus_check must be boolean")
            data["focus_check"] = focus_check
        if interval_value is not None:
            if type(interval_value) is not int or unit not in UNITS:
                raise MonitoringError("interval requires an integer and seconds, minutes, or hours unit")
            seconds = interval_value * UNITS[unit]
            if not MIN_INTERVAL_SECONDS <= seconds <= MAX_INTERVAL_SECONDS:
                raise MonitoringError("monitor interval must be from 30 seconds through 24 hours")
            data["interval_seconds"] = seconds
        elif unit is not None:
            raise MonitoringError("interval unit requires an interval value")
        data = _validate({**data, "schema_version": SCHEMA_VERSION, "updated_at": _utc_now()})
        try:
            current = path.lstat()
            if (not stat.S_ISREG(current.st_mode) or stat.S_ISLNK(current.st_mode)
                    or current.st_uid != os.getuid() or current.st_mode & 0o077):
                raise MonitoringError("monitor policy file identity or permissions are unsafe")
        except FileNotFoundError:
            pass
        temporary = root / (".gui-monitoring." + uuid.uuid4().hex + ".tmp")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(data, stream, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            dir_fd = os.open(root, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except BaseException:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
            raise
    finally:
        lock.rmdir()
    return status(state_dir)



def _scheduler_state(root: Path, enabled: bool) -> str:
    if not enabled:
        return "disabled"
    lock = root / ".gui-monitor-scheduler.lock"
    try:
        info = lock.lstat()
    except FileNotFoundError:
        return "not_running"
    if stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and not (info.st_mode & 0o077):
        try:
            fd = os.open(lock, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return "running"
            finally:
                os.close(fd)
            return "not_running"
        except OSError:
            return "unknown"
    return "unsafe"


def _atomic_save(root: Path, data: dict[str, object]) -> None:
    temporary = root / (".gui-monitoring." + uuid.uuid4().hex + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, root / "gui-monitoring.json")
        dir_fd = os.open(root, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except BaseException:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def _linux_gui_state(home: str, state_dir: str, tmp_root: str) -> str:
    import desktop_session_state
    report = desktop_session_state.inspect(Path(home), Path(state_dir), Path("/proc"), Path(tmp_root))
    return str(report.get("state", "unknown"))


def _activity_and_focus(env: dict[str, str], *, do_focus: bool, do_launch: bool,
                        linux_state: str) -> tuple[str, str, str, str | None]:
    """Probe Android only in the opt-in scheduler, never in status calls."""
    prefix = env.get("PREFIX", "/data/data/com.termux/files/usr")
    pm = Path(prefix) / "bin/pm"
    am = Path(prefix) / "bin/am"
    dumpsys = Path(prefix) / "bin/dumpsys"
    availability = "not_requested"
    request = "not_requested"
    focus = "not_requested"
    error = None
    if do_focus or do_launch:
        if pm.is_file() and os.access(pm, os.X_OK):
            try:
                result = subprocess.run([str(pm), "path", "com.termux.x11"], capture_output=True,
                                        text=True, timeout=3, check=False)
                if result.returncode == 0:
                    availability = "available" if "package:" in result.stdout else "unavailable"
                else:
                    availability = "unknown"
            except (OSError, subprocess.TimeoutExpired):
                availability = "unknown"
        else:
            availability = "unknown"
    if do_focus:
        if not (dumpsys.is_file() and os.access(dumpsys, os.X_OK)):
            focus = "unknown"
        else:
            try:
                result = subprocess.run([str(dumpsys), "activity", "activities"], capture_output=True,
                                        text=True, timeout=4, check=False)
                if result.returncode != 0:
                    focus = "unknown"
                else:
                    text = result.stdout[-50000:]
                    resumed = re.search(r"(?:mResumedActivity|topResumedActivity)\s*[:=].{0,256}", text)
                    if not resumed:
                        focus = "unknown"
                    elif "com.termux.x11" in resumed.group(0):
                        focus = "foreground"
                    else:
                        focus = "background"
            except (OSError, subprocess.TimeoutExpired):
                focus = "unknown"
    if do_launch and linux_state == "running" and availability == "available":
        if focus == "background":
            if am.is_file() and os.access(am, os.X_OK):
                try:
                    result = subprocess.run([str(am), "start", "--user", "0", "-n",
                                             "com.termux.x11/com.termux.x11.MainActivity"],
                                            capture_output=True, text=True, timeout=5, check=False)
                    request = "requested" if result.returncode == 0 else "failed"
                    if result.returncode != 0:
                        error = "Termux:X11 Activity request failed"
                except (OSError, subprocess.TimeoutExpired):
                    request = "failed"
                    error = "Termux:X11 Activity request failed or timed out"
            else:
                request = "unavailable"
                error = "Activity launcher is unavailable"
        elif focus == "foreground":
            request = "not_needed"
        else:
            request = "skipped_unknown_focus"
            error = "Activity launch skipped because foreground state is unknown"
    return availability, focus, request, error


def monitor_once(home: str, state_dir: str, env: dict[str, str] | None = None) -> dict[str, object]:
    """One bounded scheduler tick. Disabled policy performs no Android commands."""
    env = dict(os.environ if env is None else env)
    root, path, _ = _paths(state_dir)
    data = _read(root, path)
    if not data["enabled"]:
        return {"result": "disabled", "android_probes_performed": False}
    try:
        linux_state = _linux_gui_state(home, state_dir, env.get("TMPDIR", "/data/data/com.termux/files/usr/tmp"))
    except (OSError, ValueError, RuntimeError):
        linux_state = "unknown"
    availability, focus, request, error = _activity_and_focus(
        env, do_focus=bool(data["focus_check"]), do_launch=bool(data["activity_launch"]),
        linux_state=linux_state,
    )
    now = _utc_now()
    result = "ok" if error is None and linux_state in {"running", "stopped"} else "degraded"
    policy_lock = root / ".gui-monitoring.lock"
    try:
        policy_lock.mkdir(mode=0o700)
    except FileExistsError:
        return {"result": "policy_update_in_progress", "android_probes_performed": True}
    try:
        updated = _read(root, path)
        updated.update({"last_check_at": now, "last_result": result, "last_error": error,
                        "activity_availability": availability,
                        "activity_request_status": request, "focus_status": focus})
        _atomic_save(root, _validate(updated))
    finally:
        policy_lock.rmdir()
    log_dir = root / "log"
    log_dir.mkdir(mode=0o700, exist_ok=True)
    info = log_dir.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise MonitoringError("GUI monitoring log directory is unsafe")
    log = log_dir / "gui-monitoring.log"
    try:
        log_info = log.lstat()
        if (not stat.S_ISREG(log_info.st_mode) or log_info.st_uid != os.getuid()
                or log_info.st_mode & 0o077):
            raise MonitoringError("GUI monitoring log identity or permissions are unsafe")
    except FileNotFoundError:
        pass
    fd = os.open(log, os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as stream:
        stream.write(json.dumps({"at": now, "result": result, "linux_gui_health": linux_state,
                                 "activity_availability": availability,
                                 "activity_request_status": request, "focus_status": focus,
                                 "error": error}, sort_keys=True) + "\n")
    return {"result": result, "linux_gui_health": linux_state,
            "activity_availability": availability, "activity_request_status": request,
            "focus_status": focus, "last_check_at": now, "last_error": error,
            "android_probes_performed": bool(data["focus_check"] or data["activity_launch"])}


def run_scheduler(home: str, state_dir: str, env: dict[str, str] | None = None) -> int:
    """Run the one Runit-owned scheduler; flock prevents duplicate polling loops."""
    env = dict(os.environ if env is None else env)
    root, _, _ = _paths(state_dir)
    _check_root(root, create=True)
    lock_path = root / ".gui-monitor-scheduler.lock"
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        os.close(fd)
        raise MonitoringError("GUI monitoring scheduler lock is unsafe")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        os.close(fd)
        raise MonitoringError("GUI monitoring scheduler is already running") from exc
    try:
        next_due = time.monotonic()
        while True:
            data = _read(root, root / "gui-monitoring.json")
            now = time.monotonic()
            if not data["enabled"]:
                next_due = now + 5
            elif now >= next_due:
                try:
                    monitor_once(home, state_dir, env)
                except (OSError, MonitoringError, ValueError) as exc:
                    print(f"GUI monitoring tick failed: {exc.__class__.__name__}", file=sys.stderr, flush=True)
                current = _read(root, root / "gui-monitoring.json")
                next_due = time.monotonic() + int(current["interval_seconds"]) if current["enabled"] else time.monotonic() + 5
            time.sleep(max(0.1, min(5.0, next_due - time.monotonic())))
    finally:
        os.close(fd)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("status", "configure", "run"))
    parser.add_argument("--home", default=os.environ.get("HOME", ""))
    parser.add_argument("--state-dir", default=os.environ.get("TERNUXX_STATE_DIR", ""))
    parser.add_argument("--enabled", action="store_true", default=None)
    parser.add_argument("--disabled", action="store_true")
    parser.add_argument("--interval", type=int)
    parser.add_argument("--unit", choices=tuple(UNITS))
    parser.add_argument("--activity-launch", action="store_true", default=None)
    parser.add_argument("--no-activity-launch", action="store_true")
    parser.add_argument("--focus-check", action="store_true", default=None)
    parser.add_argument("--no-focus-check", action="store_true")
    args = parser.parse_args(argv)
    try:
        if not args.state_dir:
            raise MonitoringError("TERNUXX_STATE_DIR is required")
        if args.command == "status":
            result = status(args.state_dir, home=args.home)
        elif args.command == "configure":
            result = configure(args.state_dir,
                enabled=False if args.disabled else args.enabled,
                interval_value=args.interval, unit=args.unit,
                activity_launch=False if args.no_activity_launch else args.activity_launch,
                focus_check=False if args.no_focus_check else args.focus_check)
        else:
            return run_scheduler(args.home, args.state_dir)
    except (MonitoringError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps({"ok": True, "data": result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
