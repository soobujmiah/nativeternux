#!/data/data/com.termux/files/usr/bin/python
"""Typed local bridge for the GTK management client; delegates to the shared core."""
from __future__ import annotations

import json
import re
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import management_service  # noqa: E402
import management_sessions  # noqa: E402


def call(operation: str, args: dict[str, object] | None = None) -> dict[str, object]:
    return management_service.dispatch({
        "api_version": management_service.API_VERSION,
        "request_id": uuid.uuid4().hex,
        "operation": operation,
        "args": args or {},
    }, caller="local_cli", env=dict(os.environ))


def clean(value: object) -> str:
    return str(value if value is not None else "").replace("\t", " ").replace("\r", " ").replace("\n", " ")


def main(argv: list[str]) -> int:
    if not os.environ.get("TERMUX_VERSION") or os.environ.get("PREFIX") != "/data/data/com.termux/files/usr":
        print("Native Termux is required.", file=sys.stderr)
        return 2
    os.environ.setdefault("TERNUXX_STATE_DIR", str(Path.home() / ".local/share/ternuxx"))
    if not argv:
        print("Typed management action required.", file=sys.stderr)
        return 2
    action = argv[0]
    if action == "catalog" and len(argv) == 1:
        result = call("management.catalog")
        if not result.get("ok"):
            print(json.dumps(result, ensure_ascii=False))
            return 1
        data = result["data"]
        for item in data["categories"]:
            print("C\t" + "\t".join(clean(item.get(k)) for k in ("id", "name", "description", "status")))
        for item in data["resources"]:
            print("R\t" + "\t".join(clean(item.get(k)) for k in (
                "id", "category_id", "name", "status", "availability", "description")))
        return 0
    if action == "inspect" and len(argv) == 2:
        rid = argv[1]
        operation_args: dict[str, object] = {}
        if rid == "network.ssh.manual-8022":
            operation = "ssh.inspect"
        elif rid == "native.acceleration.qualification":
            operation = "doctor.report"
            # Bounded, read-only probes inspect this process's current display;
            # they never launch a server, workload, or guest.
            operation_args = {"graphics": True}
        elif rid == "network.ssh.managed-8023":
            operation = "native.ssh.status"
        else:
            catalog = call("management.catalog")
            resource = next((r for r in catalog.get("data", {}).get("resources", []) if r["id"] == rid), None)
            if resource is None:
                print(json.dumps({"ok": False, "error": {"code": "unknown_resource"}}))
                return 2
            operation = next((op for op in resource["supported_operations"]
                              if op != "management.catalog"
                              and op in management_service.OPERATIONS
                              and (not management_service.OPERATIONS[op]["args"] or op == "doctor.report")
                              and op not in management_sessions.MUTATING_OPERATIONS), None)
            if operation == "doctor.report":
                operation_args = {"graphics": False}
            if operation is None:
                print(json.dumps({"ok": False, "error": {"code": "live_status_unavailable"}}))
                return 3
        result = call(operation, operation_args) if operation_args else call(operation)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1
    if action == "cron-jobs" and len(argv) == 1:
        result = call("cron.jobs.list")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1
    if action == "history" and len(argv) == 1:
        result = call("recovery.status")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1
    if action in {"ssh-preview-start", "ssh-preview-stop"} and len(argv) == 1:
        operation = "ssh.service.start" if action.endswith("start") else "ssh.service.stop"
        result = call(operation, {"confirmed": False, "plan_id": None})
        if not result.get("ok"):
            print(json.dumps(result, ensure_ascii=False))
            return 1
        data = result.get("data", {})
        fields = ("P", clean(data.get("plan_id")) or "-",
                  str(bool(data.get("requires_confirmation"))).lower(),
                  clean(data.get("impact")))
        print("\t".join(fields))
        return 0
    if action in {"ssh-apply-start", "ssh-apply-stop"} and len(argv) == 3 and argv[1] == "confirmed":
        plan_id = argv[2]
        if not re.fullmatch(r"[0-9a-f]{64}", plan_id):
            print(json.dumps({"ok": False, "error": {"code": "invalid_plan_id"}}))
            return 2
        operation = "ssh.service.start" if action.endswith("start") else "ssh.service.stop"
        result = call(operation, {"confirmed": True, "plan_id": plan_id})
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1
    if action in {"start-desktop", "stop-desktop"} and len(argv) == 2 and argv[1] == "confirmed":
        result = call("desktop.start" if action == "start-desktop" else "desktop.stop")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1
    if action == "monitor" and len(argv) == 1:
        result = call("desktop.monitor.status")
        if not result.get("ok"):
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 1
        data = result["data"]
        print("M\t" + "\t".join(clean(data.get(k)) for k in (
            "enabled", "interval_seconds", "focus_check", "activity_launch")))
        return 0
    if action == "set-monitor" and len(argv) == 6:
        enabled, interval, unit, focus, launch = argv[1:]
        if (any(value not in {"true", "false"} for value in (enabled, focus, launch))
                or not interval.isdecimal() or unit not in {"seconds", "minutes", "hours"}):
            print(json.dumps({"ok": False, "error": {"code": "invalid_arguments"}}))
            return 2
        result = call("desktop.monitor.configure", {
            "enabled": enabled == "true", "interval_value": int(interval), "unit": unit,
            "focus_check": focus == "true", "activity_launch": launch == "true",
        })
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1
    print("Unsupported typed management action.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
