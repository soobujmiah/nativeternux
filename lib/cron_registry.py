#!/usr/bin/env python3
"""Persistent, typed Cron registry and deterministic preview engine.

This module stores validated job definitions only. It never executes jobs or
starts a scheduler. Device boot and scheduler recovery are independent trigger
flags; delivery remains unavailable until a separately qualified scheduler is
implemented.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import re
import time
import uuid
import timezone_support

SCHEMA_VERSION = 1
STORE_NAME = "jobs.json"
LOCK_NAME = ".jobs.lock"
MAX_TIMEOUT = 86400
MAX_RETRIES = 10
MAX_RETRY_DELAY = 86400
MAX_JOBS = 1000
MAX_SEARCH_MINUTES = 5 * 366 * 24 * 60
_ALLOWED_ACTIONS = {"diagnostics.doctor", "management.catalog.refresh", "hermes.status", "scheduler.self_test"}
_SCHEDULE_TYPES = {"cron", "interval", "calendar", "one_time"}
_MISSED = {"skip", "run_once_after_recovery", "catch_up_bounded"}
_CONCURRENCY = {"skip_overlap", "queue_one"}
_OUTPUT = {"discard", "bounded_redacted"}

class CronError(ValueError):
    pass


def _timestamp(value: object, name: str, *, require_future: bool = False,
               now: dt.datetime | None = None) -> dt.datetime:
    if not isinstance(value, str) or len(value) > 40:
        raise CronError(f"{name} must be an ISO-8601 timestamp with timezone")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CronError(f"{name} is not a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CronError(f"{name} must include an explicit UTC offset")
    parsed = parsed.astimezone(dt.timezone.utc)
    if require_future and parsed <= (now or dt.datetime.now(dt.timezone.utc)):
        raise CronError(f"{name} must be in the future")
    return parsed


def _timezone(value: object) -> dt.tzinfo:
    try:
        return timezone_support.get_timezone(value)
    except timezone_support.TimezoneError as exc:
        raise CronError(str(exc)) from exc


def _cron_field(text: str, minimum: int, maximum: int, *, dow: bool = False) -> tuple[set[int], bool]:
    if not isinstance(text, str) or not text or len(text) > 100:
        raise CronError("cron field is empty or too long")
    wildcard = all(part.split("/", 1)[0] == "*" for part in text.split(","))
    result: set[int] = set()
    for part in text.split(","):
        if not part:
            raise CronError("cron expression has an empty list item")
        base, slash, step_text = part.partition("/")
        if slash:
            if not step_text.isdigit() or int(step_text) < 1:
                raise CronError("cron step must be a positive integer")
            step = int(step_text)
        else:
            step = 1
        if base == "*":
            low, high = minimum, maximum
        elif "-" in base:
            ends = base.split("-")
            if len(ends) != 2 or not all(x.isdigit() for x in ends):
                raise CronError("cron range is invalid")
            low, high = map(int, ends)
            if low > high:
                raise CronError("wrapping cron ranges are unsupported")
        elif base.isdigit():
            low = high = int(base)
            if slash:
                high = maximum
        else:
            raise CronError("cron names and macros are unsupported; use numeric fields")
        if low < minimum or high > maximum:
            raise CronError("cron field is out of range")
        result.update(range(low, high + 1, step))
    if dow and 7 in result:
        result.add(0)
        result.discard(7)
    return result, wildcard


def parse_cron(expression: object) -> dict[str, object]:
    if not isinstance(expression, str) or len(expression) > 120:
        raise CronError("cron expression must contain five numeric fields")
    fields = expression.split()
    if len(fields) != 5:
        raise CronError("cron expression must contain exactly five fields")
    minute, _ = _cron_field(fields[0], 0, 59)
    hour, _ = _cron_field(fields[1], 0, 23)
    dom, dom_star = _cron_field(fields[2], 1, 31)
    month, _ = _cron_field(fields[3], 1, 12)
    dow, dow_star = _cron_field(fields[4], 0, 7, dow=True)
    return {"minute": minute, "hour": hour, "dom": dom, "month": month,
            "dow": dow, "dom_star": dom_star, "dow_star": dow_star}


def _cron_matches(local: dt.datetime, parsed: dict[str, object]) -> bool:
    if local.minute not in parsed["minute"] or local.hour not in parsed["hour"] or local.month not in parsed["month"]:
        return False
    dom_match = local.day in parsed["dom"]
    dow_match = ((local.weekday() + 1) % 7) in parsed["dow"]
    if parsed["dom_star"]:
        day_match = dow_match
    elif parsed["dow_star"]:
        day_match = dom_match
    else:
        day_match = dom_match or dow_match
    return day_match


def validate_job(job: object, *, now: dt.datetime | None = None, require_future: bool = True, allow_legacy_policies: bool = False) -> dict[str, object]:
    if not isinstance(job, dict):
        raise CronError("job must be an object")
    required = {"schema_version", "job_id", "name", "description", "action_id", "owner", "provider", "source",
                "schedule_type", "schedule", "enabled", "run_after_device_boot",
                "run_after_scheduler_recovery", "timeout_seconds", "retry_policy",
                "missed_run_policy", "concurrency_policy", "environment", "required_capabilities",
                "output_policy", "created_at", "updated_at", "last_execution"}
    if set(job) != required:
        raise CronError("job fields do not match schema version 1")
    if type(job["schema_version"]) is not int or job["schema_version"] != SCHEMA_VERSION:
        raise CronError("unsupported job schema version")
    if not isinstance(job["job_id"], str) or not re.fullmatch(r"job-[0-9a-f]{32}", job["job_id"]):
        raise CronError("job ID must be a stable job-<32 hex> identifier")
    for key, limit in (("name", 100), ("description", 500)):
        value = job[key]
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise CronError(f"{key} must be non-empty and at most {limit} characters")
    if not isinstance(job["action_id"], str) or job["action_id"] not in _ALLOWED_ACTIONS:
        raise CronError("action is not a registered safe task type")
    if job["owner"] != "ternuxx" or job["provider"] != "ternuxx":
        raise CronError("job owner/provider must identify the Ternuxx registry")
    if job["source"] != "tx-mng-cron" or not isinstance(job["source"], str):
        raise CronError("job source identity is invalid")
    if not isinstance(job["environment"], str) or job["environment"] not in {"native-termux", "debian-proot"}:
        raise CronError("execution environment is unsupported")
    if type(job["enabled"]) is not bool or type(job["run_after_device_boot"]) is not bool or type(job["run_after_scheduler_recovery"]) is not bool:
        raise CronError("enabled and startup trigger fields must be booleans")
    if type(job["timeout_seconds"]) is not int or not 1 <= job["timeout_seconds"] <= MAX_TIMEOUT:
        raise CronError("timeout_seconds must be between 1 and 86400")
    retry = job["retry_policy"]
    if not isinstance(retry, dict) or set(retry) != {"max_attempts", "delay_seconds", "backoff"}:
        raise CronError("retry_policy fields are invalid")
    if type(retry["max_attempts"]) is not int or not 1 <= retry["max_attempts"] <= MAX_RETRIES:
        raise CronError("retry max_attempts must be between 1 and 10, including the first attempt")
    if type(retry["delay_seconds"]) is not int or not 0 <= retry["delay_seconds"] <= MAX_RETRY_DELAY:
        raise CronError("retry delay_seconds is out of range")
    if not isinstance(retry["backoff"], str) or retry["backoff"] not in {"fixed", "exponential"}:
        raise CronError("retry backoff must be fixed or exponential")
    if not isinstance(job["missed_run_policy"], str) or job["missed_run_policy"] not in _MISSED:
        raise CronError("missed_run_policy is unsupported")
    if not isinstance(job["concurrency_policy"], str) or job["concurrency_policy"] not in _CONCURRENCY:
        raise CronError("concurrency_policy is unsupported")
    if not isinstance(job["output_policy"], str) or job["output_policy"] not in _OUTPUT:
        raise CronError("output_policy is unsupported")
    caps = job["required_capabilities"]
    if not isinstance(caps, list) or len(caps) > 12 or any(not isinstance(x, str) or not re.fullmatch(r"[a-z][a-z0-9_.-]{0,63}", x) for x in caps):
        raise CronError("required_capabilities must be a bounded list of capability IDs")
    if job["last_execution"] is not None:
        raise CronError("execution history is not writable until an execution engine exists")
    _timestamp(job["created_at"], "created_at")
    _timestamp(job["updated_at"], "updated_at")
    schedule_type = job["schedule_type"]
    schedule = job["schedule"]
    if not isinstance(schedule_type, str) or schedule_type not in _SCHEDULE_TYPES or not isinstance(schedule, dict):
        raise CronError("schedule_type or schedule is invalid")
    if schedule_type == "cron":
        if set(schedule) != {"expression", "timezone"}:
            raise CronError("cron schedule requires expression and timezone")
        parse_cron(schedule["expression"])
        _timezone(schedule["timezone"])
    elif schedule_type == "interval":
        if set(schedule) != {"interval_seconds", "anchor_at"} or type(schedule["interval_seconds"]) is not int or not 1 <= schedule["interval_seconds"] <= 31536000:
            raise CronError("interval requires 1..31536000 interval_seconds and anchor_at")
        _timestamp(schedule["anchor_at"], "anchor_at")
    elif schedule_type == "calendar":
        mode = schedule.get("mode")
        if mode == "daily" and set(schedule) == {"mode", "time", "timezone"}:
            if not isinstance(schedule["time"], str) or not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", schedule["time"]):
                raise CronError("daily time must use HH:MM 24-hour format")
            _timezone(schedule["timezone"])
        elif mode == "specific" and set(schedule) == {"mode", "datetime"}:
            _timestamp(schedule["datetime"], "specific datetime", require_future=require_future, now=now)
        else:
            raise CronError("calendar schedule must be daily(time, timezone) or specific(datetime)")
    elif schedule_type == "one_time":
        if set(schedule) != {"at"}:
            raise CronError("one_time schedule requires at")
        _timestamp(schedule["at"], "one_time at", require_future=require_future, now=now)
    result = json.loads(json.dumps(job))
    return result if allow_legacy_policies else require_supported_job(result)


def require_supported_job(job: dict[str, object]) -> dict[str, object]:
    """Reject execution policies that the current scheduler cannot honor."""
    if job["environment"] != "native-termux":
        raise CronError("only native-termux execution is currently supported")
    retry = job["retry_policy"]
    if retry != {"max_attempts": 1, "delay_seconds": 0, "backoff": "fixed"}:
        raise CronError("only one attempt with zero delay and fixed backoff is currently supported")
    if job["missed_run_policy"] != "skip":
        raise CronError("only missed-run policy 'skip' is currently supported")
    if job["concurrency_policy"] != "skip_overlap":
        raise CronError("only concurrency policy 'skip_overlap' is currently supported")
    if job["run_after_device_boot"] or job["run_after_scheduler_recovery"]:
        raise CronError("boot and scheduler-recovery delivery are not currently supported")
    if job["required_capabilities"]:
        raise CronError("per-job required capabilities are not enforced yet")
    return job


def new_job(*, name: str, action_id: str, schedule_type: str, schedule: dict[str, object],
            description: str = "Scheduled Ternuxx action", enabled: bool = False,
            run_after_device_boot: bool = False, run_after_scheduler_recovery: bool = False,
            timeout_seconds: int = 300, retry_policy: dict[str, object] | None = None,
            missed_run_policy: str = "skip", concurrency_policy: str = "skip_overlap",
            environment: str = "native-termux", required_capabilities: list[str] | None = None,
            output_policy: str = "discard", now: dt.datetime | None = None) -> dict[str, object]:
    instant = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc).replace(microsecond=0)
    stamp = instant.isoformat().replace("+00:00", "Z")
    job = {"schema_version": SCHEMA_VERSION, "job_id": "job-" + uuid.uuid4().hex,
           "name": name, "description": description, "action_id": action_id, "owner": "ternuxx",
           "provider": "ternuxx", "source": "tx-mng-cron", "schedule_type": schedule_type, "schedule": schedule, "enabled": enabled,
           "run_after_device_boot": run_after_device_boot,
           "run_after_scheduler_recovery": run_after_scheduler_recovery,
           "timeout_seconds": timeout_seconds,
           "retry_policy": retry_policy if retry_policy is not None else {"max_attempts": 1, "delay_seconds": 0, "backoff": "fixed"},
           "missed_run_policy": missed_run_policy, "concurrency_policy": concurrency_policy,
           "environment": environment, "required_capabilities": required_capabilities if required_capabilities is not None else [],
           "output_policy": output_policy, "created_at": stamp, "updated_at": stamp,
           "last_execution": None}
    return validate_job(job, now=instant)


def plan_startup_triggers(job: dict[str, object], events: list[dict[str, object]], *,
                          processed_event_ids: set[str] | None = None,
                          one_time_completed: bool = False) -> list[dict[str, str]]:
    """Pure policy preview; this does not persist claims or execute jobs.

    When both a device-boot event and scheduler-recovery event identify the
    same boot session, device_boot wins and recovery is suppressed. Event
    claims must be persisted atomically by a future qualified scheduler.
    """
    job = validate_job(job, allow_legacy_policies=True)
    if type(one_time_completed) is not bool:
        raise CronError("one_time_completed must be a boolean")
    if not job["enabled"] or (job["schedule_type"] == "one_time" and one_time_completed):
        return []
    if processed_event_ids is not None and not isinstance(processed_event_ids, (set, frozenset, list, tuple)):
        raise CronError("processed trigger event IDs must be a collection")
    raw_seen = list(processed_event_ids or set())
    if not isinstance(events, list):
        raise CronError("startup events must be a list")
    if any(not isinstance(item, str) or not item or len(item) > 160 for item in raw_seen):
        raise CronError("processed trigger event IDs are invalid")
    seen = set(raw_seen)
    normalized: list[dict[str, str]] = []
    for event in events:
        if not isinstance(event, dict) or set(event) - {"source", "event_id", "boot_id"}:
            raise CronError("startup event fields are invalid")
        source, event_id = event.get("source"), event.get("event_id")
        boot_id = event.get("boot_id")
        if not isinstance(source, str) or source not in {"device_boot", "scheduler_recovery"} or not isinstance(event_id, str) or not event_id or len(event_id) > 160:
            raise CronError("startup event source or identity is invalid")
        if boot_id is not None and (not isinstance(boot_id, str) or not boot_id or len(boot_id) > 160):
            raise CronError("boot session identity is invalid")
        if source == "device_boot" and not job["run_after_device_boot"]:
            continue
        if source == "scheduler_recovery" and not job["run_after_scheduler_recovery"]:
            continue
        normalized.append({"source": source, "event_id": event_id, **({"boot_id": boot_id} if boot_id else {})})
    normalized.sort(key=lambda item: (0 if item["source"] == "device_boot" else 1, item["event_id"]))
    boot_ids = {item.get("boot_id", item["event_id"]) for item in normalized if item["source"] == "device_boot"}
    result: list[dict[str, str]] = []
    claimed: set[str] = set()
    for item in normalized:
        if item["event_id"] in seen or item["event_id"] in claimed:
            continue
        if item["source"] == "scheduler_recovery" and item.get("boot_id") in boot_ids:
            continue
        claimed.add(item["event_id"])
        result.append({"source": item["source"], "event_id": item["event_id"]})
    return result


def next_runs(job: dict[str, object], *, count: int = 5,
              now: dt.datetime | None = None) -> list[str]:
    if type(count) is not int or not 1 <= count <= 10:
        raise CronError("next-run count must be 1..10")
    job = validate_job(job, now=now, require_future=False)
    instant = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    stype, schedule = job["schedule_type"], job["schedule"]
    if stype == "one_time":
        value = _timestamp(schedule["at"], "one_time at", now=instant)
        return [value.isoformat().replace("+00:00", "Z")] if value > instant else []
    if stype == "calendar" and schedule["mode"] == "specific":
        value = _timestamp(schedule["datetime"], "specific datetime", now=instant)
        return [value.isoformat().replace("+00:00", "Z")] if value > instant else []
    if stype == "interval":
        anchor = _timestamp(schedule["anchor_at"], "anchor_at")
        seconds = schedule["interval_seconds"]
        elapsed = (instant - anchor).total_seconds()
        step = max(0, int(elapsed // seconds) + 1)
        return [(anchor + dt.timedelta(seconds=seconds * (step + idx))).isoformat().replace("+00:00", "Z") for idx in range(count)]
    zone = _timezone(schedule["timezone"] if stype == "cron" else schedule["timezone"])
    parsed = parse_cron(schedule["expression"]) if stype == "cron" else None
    daily_hour = daily_minute = None
    if stype == "calendar":
        daily_hour, daily_minute = map(int, schedule["time"].split(":"))
    cursor = instant.replace(second=0, microsecond=0) + dt.timedelta(minutes=1)
    results: list[str] = []
    for _ in range(MAX_SEARCH_MINUTES):
        local = cursor.astimezone(zone)
        match = _cron_matches(local, parsed) if parsed else (local.hour == daily_hour and local.minute == daily_minute and local.fold == 0)
        if match:
            results.append(cursor.isoformat().replace("+00:00", "Z"))
            if len(results) >= count:
                return results
        cursor += dt.timedelta(minutes=1)
    raise CronError("no next run found within the bounded five-year search horizon")


def _store_root(state_dir: str | os.PathLike[str], *, create: bool = True) -> Path | None:
    state = Path(state_dir)
    if not state.is_absolute():
        raise CronError("state directory must be absolute")
    try:
        st = state.lstat()
    except FileNotFoundError:
        if not create:
            return None
        raise CronError("Ternuxx state directory must already exist")
    if not state.is_dir() or state.is_symlink() or st.st_uid != os.getuid():
        raise CronError("Ternuxx state directory identity is unsafe")
    root = state / "cron"
    if not root.exists() and not root.is_symlink():
        if not create:
            return None
        try:
            root.mkdir(mode=0o700)
        except FileExistsError:
            pass
    st = root.lstat()
    if root.is_symlink() or not root.is_dir() or st.st_uid != os.getuid() or (st.st_mode & 0o077):
        raise CronError("Cron registry directory is unsafe")
    return root


def _lock(root: Path) -> Path:
    lock = root / LOCK_NAME
    try:
        lock.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise CronError("Cron registry is busy or has an unresolved lock") from exc
    fd = os.open(lock / "owner", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="ascii") as stream:
        stream.write(f"{os.getpid()}\n")
        stream.flush()
        os.fsync(stream.fileno())
    return lock


def _release_lock(lock: Path) -> None:
    owner = lock / "owner"
    st = owner.lstat()
    if owner.is_symlink() or not owner.is_file() or st.st_uid != os.getuid():
        raise CronError("Cron registry lock ownership is unsafe")
    owner.unlink()
    lock.rmdir()


def _read(root: Path) -> dict[str, object]:
    path = root / STORE_NAME
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "jobs": []}
    if path.is_symlink() or not path.is_file() or path.stat().st_uid != os.getuid() or (path.stat().st_mode & 0o077):
        raise CronError("Cron registry file identity or permissions are unsafe")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CronError("Cron registry is unreadable or corrupt") from exc
    if not isinstance(data, dict) or set(data) != {"schema_version", "jobs"} or data["schema_version"] != SCHEMA_VERSION or not isinstance(data["jobs"], list):
        raise CronError("Cron registry schema is unsupported or malformed")
    if len(data["jobs"]) > MAX_JOBS:
        raise CronError("Cron registry exceeds the supported job limit")
    jobs = [validate_job(job, require_future=False, allow_legacy_policies=True) for job in data["jobs"]]
    ids = [job["job_id"] for job in jobs]
    if len(ids) != len(set(ids)):
        raise CronError("Cron registry contains duplicate job IDs")
    return {"schema_version": SCHEMA_VERSION, "jobs": jobs}


def _write(root: Path, data: dict[str, object]) -> None:
    temp = root / (".jobs." + uuid.uuid4().hex + ".tmp")
    payload = (json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, root / STORE_NAME)
        os.chmod(root / STORE_NAME, 0o600)
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


def list_jobs(state_dir: str | os.PathLike[str]) -> list[dict[str, object]]:
    root = _store_root(state_dir, create=False)
    return [] if root is None else _read(root)["jobs"]


def show_job(state_dir: str | os.PathLike[str], job_id: str) -> dict[str, object]:
    for job in list_jobs(state_dir):
        if job["job_id"] == job_id:
            return job
    raise CronError("job was not found")


def create_job(state_dir: str | os.PathLike[str], job: dict[str, object]) -> dict[str, object]:
    root = _store_root(state_dir)
    lock = _lock(root)
    try:
        data = _read(root)
        candidate = validate_job(job)
        if any(existing["job_id"] == candidate["job_id"] for existing in data["jobs"]):
            raise CronError("job ID already exists")
        if len(data["jobs"]) >= MAX_JOBS:
            raise CronError("Cron registry job limit reached")
        data["jobs"].append(candidate)
        _write(root, data)
        return candidate
    finally:
        _release_lock(lock)


def update_job(state_dir: str | os.PathLike[str], job_id: str, changes: dict[str, object]) -> dict[str, object]:
    if not isinstance(changes, dict) or not changes or set(changes) - ({"name", "description", "action_id", "schedule_type", "schedule", "enabled", "run_after_device_boot", "run_after_scheduler_recovery", "timeout_seconds", "retry_policy", "missed_run_policy", "concurrency_policy", "environment", "required_capabilities", "output_policy"}):
        raise CronError("job update fields are invalid")
    root = _store_root(state_dir)
    lock = _lock(root)
    try:
        data = _read(root)
        for index, existing in enumerate(data["jobs"]):
            if existing["job_id"] == job_id:
                candidate = dict(existing)
                candidate.update(changes)
                candidate["updated_at"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
                candidate = validate_job(
                    candidate, require_future=("schedule" in changes or "schedule_type" in changes))
                data["jobs"][index] = candidate
                _write(root, data)
                return candidate
        raise CronError("job was not found")
    finally:
        _release_lock(lock)


def remove_job(state_dir: str | os.PathLike[str], job_id: str) -> dict[str, object]:
    root = _store_root(state_dir)
    lock = _lock(root)
    try:
        data = _read(root)
        kept = [job for job in data["jobs"] if job["job_id"] != job_id]
        if len(kept) == len(data["jobs"]):
            raise CronError("job was not found")
        data["jobs"] = kept
        _write(root, data)
        return {"job_id": job_id, "removed": True, "execution_data_removed": False}
    finally:
        _release_lock(lock)


def status(state_dir: str | os.PathLike[str]) -> dict[str, object]:
    jobs = list_jobs(state_dir)
    return {"registry_schema_version": SCHEMA_VERSION, "job_count": len(jobs),
            "scheduler": "not_installed", "process": "not_running",
            "execution": "core_available_no_scheduler", "device_boot_delivery": "not_qualified",
            "scheduler_recovery_delivery": "not_installed"}
