#!/usr/bin/env python3
"""Opt-in Native Runit replay in a private service root; no workstation restart."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import gui_monitoring
import fixed_service_deployment as deployment


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval-check", action="store_true",
                        help="also verify two Linux-only ticks 30 seconds apart in private test state")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    prefix = Path(os.environ.get("PREFIX", ""))
    if str(prefix) != "/data/data/com.termux/files/usr" or not os.environ.get("TERMUX_VERSION"):
        parser.error("Native Termux is required")
    for command in ("sv", "runsvdir", "runsv"):
        if not (prefix / "bin" / command).is_file():
            parser.error("termux-services/Runit tools are required")
    real_state = Path(os.environ.get("TERNUXX_STATE_DIR", str(Path.home() / ".local/share/ternuxx")))
    real_policy = real_state / "gui-monitoring.json"
    before = real_policy.read_bytes() if real_policy.exists() else None
    private = Path(tempfile.mkdtemp(prefix="ternuxx-monitor-replay-", dir=prefix / "tmp"))
    private.chmod(0o700)
    test_prefix = private / "prefix"
    services = test_prefix / "var/service"
    services.mkdir(parents=True, mode=0o700)
    (test_prefix / "bin").mkdir()
    shutil.copy2(prefix / "bin/sv", test_prefix / "bin/sv")
    state = private / "state"
    state.mkdir(mode=0o700)
    env = dict(os.environ, TERNUXX_STATE_DIR=str(state))
    watcher = None
    target = services / deployment.MONITOR_SERVICE_ID
    cleanup_safe = False
    report = {}
    try:
        watcher = subprocess.Popen([str(prefix / "bin/runsvdir"), str(services)],
            env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True)
        time.sleep(.3)
        if watcher.poll() is not None:
            raise RuntimeError("private Runit watcher exited")
        # The service child inherits this private state from its own watcher.
        plan = deployment.preview_install(prefix=test_prefix, service_id=deployment.MONITOR_SERVICE_ID)
        result = deployment.install(prefix=test_prefix, service_id=deployment.MONITOR_SERVICE_ID,
                                    confirmed=True, plan_id=plan["plan_id"])
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            current = gui_monitoring.status(state)
            if current["scheduler"] == "running_idle":
                break
            time.sleep(.1)
        if current["scheduler"] != "running_idle":
            raise RuntimeError("private scheduler did not become idle")
        time.sleep(1)
        if (state / "gui-monitoring.json").exists() or (state / "log").exists():
            raise RuntimeError("disabled scheduler wrote monitoring policy or logs")
        ticks = []
        if args.interval_check:
            gui_monitoring.configure(state, enabled=True, interval_value=30, unit="seconds",
                                     focus_check=False, activity_launch=False)
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                current = gui_monitoring.status(state)
                checked = current["last_check_at"]
                if checked and checked not in ticks:
                    ticks.append(checked)
                if len(ticks) >= 2:
                    break
                time.sleep(.2)
            if len(ticks) < 2:
                raise RuntimeError("private scheduler did not deliver two interval checks")
            elapsed = (dt.datetime.fromisoformat(ticks[1]) - dt.datetime.fromisoformat(ticks[0])).total_seconds()
            if not 29 <= elapsed <= 40:
                raise RuntimeError("private scheduler interval was outside tolerance")
            logs = [json.loads(line) for line in (state / "log/gui-monitoring.log").read_text().splitlines()]
            if not all(x["activity_request_status"] == "not_requested" and x["focus_status"] == "not_requested" for x in logs):
                raise RuntimeError("private Linux-only run attempted Activity/focus work")
        installed = deployment.status(prefix=test_prefix, service_id=deployment.MONITOR_SERVICE_ID)
        if installed["status"] != "running" or installed["source_matches"] is not True:
            raise RuntimeError("private live/source service parity failed")
        if (real_policy.read_bytes() if real_policy.exists() else None) != before:
            raise RuntimeError("workstation monitoring policy changed during replay")
        report = {"schema_version": 1, "observed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                  "service_id": deployment.MONITOR_SERVICE_ID, "fresh_isolated_registration": result["service_started"],
                  "idle_default_verified": True, "source_matches": installed["source_matches"],
                  "interval_check": bool(args.interval_check), "tick_count": len(ticks),
                  "tick_interval_seconds": elapsed if args.interval_check else None,
                  "workstation_policy_unchanged": True, "activity_launch_enabled": False,
                  "focus_check_enabled": False,
                  "run_sha256": installed["run_sha256"],
                  "module_sha256": hashlib.sha256((ROOT / "lib/gui_monitoring.py").read_bytes()).hexdigest()}
    finally:
        # Stop only the watcher we created, then its exact private service.
        # Existing Native services and desktop are not addressed.
        if watcher is not None:
            if watcher.poll() is None:
                watcher.terminate()
                watcher.wait(timeout=5)
            if target.exists():
                stopped = subprocess.run([str(prefix / "bin/sv"), "-w", "5", "exit", str(target)],
                    capture_output=True, timeout=8, check=False)
                cleanup_safe = stopped.returncode == 0
            else:
                cleanup_safe = True
        else:
            cleanup_safe = True
        if cleanup_safe:
            shutil.rmtree(private)
        else:
            print("Private replay cleanup incomplete; preserved exact target: " + str(private), file=sys.stderr)
    if not cleanup_safe:
        raise RuntimeError("private Runit service exit was not confirmed")
    report["private_service_exited_and_removed"] = True
    payload = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(payload)
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
