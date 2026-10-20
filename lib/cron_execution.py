#!/usr/bin/env python3
"""Durable Cron event claims and bounded execution outcomes.

No import, status query, or validation starts work. Dispatch requires a
lease-guarded scheduler caller and stable due-event identity. Device boot and
scheduler-recovery delivery remain disabled.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import uuid

import cron_registry

LEDGER_NAME = "executions.json"
SCHEMA_VERSION = 1
MAX_RECORDS = 5000
MAX_OUTPUT = 2048
MAX_SUMMARY = 512
_ID = re.compile(r"[A-Za-z0-9_.:-]{1,160}")
_TERMINAL = {"succeeded", "failed", "timed_out", "cancelled", "skipped", "blocked"}
_SECRET = re.compile(r"(?i)(\b(?:authorization|token|password|passwd|secret|api[_-]?key)\b\s*[:=]\s*)([^\s,;]+)")
_ACTIONS = {
    "diagnostics.doctor": ("doctor.report", []),
    "management.catalog.refresh": ("management.catalog", []),
    "hermes.status": ("agent.hermes.status", []),
    "scheduler.self_test": ("cron.executor.self_test", []),
}


class ExecutionError(ValueError):
    pass


def _stamp(value: dt.datetime | None = None) -> str:
    value = value or dt.datetime.now(dt.timezone.utc)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExecutionError("timestamps must include a timezone")
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_stamp(value: object, field: str) -> dt.datetime:
    if not isinstance(value, str) or len(value) > 40:
        raise ExecutionError(f"{field} must be a bounded ISO-8601 timestamp")
    try:
        result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ExecutionError(f"{field} is invalid") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ExecutionError(f"{field} must include a timezone")
    return result.astimezone(dt.timezone.utc)


def _ledger(root: Path) -> dict[str, object]:
    path = root / LEDGER_NAME
    if not path.exists() and not path.is_symlink():
        return {"schema_version": SCHEMA_VERSION, "records": []}
    st = path.lstat()
    if path.is_symlink() or not path.is_file() or st.st_uid != os.getuid() or (st.st_mode & 0o077):
        raise ExecutionError("execution ledger identity or permissions are unsafe")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExecutionError("execution ledger is unreadable or corrupt") from exc
    if (not isinstance(data, dict) or set(data) != {"schema_version", "records"}
            or type(data["schema_version"]) is not int or data["schema_version"] != SCHEMA_VERSION
            or not isinstance(data["records"], list) or len(data["records"]) > MAX_RECORDS):
        raise ExecutionError("execution ledger schema is unsupported or malformed")
    for item in data["records"]:
        _validate_record(item)
    if len({x["execution_id"] for x in data["records"]}) != len(data["records"]):
        raise ExecutionError("execution ledger has duplicate execution IDs")
    if len({(x["job_id"], x["event_id"]) for x in data["records"]}) != len(data["records"]):
        raise ExecutionError("execution ledger has duplicate event claims")
    return data


def _validate_record(item: object) -> None:
    fields = {"schema_version", "execution_id", "job_id", "event_id", "trigger_source",
              "scheduled_at", "status", "scheduler_instance_id", "attempt", "created_at",
              "claimed_at", "started_at", "completed_at", "exit_code", "failure_category",
              "duration_ms", "output_summary", "recovered"}
    if not isinstance(item, dict) or set(item) != fields:
        raise ExecutionError("execution record fields are malformed")
    if item["schema_version"] != SCHEMA_VERSION:
        raise ExecutionError("execution record schema is unsupported")
    for key in ("execution_id", "job_id", "event_id", "scheduler_instance_id"):
        if not isinstance(item[key], str) or not _ID.fullmatch(item[key]):
            raise ExecutionError(f"execution record {key} is invalid")
    if not re.fullmatch(r"job-[0-9a-f]{32}", item["job_id"]) or not item["execution_id"].startswith("exec-"):
        raise ExecutionError("execution or job identity is invalid")
    if item["trigger_source"] not in {"schedule", "device_boot", "scheduler_recovery", "manual"}:
        raise ExecutionError("execution trigger source is invalid")
    if item["status"] not in {"claimed", "running"} | _TERMINAL:
        raise ExecutionError("execution status is invalid")
    for key in ("scheduled_at", "created_at", "claimed_at"):
        _parse_stamp(item[key], key)
    for key in ("started_at", "completed_at"):
        if item[key] is not None:
            _parse_stamp(item[key], key)
    if type(item["attempt"]) is not int or not 1 <= item["attempt"] <= cron_registry.MAX_RETRIES:
        raise ExecutionError("execution attempt is invalid")
    if item["exit_code"] is not None and (type(item["exit_code"]) is not int or not -255 <= item["exit_code"] <= 255):
        raise ExecutionError("execution exit status is invalid")
    if item["failure_category"] is not None and item["failure_category"] not in {
            "action_failed", "action_unavailable", "timeout", "executor_error", "interrupted"}:
        raise ExecutionError("execution failure category is invalid")
    if item["duration_ms"] is not None and (type(item["duration_ms"]) is not int or item["duration_ms"] < 0):
        raise ExecutionError("execution duration is invalid")
    if not isinstance(item["output_summary"], str) or len(item["output_summary"]) > MAX_SUMMARY:
        raise ExecutionError("execution output summary is invalid")
    if type(item["recovered"]) is not bool:
        raise ExecutionError("execution recovered flag is invalid")


def _write(root: Path, data: dict[str, object]) -> None:
    records = data["records"]
    if len(records) > MAX_RECORDS:
        active_count = sum(x["status"] not in _TERMINAL for x in records)
        terminal_capacity = max(0, MAX_RECORDS - active_count)
        terminal = [x for x in records if x["status"] in _TERMINAL]
        keep_ids = {x["execution_id"] for x in terminal[-terminal_capacity:]} if terminal_capacity else set()
        records = [x for x in records if x["status"] not in _TERMINAL or x["execution_id"] in keep_ids]
        if len(records) > MAX_RECORDS:
            raise ExecutionError("execution ledger is full of active or unresolved records")
        data = {"schema_version": SCHEMA_VERSION, "records": records}
    temp = root / (".executions." + uuid.uuid4().hex + ".tmp")
    payload = (json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, root / LEDGER_NAME)
        os.chmod(root / LEDGER_NAME, 0o600)
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


def _locked(state_dir: str | os.PathLike[str]):
    root = cron_registry._store_root(state_dir)
    lock = cron_registry._lock(root)
    return root, lock


def _record(root: Path, execution_id: str) -> dict[str, object]:
    data = _ledger(root)
    for record in data["records"]:
        if record["execution_id"] == execution_id:
            return record
    raise ExecutionError("execution was not found")


def list_executions(state_dir: str | os.PathLike[str], *, job_id: str | None = None,
                    limit: int = 100) -> list[dict[str, object]]:
    if type(limit) is not int or not 1 <= limit <= 500:
        raise ExecutionError("history limit must be between 1 and 500")
    if job_id is not None and (not isinstance(job_id, str) or not job_id.startswith("job-") or not _ID.fullmatch(job_id)):
        raise ExecutionError("job ID is invalid")
    root = cron_registry._store_root(state_dir, create=False)
    if root is None:
        return []
    data = _ledger(root)
    records = data["records"]
    if job_id is not None:
        records = [x for x in records if x["job_id"] == job_id]
    return [dict(x) for x in records[-limit:]][::-1]


def show_execution(state_dir: str | os.PathLike[str], execution_id: str) -> dict[str, object]:
    if not isinstance(execution_id, str) or not execution_id.startswith("exec-") or not _ID.fullmatch(execution_id):
        raise ExecutionError("execution ID is invalid")
    root = cron_registry._store_root(state_dir, create=False)
    if root is None:
        raise ExecutionError("execution was not found")
    return dict(_record(root, execution_id))


def claim_event(state_dir: str | os.PathLike[str], *, job_id: str, event_id: str,
                scheduled_at: str, scheduler_instance_id: str,
                trigger_source: str = "schedule", now: dt.datetime | None = None) -> dict[str, object]:
    """Atomically claim one stable event; repeated claims return the original record."""
    if not all(isinstance(v, str) and _ID.fullmatch(v) for v in (job_id, event_id, scheduler_instance_id)):
        raise ExecutionError("job, event, or scheduler identity is invalid")
    if not job_id.startswith("job-"):
        raise ExecutionError("job identity is invalid")
    due = _parse_stamp(scheduled_at, "scheduled_at")
    current = now or dt.datetime.now(dt.timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ExecutionError("current time must include a timezone")
    if due > current.astimezone(dt.timezone.utc):
        raise ExecutionError("future events cannot be claimed")
    if trigger_source not in {"schedule", "device_boot", "scheduler_recovery", "manual"}:
        raise ExecutionError("trigger source is invalid")
    root, lock = _locked(state_dir)
    try:
        jobs = cron_registry._read(root)["jobs"]
        job = next((x for x in jobs if x["job_id"] == job_id), None)
        if job is None:
            raise ExecutionError("job was not found")
        try:
            cron_registry.require_supported_job(job)
        except cron_registry.CronError as exc:
            raise ExecutionError(f"job execution policy is unsupported: {exc}") from exc
        ledger = _ledger(root)
        existing = next((x for x in ledger["records"] if x["job_id"] == job_id and x["event_id"] == event_id), None)
        if existing is not None:
            return {"claimed": False, "duplicate": True, "record": dict(existing)}
        active = [x for x in ledger["records"] if x["job_id"] == job_id and x["status"] in {"claimed", "running"}]
        if job["schedule_type"] == "one_time" and any(
                x["status"] in {"succeeded", "failed", "timed_out", "cancelled"}
                for x in ledger["records"] if x["job_id"] == job_id):
            status, failure = "skipped", None
        elif trigger_source == "device_boot" and not job["run_after_device_boot"]:
            status, failure = "skipped", None
        elif trigger_source == "scheduler_recovery" and not job["run_after_scheduler_recovery"]:
            status, failure = "skipped", None
        elif not job["enabled"]:
            status, failure = "skipped", None
        elif job["retry_policy"]["max_attempts"] != 1:
            raise ExecutionError("automatic retry policy is not installed; use one attempt")
        elif active:
            if job["concurrency_policy"] == "queue_one":
                raise ExecutionError("queue_one is not dispatchable until a persistent worker queue is installed")
            status, failure = "skipped", None
        else:
            status, failure = "claimed", None
        now_text = _stamp(current)
        record = {"schema_version": SCHEMA_VERSION, "execution_id": "exec-" + uuid.uuid4().hex,
                  "job_id": job_id, "event_id": event_id, "trigger_source": trigger_source,
                  "scheduled_at": _stamp(due), "status": status, "scheduler_instance_id": scheduler_instance_id,
                  "attempt": 1, "created_at": now_text, "claimed_at": now_text,
                  "started_at": None, "completed_at": now_text if status == "skipped" else None,
                  "exit_code": None, "failure_category": None, "duration_ms": None,
                  "output_summary": "", "recovered": False}
        ledger["records"].append(record)
        _write(root, ledger)
        return {"claimed": status == "claimed", "duplicate": False, "record": dict(record)}
    finally:
        cron_registry._release_lock(lock)


def _redact(value: str) -> str:
    value = _SECRET.sub(lambda match: match.group(1) + "[REDACTED]", value)
    return value[:MAX_OUTPUT]


def _proc_start_identity(pid: int) -> str | None:
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
        fields = stat[stat.rfind(")") + 2:].split()
        return fields[19] if len(fields) > 19 else None
    except (OSError, IndexError):
        return None


def _registered_action(action_id: str, timeout_seconds: int) -> dict[str, object]:
    """Run only a fixed read-only management operation; no shell input is accepted."""
    if action_id not in _ACTIONS:
        raise ExecutionError("action is not registered")
    operation, extra = _ACTIONS[action_id]
    service = Path(__file__).with_name("management_service.py")
    argv = [sys.executable, str(service), "--operation", operation, *extra, "--json"]
    env = dict(os.environ)
    started = time.monotonic()
    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=False, env=env,
                               start_new_session=True, close_fds=True)
    start_identity = _proc_start_identity(process.pid)
    if not start_identity:
        process.terminate()
        process.wait(timeout=2)
        raise ExecutionError("cannot verify registered action process identity")
    import selectors
    selector = selectors.DefaultSelector()
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    streams = {"stdout": process.stdout, "stderr": process.stderr}
    for name, stream in streams.items():
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ, name)
    deadline = started + timeout_seconds
    try:
        while selector.get_map() or process.poll() is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("registered action exceeded its timeout")
            for key, _ in selector.select(min(0.1, remaining)):
                try:
                    chunk = os.read(key.fileobj.fileno(), 4096)
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                buffer = buffers[key.data]
                room = max(0, MAX_OUTPUT - len(buffer))
                if room:
                    buffer.extend(chunk[:room])
        process.wait(timeout=1)
    except TimeoutError:
        # Signal only the isolated process group that this executor created,
        # after checking PID start identity and session-leader relationship.
        try:
            if (_proc_start_identity(process.pid) == start_identity
                    and os.getpgid(process.pid) == process.pid):
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    if (_proc_start_identity(process.pid) == start_identity
                            and os.getpgid(process.pid) == process.pid):
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=2)
        except (OSError, ValueError, ProcessLookupError):
            pass
        raise
    finally:
        selector.close()
        for stream in streams.values():
            if stream and not stream.closed:
                stream.close()
    duration = int((time.monotonic() - started) * 1000)
    return {"exit_code": process.returncode,
            "stdout": buffers["stdout"].decode("utf-8", "replace"),
            "stderr": buffers["stderr"].decode("utf-8", "replace"),
            "duration_ms": duration}


def execute_claimed(state_dir: str | os.PathLike[str], execution_id: str, *,
                    executor=None, now: dt.datetime | None = None) -> dict[str, object]:
    """Execute one claimed event. The scheduler itself is not started here.

    Tests may inject a controlled executor. Production uses a fixed allowlist
    of read-only management operations and never accepts command strings.
    """
    if not isinstance(execution_id, str) or not execution_id.startswith("exec-") or not _ID.fullmatch(execution_id):
        raise ExecutionError("execution ID is invalid")
    root, lock = _locked(state_dir)
    try:
        record = _record(root, execution_id)
        if record["status"] != "claimed":
            raise ExecutionError("only a claimed execution can be launched")
        job = next((x for x in cron_registry._read(root)["jobs"] if x["job_id"] == record["job_id"]), None)
        if job is None or not job["enabled"]:
            raise ExecutionError("job is missing or disabled; execution remains unlaunched")
        try:
            cron_registry.require_supported_job(job)
        except cron_registry.CronError as exc:
            raise ExecutionError(f"job execution policy is unsupported: {exc}") from exc
        ledger = _ledger(root)
        record = next((x for x in ledger["records"] if x["execution_id"] == execution_id), None)
        if record is None or record["status"] != "claimed":
            raise ExecutionError("execution state changed before launch")
        record["status"] = "running"
        record["started_at"] = _stamp(now)
        _write(root, ledger)
        action_id = job["action_id"]
        timeout_seconds = job["timeout_seconds"]
        output_policy = job["output_policy"]
    finally:
        cron_registry._release_lock(lock)

    started = time.monotonic()
    try:
        outcome = (executor or _registered_action)(action_id, timeout_seconds)
        if not isinstance(outcome, dict) or set(outcome) - {"exit_code", "stdout", "stderr", "duration_ms"}:
            raise ExecutionError("executor returned an invalid result")
        code = outcome.get("exit_code")
        if type(code) is not int or not -255 <= code <= 255:
            raise ExecutionError("executor returned an invalid exit code")
        output = ""
        if output_policy == "bounded_redacted":
            output = _redact(str(outcome.get("stdout", "")) + str(outcome.get("stderr", "")))
        final_status = "succeeded" if code == 0 else "failed"
        failure = None if code == 0 else "action_failed"
        duration = outcome.get("duration_ms", int((time.monotonic() - started) * 1000))
        if type(duration) is not int or duration < 0:
            raise ExecutionError("executor returned an invalid duration")
    except TimeoutError:
        final_status, failure, code, duration, output = "timed_out", "timeout", None, int((time.monotonic() - started) * 1000), ""
    except Exception:
        final_status, failure, code, duration, output = "failed", "executor_error", None, int((time.monotonic() - started) * 1000), ""

    root, lock = _locked(state_dir)
    try:
        ledger = _ledger(root)
        record = next((x for x in ledger["records"] if x["execution_id"] == execution_id), None)
        if record is None or record["status"] != "running":
            raise ExecutionError("execution state changed while action was running")
        record.update({"status": final_status, "completed_at": _stamp(),
                       "exit_code": code, "failure_category": failure,
                       "duration_ms": duration, "output_summary": output[:MAX_SUMMARY]})
        _write(root, ledger)
        return dict(record)
    finally:
        cron_registry._release_lock(lock)


def status(state_dir: str | os.PathLike[str]) -> dict[str, object]:
    root = cron_registry._store_root(state_dir, create=False)
    if root is None:
        return {"ledger_schema_version": SCHEMA_VERSION, "record_count": 0,
                "unresolved_count": 0, "execution_core": "typed_action_executor_available", "scheduler": "runtime_status_reported_by_cron_status"}
    data = _ledger(root)
    unresolved = sum(x["status"] in {"claimed", "running"} for x in data["records"])
    return {"ledger_schema_version": SCHEMA_VERSION, "record_count": len(data["records"]),
            "unresolved_count": unresolved, "execution_core": "typed_action_executor_available",
            "scheduler": "runtime_status_reported_by_cron_status"}
