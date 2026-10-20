"""Termux-compatible Cron scheduler process lifecycle (no boot integration)."""
from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path
import signal
import sys
import time
import uuid
import threading

import cron_scheduler
import cron_registry

_STOP = False
_STOP_EVENT = threading.Event()


def _request_stop(_signum=None, _frame=None) -> None:
    global _STOP
    _STOP = True
    _STOP_EVENT.set()


def serve(state_dir: str, *, poll_seconds: int = 5) -> int:
    global _STOP
    _STOP = False
    _STOP_EVENT.clear()
    if type(poll_seconds) is not int or not 1 <= poll_seconds <= 60:
        raise ValueError("poll interval must be 1..60 seconds")
    instance = os.environ.get("TERNUXX_SCHEDULER_INSTANCE")
    lease = cron_scheduler.SchedulerLease(state_dir, instance_id=instance)
    lease.acquire()
    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)
    try:
        while not _STOP:
            now = dt.datetime.now(dt.timezone.utc)
            try:
                report = cron_scheduler.poll_once(state_dir, lease, now=now,
                                                  poll_seconds=poll_seconds)
                dispatched = report["dispatched"]
                error = report["errors"][0]["error"] if report["errors"] else None
                lease.heartbeat(poll_at=report["polled_at"],
                                dispatch_at=report["polled_at"] if dispatched else None,
                                error=error)
            except Exception as exc:
                lease.heartbeat(poll_at=now.isoformat(),
                                error=cron_execution_redacted(exc))
            # Event.wait permits prompt, bounded graceful shutdown without busy polling.
            _STOP_EVENT.wait(poll_seconds)
    finally:
        lease.close()
    return 0


def cron_execution_redacted(exc: Exception) -> str:
    import cron_execution
    return cron_execution._redact(type(exc).__name__ + ": " + str(exc))[:180]


def _runtime_context(state_dir: str) -> tuple[Path, dict[str, object]]:
    root = cron_scheduler._safe_root(state_dir, create=False)
    record = cron_scheduler._read_state(root)
    if record is None:
        raise cron_scheduler.SchedulerError("scheduler is not running")
    return root, record


def _process_matches(record: dict[str, object], *, daemon_script: Path) -> bool:
    pid = record["pid"]
    if not cron_scheduler._proc_alive(pid, record["process_start"]):
        return False
    proc = Path(f"/proc/{pid}")
    try:
        cmdline = (proc / "cmdline").read_bytes().split(b"\0")
        environ = (proc / "environ").read_bytes().split(b"\0")
    except OSError:
        return False
    command = [item.decode("utf-8", "replace") for item in cmdline if item]
    environment = [item.decode("utf-8", "replace") for item in environ if item]
    marker = "TERNUXX_SCHEDULER_INSTANCE=" + record["instance_id"]
    return (marker in environment and str(daemon_script) in command
            and "serve" in command and "--state-dir" in command)


def status(state_dir: str) -> dict[str, object]:
    return cron_scheduler.status(state_dir)


