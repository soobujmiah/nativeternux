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
import management_presentation  # noqa: E402


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
    if action == "software-run" and len(argv) == 2:
        result = call("software.app.run", {"app_id": "directory-tree", "path": argv[1]})
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "software-preview" and len(argv) == 3 and argv[1] in {"process-monitor", "terminal-multiplexer", "directory-tree"} and argv[2] in {"install", "update", "remove"}:
        result = call("software.app.preview", {"app_id": argv[1], "action": argv[2]})
        if not result.get("ok"):
            print(management_presentation.format_report(result)); return 1
        data = result.get("data", {})
        plan_id = data.get("plan_id")
        if not isinstance(plan_id, str) or not re.fullmatch(r"[0-9a-f]{64}", plan_id):
            print("Native app preview returned an invalid plan."); return 1
        print("P\t" + plan_id + "\t" + argv[1] + "\t" + argv[2] + "\t" + clean(json.dumps(data, sort_keys=True)))
        return 0
    if action == "software-apply" and len(argv) == 5 and argv[1] in {"process-monitor", "terminal-multiplexer", "directory-tree"} and argv[2] in {"install", "update", "remove"}:
        plan_id = argv[3]
        if not re.fullmatch(r"[0-9a-f]{64}", plan_id):
            print("Native app preview expired; create a new preview."); return 2
        result = call("software.app.apply", {"app_id": argv[1], "action": argv[2], "plan_id": plan_id,
                                             "confirmation": argv[4]})
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "cpu-run" and len(argv) == 1:
        prompt = sys.stdin.read(management_service.cpu_inference.MAX_PROMPT_BYTES + 1)
        result = call("inference.cpu.run", {"prompt": prompt, "max_tokens": 64})
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "cpu-model-preview" and len(argv) == 2 and argv[1] in {"install", "remove"}:
        result = call("inference.cpu.model.preview", {"action": argv[1]})
        if not result.get("ok"):
            print(management_presentation.format_report(result)); return 1
        data = result.get("data", {})
        print("P\t" + clean(data.get("plan_id")) + "\t" + clean(json.dumps(data, sort_keys=True)))
        return 0
    if action == "cpu-model-apply" and len(argv) == 4 and argv[3] == "confirmed" and argv[1] in {"install", "remove"}:
        plan_id = argv[2]
        if not re.fullmatch(r"[0-9a-f]{24}", plan_id):
            print("The CPU model preview is invalid; create a new preview.", file=sys.stderr); return 2
        result = call("inference.cpu.model.apply", {"action": argv[1], "plan_id": plan_id, "confirmed": True})
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "graphics-select" and len(argv) == 2 and argv[1] in {"kgsl-freedreno", "system"}:
        result = call("graphics.provider.select", {"provider": "native", "backend": argv[1], "confirmed": True})
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "graphics-verify" and len(argv) == 3:
        provider, api = argv[1], argv[2]
        result = call("graphics.provider.verify", {"provider": provider, "api": api, "display": ":1"})
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "catalog" and len(argv) == 1:
        result = call("management.catalog")
        if not result.get("ok"):
            print(management_presentation.format_report(result))
            return 1
        data = result["data"]
        categories = data["categories"]
        for item in categories:
            print("C\t" + "\t".join(clean(item.get(k)) for k in ("id", "name", "description", "status")))
        resources = sorted(data["resources"], key=lambda item: (str(item.get("category_id", "")), str(item.get("name", "")).casefold()))
        for item in resources:
            operation_names = [management_presentation.operation_label(op)
                               for op in item.get("supported_operations", [])]
            print("R\t" + "\t".join(clean(item.get(k)) for k in (
                "id", "category_id", "name", "status", "availability", "description"))
                  + "\t" + clean(", ".join(operation_names)))
        return 0
    if action == "ssh-autostart-status" and len(argv) == 1:
        result = call("ssh.service.autostart.status")
        if not result.get("ok"):
            print(management_presentation.format_report(result))
            return 1
        enabled = result.get("data", {}).get("enabled")
        if type(enabled) is not bool:
            print("Could not verify the SSH startup preference.")
            return 1
        print("S\t" + ("true" if enabled else "false"))
        return 0
    if action == "ssh-autostart-preview" and len(argv) == 2 and argv[1] in {"enabled", "disabled"}:
        enabled = argv[1] == "enabled"
        result = call("ssh.service.autostart.preview", {"enabled": enabled})
        if not result.get("ok"):
            print(management_presentation.format_report(result))
            return 1
        data = result.get("data", {})
        if data.get("changed") is not True:
            print(management_presentation.format_report(result))
            return 0
        plan_id = data.get("plan_id")
        if not isinstance(plan_id, str) or not re.fullmatch(r"[0-9a-f]{32}", plan_id):
            print("Could not verify the exact SSH startup preference plan.")
            return 1
        print("P\t" + plan_id + "\t" + ("true" if enabled else "false") + "\t"
              + clean(data.get("effect")))
        return 0
    if action == "ssh-autostart-apply" and len(argv) == 4 and argv[1] == "confirmed" and argv[2] in {"true", "false"}:
        enabled = argv[2] == "true"
        plan_id = argv[3]
        if not re.fullmatch(r"[0-9a-f]{32}", plan_id):
            print("SSH startup preference preview expired; create a new preview.")
            return 2
        result = call("ssh.service.autostart.apply", {
            "enabled": enabled, "confirmed": True, "plan_id": plan_id})
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "ssh-wakelock-status" and len(argv) == 1:
        result = call("wakelock.ssh-policy.status")
        if not result.get("ok"):
            print(management_presentation.format_report(result)); return 1
        enabled = result.get("data", {}).get("persistent_lease_enabled")
        if type(enabled) is not bool:
            print("Could not verify the managed SSH Wake Lock preference."); return 1
        print("S\t" + ("true" if enabled else "false")); return 0
    if action == "ssh-wakelock-preview" and len(argv) == 2 and argv[1] in {"enabled", "disabled"}:
        enabled = argv[1] == "enabled"
        result = call("wakelock.ssh-policy.preview", {"enabled": enabled})
        if not result.get("ok"):
            print(management_presentation.format_report(result)); return 1
        data = result.get("data", {})
        if data.get("changed") is not True:
            print(management_presentation.format_report(result)); return 0
        plan_id = data.get("plan_id")
        if not isinstance(plan_id, str) or not re.fullmatch(r"[0-9a-f]{32}", plan_id):
            print("Could not verify the exact Wake Lock preference plan."); return 1
        print("P\t" + plan_id + "\t" + ("true" if enabled else "false") + "\t" + clean(data.get("effect")))
        return 0
    if action == "ssh-wakelock-apply" and len(argv) == 4 and argv[1] == "confirmed" and argv[2] in {"true", "false"}:
        enabled = argv[2] == "true"; plan_id = argv[3]
        if not re.fullmatch(r"[0-9a-f]{32}", plan_id):
            print("Wake Lock preference preview expired; create a new preview."); return 2
        result = call("wakelock.ssh-policy.apply", {"enabled": enabled, "confirmed": True, "plan_id": plan_id})
        print(management_presentation.format_report(result)); return 0 if result.get("ok") else 1
    if action == "ssh-client-key-preview" and len(argv) == 2:
        result = call("ssh.client-key.create.preview", {"name": argv[1]})
        if not result.get("ok"):
            print(management_presentation.format_report(result))
            return 1
        data = result.get("data", {})
        plan_id = data.get("plan_id")
        if data.get("changed") is not True:
            print(management_presentation.format_report(result))
            return 0
        if not isinstance(plan_id, str) or not re.fullmatch(r"[0-9a-f]{32}", plan_id):
            print("Could not verify the exact Native SSH recovery key plan.")
            return 1
        impact = "Creates a local Ed25519 private key (mode 0600); it is not enrolled yet."
        print("P\t" + plan_id + "\t" + clean(data.get("name")) + "\t"
              + clean(data.get("private_key_path")) + "\t" + impact)
        return 0
    if action == "ssh-client-key-apply" and len(argv) == 4 and argv[1] == "confirmed":
        name, plan_id = argv[2:]
        if not re.fullmatch(r"[0-9a-f]{32}", plan_id):
            print("The Native SSH key preview expired; create a new preview.")
            return 2
        result = call("ssh.client-key.create.apply", {
            "name": name, "confirmed": True, "plan_id": plan_id})
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action in {"ssh-key-add-preview", "ssh-key-remove-preview"} and len(argv) == 2:
        operation = "ssh.keys.add.preview" if action == "ssh-key-add-preview" else "ssh.keys.remove.preview"
        args = {"public_key": argv[1]} if action == "ssh-key-add-preview" else {"fingerprint": argv[1]}
        result = call(operation, args)
        if not result.get("ok"):
            print(management_presentation.format_report(result))
            return 1
        data = result.get("data", {})
        plan_id = data.get("plan_id")
        fingerprint = data.get("fingerprint")
        if not isinstance(plan_id, str) or not re.fullmatch(r"[0-9a-f]{24}", plan_id) or not isinstance(fingerprint, str):
            print("Could not verify the exact SSH key change preview.")
            return 1
        impact = "Shared authorized keys for owner-managed SSH 8022 and Ternuxx SSH 8023. "
        impact += ("Adds " if action == "ssh-key-add-preview" else "Removes ") + fingerprint
        print("P\t" + plan_id + "\t" + fingerprint + "\t" + clean(impact))
        return 0
    if action in {"ssh-key-add-apply", "ssh-key-remove-apply"} and len(argv) == 4 and argv[1] == "confirmed":
        subject, plan_id = argv[2:]
        if not re.fullmatch(r"[0-9a-f]{24}", plan_id):
            print("The SSH key change preview expired; create a new preview.")
            return 2
        is_add = action == "ssh-key-add-apply"
        operation = "ssh.keys.add.apply" if is_add else "ssh.keys.remove.apply"
        args = ({"public_key": subject} if is_add else {"fingerprint": subject})
        args.update({"confirmed": True, "plan_id": plan_id})
        result = call(operation, args)
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "ssh-key-rollback-list" and len(argv) == 1:
        result = call("ssh.keys.rollback.list")
        if not result.get("ok"):
            print(management_presentation.format_report(result)); return 1
        entries = result.get("data", {}).get("entries", [])
        for entry in entries:
            print("R\t" + clean(entry.get("rollback_id")) + "\t" + clean(entry.get("fingerprint"))
                  + "\t" + clean(entry.get("action")) + "\t" + clean(entry.get("status")))
        if not entries: print("R\t-\t-\t-\t-")
        return 0
    if action == "ssh-key-rollback-preview" and len(argv) == 2:
        result = call("ssh.keys.rollback.preview", {"rollback_id": argv[1]})
        if not result.get("ok"):
            print(management_presentation.format_report(result)); return 1
        data = result.get("data", {}); plan_id = data.get("plan_id")
        if not isinstance(plan_id, str) or not re.fullmatch(r"[0-9a-f]{24}", plan_id):
            print("Could not verify the exact SSH recovery preview."); return 1
        print("P\t" + plan_id + "\t" + clean(data.get("rollback_id")) + "\t" + clean(data.get("effect")))
        return 0
    if action == "ssh-key-rollback-apply" and len(argv) == 3:
        rollback_id, plan_id = argv[1:]
        if not re.fullmatch(r"[0-9a-f]{32}", rollback_id) or not re.fullmatch(r"[0-9a-f]{24}", plan_id):
            print("The SSH recovery preview is invalid or expired."); return 2
        result = call("ssh.keys.rollback.apply", {"rollback_id": rollback_id,
            "confirmed": True, "plan_id": plan_id})
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "ssh-keys-list" and len(argv) == 1:
        result = call("ssh.keys.list")
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "inspect" and len(argv) == 2:
        rid = argv[1]
        operation_args: dict[str, object] = {}
        if rid == "graphics.native":
            operation = "graphics.provider.status"
            operation_args = {"provider": "native"}
        elif rid == "network.ssh.manual-8022":
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
                print(management_presentation.format_report(
                    {"ok": False, "error": {"code": "unknown_resource"}}))
                return 2
            operation = next((op for op in resource["supported_operations"]
                              if op != "management.catalog"
                              and op in management_service.OPERATIONS
                              and (not management_service.OPERATIONS[op]["args"] or op == "doctor.report")
                              and op not in management_sessions.MUTATING_OPERATIONS), None)
            if operation == "doctor.report":
                operation_args = {"graphics": False}
            if operation is None:
                print(management_presentation.format_report(
                    {"ok": False, "error": {"code": "live_status_unavailable"}}))
                return 3
        result = call(operation, operation_args) if operation_args else call(operation)
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "cron-preview" and len(argv) in {3, 5, 7, 8}:
        kind = argv[1]
        if kind == "create" and len(argv) in {5, 7, 8}:
            if len(argv) == 5:
                name, action_id, expression = argv[2:]
                schedule_type, value, extra, timezone_name = "cron", expression, "", ""
            else:
                name, action_id, schedule_type, value, extra = argv[2:7]
                timezone_name = argv[7] if len(argv) == 8 else ""
            schedule: dict[str, object]
            if schedule_type == "cron" and not extra:
                schedule = {"expression": value}
                if timezone_name: schedule["timezone"] = timezone_name
            elif schedule_type == "interval" and extra and not timezone_name:
                if not value.isdigit():
                    print(json.dumps({"ok": False, "error": {"code": "invalid_interval"}}))
                    return 2
                schedule = {"interval_seconds": int(value), "anchor_at": extra}
            elif schedule_type == "calendar" and extra == "daily":
                schedule = {"mode": "daily", "time": value}
                if timezone_name: schedule["timezone"] = timezone_name
            elif schedule_type == "calendar" and extra == "specific" and not timezone_name:
                schedule = {"mode": "specific", "datetime": value}
            elif schedule_type == "one_time" and not timezone_name and not extra:
                schedule = {"at": value}
            else:
                print(json.dumps({"ok": False, "error": {"code": "invalid_schedule"}}))
                return 2
            args = {"action": "create", "name": name, "action_id": action_id,
                    "schedule_type": schedule_type, "schedule": schedule}
        elif kind == "update" and len(argv) == 5:
            job_id, field, value = argv[2:]
            if field not in {"name", "enabled"}:
                print(json.dumps({"ok": False, "error": {"code": "invalid_update_field"}}))
                return 2
            change = {"name": value} if field == "name" else {"enabled": value.lower() == "true"}
            if field == "enabled" and value.lower() not in {"true", "false"}:
                print(json.dumps({"ok": False, "error": {"code": "invalid_enabled_value"}}))
                return 2
            args = {"action": "update", "job_id": job_id, "changes": change}
        elif kind == "remove" and len(argv) == 3:
            args = {"action": "remove", "job_id": argv[2]}
        else:
            print(json.dumps({"ok": False, "error": {"code": "invalid_arguments"}}))
            return 2
        preview = call("cron.jobs.mutation.preview", args)
        if not preview.get("ok"):
            print(management_presentation.format_report(preview))
            return 1
        plan = preview.get("data", {}).get("plan", {})
        if not isinstance(plan.get("plan_id"), str):
            print(json.dumps({"ok": False, "error": {"code": "invalid_preview"}}))
            return 1
        print("P\t" + plan["plan_id"] + "\t" + clean(json.dumps(plan, ensure_ascii=False, sort_keys=True)))
        return 0
    if action == "cron-apply" and len(argv) == 2:
        plan_id = argv[1]
        if not re.fullmatch(r"[0-9a-f]{32}", plan_id):
            print(json.dumps({"ok": False, "error": {"code": "invalid_plan_id"}}))
            return 2
        result = call("cron.jobs.mutation.apply", {"plan_id": plan_id, "confirmed": True})
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "cron-scheduler" and len(argv) in {2, 3}:
        choice = argv[1]
        if choice == "status" and len(argv) == 2:
            result = call("cron.status")
        elif choice == "start" and len(argv) == 3 and argv[2].isdigit() and 1 <= int(argv[2]) <= 60:
            result = call("cron.scheduler.start", {"poll_seconds": int(argv[2]), "confirmed": True})
        elif choice == "stop" and len(argv) == 2:
            result = call("cron.scheduler.stop", {"confirmed": True})
        else:
            print(json.dumps({"ok": False, "error": {"code": "invalid_arguments"}}))
            return 2
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "cron-jobs" and len(argv) == 1:
        result = call("cron.jobs.list")
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "cron-inspect" and len(argv) == 3:
        kind, item_id = argv[1:]
        if kind == "job" and re.fullmatch(r"job-[0-9a-f]{32}", item_id):
            operation, args = "cron.jobs.show", {"job_id": item_id}
        elif kind == "next" and re.fullmatch(r"job-[0-9a-f]{32}", item_id):
            operation, args = "cron.jobs.next_runs", {"job_id": item_id, "count": 5}
        elif kind == "execution" and re.fullmatch(r"exec-[0-9a-f]{32}", item_id):
            operation, args = "cron.executions.show", {"execution_id": item_id}
        else:
            print(json.dumps({"ok": False, "error": {"code": "invalid_cron_reference"}}))
            return 2
        result = call(operation, args)
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action.startswith(("proot-", "guest-lifecycle-", "shortcut-", "terminal-session-")):
        print(json.dumps({"ok": False, "error": {"code": "feature_removed",
            "message": "PRoot guest management has been retired; use Native Termux controls."}}))
        return 2
    if action == "timezone-set" and len(argv) == 2:
        result = call("timezone.set", {"timezone": argv[1]})
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "cron-history" and len(argv) == 1:
        result = call("cron.executions.list", {"limit": 20})
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "logs-read" and len(argv) == 2:
        source_id = argv[1]
        if source_id not in {"native-desktop", "cron-scheduler", "management-api"}:
            print(json.dumps({"ok": False, "error": {"code": "invalid_log_source"}}))
            return 2
        result = call("management.logs.read", {"source_id": source_id, "limit": 100})
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "history" and len(argv) == 1:
        result = call("recovery.status")
        print(management_presentation.format_activity_history(result))
        return 0 if result.get("ok") else 1
    if action in {"ssh-preview-start", "ssh-preview-stop", "ssh-preview-restart"} and len(argv) == 1:
        operation = "ssh.service." + action.removeprefix("ssh-preview-")
        result = call(operation, {"confirmed": False, "plan_id": None})
        if not result.get("ok"):
            print(management_presentation.format_report(result))
            return 1
        data = result.get("data", {})
        fields = ("P", clean(data.get("plan_id")) or "-",
                  str(bool(data.get("requires_confirmation"))).lower(),
                  clean(data.get("impact")))
        print("\t".join(fields))
        return 0
    if action in {"ssh-apply-start", "ssh-apply-stop", "ssh-apply-restart"} and len(argv) == 3 and argv[1] == "confirmed":
        plan_id = argv[2]
        if not re.fullmatch(r"[0-9a-f]{64}", plan_id):
            print(json.dumps({"ok": False, "error": {"code": "invalid_plan_id"}}))
            return 2
        operation = "ssh.service." + action.removeprefix("ssh-apply-")
        result = call(operation, {"confirmed": True, "plan_id": plan_id})
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action in {"start-desktop", "stop-desktop"} and len(argv) == 2 and argv[1] == "confirmed":
        result = call("desktop.start" if action == "start-desktop" else "desktop.stop")
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "monitor" and len(argv) == 1:
        result = call("desktop.monitor.status")
        if not result.get("ok"):
            print(management_presentation.format_report(result))
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
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    print("Unsupported typed management action.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
