"""Lease-guarded Cron polling and deterministic due-event dispatch.

Persistent service startup is explicit through cron_daemon; this module itself
never starts a process or enables boot delivery.
"""
from __future__ import annotations

import datetime as dt
import fcntl
import hashlib
import json
import os
import stat
from pathlib import Path
import re
import uuid

import cron_execution
import cron_registry

_STATE = "scheduler.json"
_LOCK = ".scheduler.lease"
_INSTANCE = re.compile(r"sched-[0-9a-f]{32}")


class SchedulerError(ValueError):
    pass


def _proc_start(pid: int) -> str | None:
    identity = _proc_identity(pid)
    return identity[1] if identity is not None else None


def _proc_identity(pid: int) -> tuple[str, str] | None:
    try:
        raw = Path(f"/proc/{pid}/stat").read_text()
        fields = raw[raw.rfind(")") + 2:].split()
        return (fields[0], fields[19]) if len(fields) > 19 else None
    except (OSError, IndexError):
        return None


def _proc_alive(pid: int, process_start: str) -> bool:
    identity = _proc_identity(pid)
    # A zombie still has a /proc entry and start-time, but cannot dispatch or
    # own a live scheduler. Treat it as exited without signalling it.
    return identity is not None and identity[1] == process_start and identity[0] not in {"Z", "X"}


def _safe_root(state_dir: str | os.PathLike[str], *, create: bool) -> Path:
    root = cron_registry._store_root(state_dir, create=create)
    if root is None:
        raise SchedulerError("Cron state is not installed")
    return root


def _read_state(root: Path) -> dict[str, object] | None:
    path = root / _STATE
    if not path.exists() and not path.is_symlink():
        return None
    try:
        st = path.lstat()
        if path.is_symlink() or not path.is_file() or st.st_uid != os.getuid() or st.st_mode & 0o077:
            raise SchedulerError("scheduler state identity or permissions are unsafe")
        data = json.loads(path.read_text(encoding="utf-8"))
    except SchedulerError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SchedulerError("scheduler state is malformed or unreadable") from exc
    expected = {"schema_version", "instance_id", "pid", "process_start", "started_at",
                "heartbeat_at", "last_poll_at", "last_dispatch_at", "last_error"}
    if (not isinstance(data, dict) or set(data) != expected or data["schema_version"] != 1
            or not isinstance(data["instance_id"], str) or not _INSTANCE.fullmatch(data["instance_id"])
            or type(data["pid"]) is not int or data["pid"] <= 0
            or not isinstance(data["process_start"], str) or not data["process_start"]
            or not isinstance(data["started_at"], str) or not isinstance(data["heartbeat_at"], str)
            or (data["last_poll_at"] is not None and not isinstance(data["last_poll_at"], str))
            or (data["last_dispatch_at"] is not None and not isinstance(data["last_dispatch_at"], str))
            or (data["last_error"] is not None and not isinstance(data["last_error"], str))):
        raise SchedulerError("scheduler state schema is unsupported")
    return data