def start(state_dir: str, *, poll_seconds: int = 5, startup_timeout: float = 5.0) -> dict[str, object]:
    if type(poll_seconds) is not int or not 1 <= poll_seconds <= 60:
        raise cron_scheduler.SchedulerError("poll interval must be 1..60 seconds")
    current = cron_scheduler.status(state_dir)
    if current["status"] == "running":
        return {"started": False, "already_running": True, "status": current}
    if current["status"] not in {"not_installed", "stopped"}:
        raise cron_scheduler.SchedulerError("scheduler ownership is unknown or degraded; refusing start")
    root = cron_scheduler._safe_root(state_dir, create=True)
    identifier = "sched-" + uuid.uuid4().hex
    log_path = root / "scheduler.log"
    if log_path.is_symlink():
        raise cron_scheduler.SchedulerError("scheduler log path is a symlink")
    fd = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        proc = os.fstat(fd)
        if not __import__("stat").S_ISREG(proc.st_mode) or proc.st_uid != os.getuid() or proc.st_mode & 0o077:
            raise cron_scheduler.SchedulerError("scheduler log identity or permissions are unsafe")
        script = Path(__file__).resolve()
        env = dict(os.environ)
        env["TERNUXX_SCHEDULER_INSTANCE"] = identifier
        env["TERNUXX_STATE_DIR"] = str(Path(state_dir).absolute())
        child_pid = os.fork()
        if child_pid == 0:
            try:
                os.setsid()
                null_fd = os.open(os.devnull, os.O_RDONLY)
                os.dup2(null_fd, 0)
                os.dup2(fd, 1)
                os.dup2(fd, 2)
                os.closerange(3, 65536)
                argv = [sys.executable, str(script), "serve", "--state-dir",
                        str(Path(state_dir).absolute()), "--poll-seconds", str(poll_seconds)]
                os.execve(sys.executable, argv, env)
            except BaseException:
                os._exit(127)
    finally:
        os.close(fd)
    deadline = time.monotonic() + startup_timeout
    while time.monotonic() < deadline:
        try:
            exited_pid, _status = os.waitpid(child_pid, os.WNOHANG)
        except ChildProcessError:
            exited_pid = child_pid
        if exited_pid == child_pid:
            raise cron_scheduler.SchedulerError("scheduler exited during startup; inspect its bounded log")
        current = cron_scheduler.status(state_dir)
        if current.get("status") == "running" and current.get("instance_id") == identifier:
            return {"started": True, "status": current, "pid": child_pid}
        time.sleep(0.05)
    start_id = cron_scheduler._proc_start(child_pid)
    if start_id is not None and cron_scheduler._proc_alive(child_pid, start_id):
        os.kill(child_pid, signal.SIGTERM)
        shutdown_deadline = time.monotonic() + 2
        while time.monotonic() < shutdown_deadline and cron_scheduler._proc_alive(child_pid, start_id):
            time.sleep(0.05)
        try:
            os.waitpid(child_pid, os.WNOHANG)
        except ChildProcessError:
            pass
    raise cron_scheduler.SchedulerError("scheduler readiness timed out; no force-kill was attempted")


def stop(state_dir: str, *, confirmed: bool = False, timeout: float = 3.0) -> dict[str, object]:
    if confirmed is not True:
        raise cron_scheduler.SchedulerError("scheduler stop requires explicit confirmation")
    root, record = _runtime_context(state_dir)
    script = Path(__file__).resolve()
    runtime = cron_scheduler.status(state_dir)
    if (not _process_matches(record, daemon_script=script)
            or runtime.get("instance_id") != record["instance_id"]
            or runtime.get("lease_held") is not True
            or runtime.get("process_alive") is not True):
        raise cron_scheduler.SchedulerError("scheduler process or lease ownership cannot be verified")
    pid, start_id, instance = record["pid"], record["process_start"], record["instance_id"]
    # Revalidate immediately before signaling.
    current = cron_scheduler._read_state(root)
    if (current is None or current["instance_id"] != instance
            or current["pid"] != pid or current["process_start"] != start_id
            or not _process_matches(current, daemon_script=script)):
        raise cron_scheduler.SchedulerError("scheduler identity changed before stop")
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not cron_scheduler._proc_alive(pid, start_id):
            return {"stopped": True, "instance_id": instance, "pid": pid}
        time.sleep(0.05)
    return {"stopped": False, "stop_requested": True, "instance_id": instance,
            "pid": pid, "reason": "graceful shutdown has not completed; process left running"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    daemon = sub.add_parser("serve")
    daemon.add_argument("--state-dir", required=True)
    daemon.add_argument("--poll-seconds", type=int, default=5)
    args = parser.parse_args(argv)
    try:
        return serve(args.state_dir, poll_seconds=args.poll_seconds)
    except Exception:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