def _write_state(root: Path, data: dict[str, object]) -> None:
    temp = root / (".scheduler." + uuid.uuid4().hex + ".tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, root / _STATE)
        os.chmod(root / _STATE, 0o600)
        dir_fd = os.open(root, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def status(state_dir: str | os.PathLike[str]) -> dict[str, object]:
    root = cron_registry._store_root(state_dir, create=False)
    if root is None:
        return {"status": "stopped", "runtime_available": True, "process_alive": False,
                "lease_held": False, "dispatch_healthy": False, "dispatch": "unqualified",
                "instance_id": None}
    state = _read_state(root)
    if state is None:
        return {"status": "stopped", "runtime_available": True, "process_alive": False,
                "lease_held": False, "dispatch_healthy": False, "dispatch": "unqualified",
                "instance_id": None}
    lock_path = root / _LOCK
    try:
        st = lock_path.lstat()
        if lock_path.is_symlink() or not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077:
            raise SchedulerError("scheduler lease identity or permissions are unsafe")
        fd = os.open(lock_path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except FileNotFoundError:
        return {"status": "stopped", "runtime_available": True, "process_alive": False,
                "lease_held": False, "dispatch_healthy": False, "dispatch": "unqualified",
                "instance_id": state["instance_id"]}
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            live = _proc_alive(state["pid"], state["process_start"])
            last_poll = state["last_poll_at"]
            fresh = False
            if live and last_poll:
                try:
                    polled = dt.datetime.fromisoformat(last_poll)
                    fresh = 0 <= (dt.datetime.now(dt.timezone.utc) - polled).total_seconds() <= 120
                except ValueError:
                    fresh = False
            healthy = bool(live and fresh and state["last_error"] is None)
            return {"status": "running" if live else "degraded",
                    "process_alive": live, "lease_held": True, "dispatch_healthy": healthy,
                    "dispatch": "healthy" if healthy else "degraded",
                    "instance_id": state["instance_id"], "identity_verified": live,
                    "last_poll_at": last_poll, "last_dispatch_at": state["last_dispatch_at"],
                    "last_error": state["last_error"]}
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
    return {"status": "stopped", "dispatch": "unqualified", "instance_id": state["instance_id"]}


class SchedulerLease:
    """In-process exclusive lease; never removes stale state on acquisition."""

    def __init__(self, state_dir: str | os.PathLike[str], *, instance_id: str | None = None):
        self.root = _safe_root(state_dir, create=True)
        self.instance_id = instance_id or "sched-" + uuid.uuid4().hex
        if not _INSTANCE.fullmatch(self.instance_id):
            raise SchedulerError("scheduler instance identity is invalid")
        self.fd: int | None = None

    def acquire(self) -> str:
        path = self.root / _LOCK
        if path.is_symlink():
            raise SchedulerError("scheduler lease is a symlink")
        fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
        st = os.fstat(fd)
        if not __import__("stat").S_ISREG(st.st_mode) or st.st_uid != os.getuid() or st.st_mode & 0o077:
            os.close(fd)
            raise SchedulerError("scheduler lease identity or permissions are unsafe")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(fd)
            raise SchedulerError("another scheduler instance holds the lease") from exc
        self.fd = fd
        try:
            previous = _read_state(self.root)
            if previous is not None and _proc_alive(previous["pid"], previous["process_start"]):
                if previous["pid"] != os.getpid():
                    raise SchedulerError("scheduler state reports a competing live owner")
            now = dt.datetime.now(dt.timezone.utc).isoformat()
            identity = _proc_start(os.getpid())
            if identity is None:
                raise SchedulerError("current process identity is unavailable")
            state = {"schema_version": 1, "instance_id": self.instance_id, "pid": os.getpid(),
                     "process_start": identity, "started_at": now, "heartbeat_at": now,
                     "last_poll_at": None, "last_dispatch_at": None, "last_error": None}
            _write_state(self.root, state)
            return self.instance_id
        except Exception:
            self.close()
            raise

    def heartbeat(self, *, poll_at: str | None = None, dispatch_at: str | None = None,
                  error: str | None = None) -> None:
        if self.fd is None:
            raise SchedulerError("scheduler lease is not held")
        state = _read_state(self.root)
        if (state is None or state["instance_id"] != self.instance_id
                or state["pid"] != os.getpid()
                or not _proc_alive(os.getpid(), state["process_start"])):
            raise SchedulerError("scheduler ownership changed")
        state["heartbeat_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        state["last_poll_at"] = poll_at or state["last_poll_at"]
        state["last_dispatch_at"] = dispatch_at or state["last_dispatch_at"]
        state["last_error"] = error[:180] if error else None
        _write_state(self.root, state)

    def close(self) -> None:
        if self.fd is None:
            return
        try:
            try:
                state = _read_state(self.root)
            except SchedulerError:
                state = None  # Preserve uncertain state; release only this process's OS lease.
            if state is not None and state["instance_id"] == self.instance_id and state["pid"] == os.getpid():
                (self.root / _STATE).unlink()
        finally:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)
            self.fd = None

    def __enter__(self) -> "SchedulerLease":
        self.acquire()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def dispatch_claimed_event(state_dir: str | os.PathLike[str], lease: SchedulerLease, *,
                           job_id: str, event_id: str, scheduled_at: str,
                           trigger_source: str = "schedule", now: dt.datetime | None = None,
                           executor=None) -> dict[str, object]:
    if lease.fd is None:
        raise SchedulerError("dispatch requires a held scheduler lease")
    target_root = _safe_root(state_dir, create=False)
    state = _read_state(lease.root)
    current_start = _proc_start(os.getpid())
    if (target_root != lease.root or state is None or state["instance_id"] != lease.instance_id
            or state["pid"] != os.getpid() or state["process_start"] != current_start):
        raise SchedulerError("scheduler ownership changed before dispatch")
    claim = cron_execution.claim_event(
        state_dir, job_id=job_id, event_id=event_id, scheduled_at=scheduled_at,
        scheduler_instance_id=lease.instance_id, trigger_source=trigger_source, now=now)
    if not claim["claimed"]:
        return claim
    result = cron_execution.execute_claimed(
        state_dir, claim["record"]["execution_id"], executor=executor, now=now)
    return {"claimed": True, "duplicate": False, "record": result}


def _parse_instant(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SchedulerError("schedule instant must include a timezone")
    return parsed.astimezone(dt.timezone.utc)


def due_instant(job: dict[str, object], now: dt.datetime, *, poll_seconds: int) -> dt.datetime | None:
    # Missed slots are skipped; timezone resolution delegates to cron_registry.
    if not isinstance(job, dict) or type(poll_seconds) is not int or not 1 <= poll_seconds <= 60:
        raise SchedulerError("job or polling interval is invalid")
    now = now.astimezone(dt.timezone.utc)
    kind, schedule = job["schedule_type"], job["schedule"]
    grace = dt.timedelta(seconds=max(2 * poll_seconds, 2))
    if kind == "interval":
        anchor = _parse_instant(schedule["anchor_at"])
        interval = schedule["interval_seconds"]
        elapsed = (now - anchor).total_seconds()
        if elapsed < 0:
            return None
        due = anchor + dt.timedelta(seconds=(int(elapsed // interval) * interval))
    elif kind == "one_time":
        due = _parse_instant(schedule["at"])
    elif kind == "calendar" and schedule["mode"] == "specific":
        due = _parse_instant(schedule["datetime"])
    else:
        runs = cron_registry.next_runs(job, count=1, now=now - dt.timedelta(minutes=1))
        if not runs:
            return None
        due = _parse_instant(runs[0])
    if due > now or now - due > grace:
        return None
    return due


def poll_once(state_dir: str | os.PathLike[str], lease: SchedulerLease, *,
              now: dt.datetime | None = None, poll_seconds: int = 5,
              executor=None) -> dict[str, object]:
    if lease.fd is None:
        raise SchedulerError("poll requires a held scheduler lease")
    now = now or dt.datetime.now(dt.timezone.utc)
    target = _safe_root(state_dir, create=False)
    state = _read_state(lease.root)
    if (target != lease.root or state is None or state["instance_id"] != lease.instance_id
            or state["pid"] != os.getpid() or not _proc_alive(os.getpid(), state["process_start"])):
        raise SchedulerError("scheduler ownership changed before polling")
    result = {"polled_at": now.astimezone(dt.timezone.utc).isoformat(),
              "considered": 0, "dispatched": [], "errors": []}
    for job in cron_registry.list_jobs(state_dir):
        if not job["enabled"]:
            continue
        result["considered"] += 1
        try:
            if job["missed_run_policy"] != "skip":
                raise SchedulerError("missed-run policy delivery is not installed")
            due = due_instant(job, now, poll_seconds=poll_seconds)
            if due is None:
                continue
            event_id = stable_schedule_event_id(job["job_id"], due.isoformat())
            event = dispatch_claimed_event(
                state_dir, lease, job_id=job["job_id"], event_id=event_id,
                scheduled_at=due.isoformat(), now=now, executor=executor)
            if event.get("claimed"):
                result["dispatched"].append(event["record"])
        except (cron_registry.CronError, cron_execution.ExecutionError, SchedulerError, OSError) as exc:
            result["errors"].append({"job_id": job["job_id"],
                                     "error": cron_execution._redact(str(exc))[:180]})
    return result


def stable_schedule_event_id(job_id: str, scheduled_at: str) -> str:
    if not isinstance(job_id, str) or not re.fullmatch(r"job-[0-9a-f]{32}", job_id):
        raise SchedulerError("job identity is invalid")
    try:
        due = dt.datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise SchedulerError("scheduled time is invalid") from exc
    if due.tzinfo is None or due.utcoffset() is None:
        raise SchedulerError("scheduled time must include a timezone")
    instant = due.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return "schedule-" + hashlib.sha256((job_id + "\0" + instant).encode()).hexdigest()
