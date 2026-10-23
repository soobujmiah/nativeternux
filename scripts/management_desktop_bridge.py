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
        if rid in {"graphics.native", "graphics.debian"}:
            operation = "graphics.provider.status"
            operation_args = {"provider": "native" if rid.endswith("native") else "debian"}
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
    if action == "cron-preview" and len(argv) in {3, 5}:
        import cron_registry
        import timezone_support
        kind = argv[1]
        if kind == "create" and len(argv) == 5:
            name, action_id, expression = argv[2:]
            if action_id not in cron_registry._ALLOWED_ACTIONS:
                print(json.dumps({"ok": False, "error": {"code": "invalid_action"}}))
                return 2
            state = os.environ.get("TERNUXX_STATE_DIR") or str(Path.home() / ".local/share/ternuxx")
            zone = timezone_support.current_timezone(state, installation_timezone=os.environ.get("TERNUXX_INSTALL_TIMEZONE"))
            job = cron_registry.new_job(name=name, description="Scheduled Ternuxx action",
                action_id=action_id, schedule_type="cron", schedule={"expression": expression, "timezone": zone})
            args = {"action": "create", "job": job}
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
    if action == "cron-jobs" and len(argv) == 1:
        result = call("cron.jobs.list")
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "guest-lifecycle-preview" and len(argv) == 4:
        kind, alias, backup_id = argv[1:]
        if kind in {"retire", "restore"} and not re.fullmatch(r"ternuxx-replay-[a-z0-9][a-z0-9-]{0,31}", alias):
            print(json.dumps({"ok": False, "error": {"code": "invalid_replay_alias"}})); return 2
        if kind in {"migrate", "rollback"} and alias != "debian":
            print(json.dumps({"ok": False, "error": {"code": "invalid_debian_alias"}})); return 2
        if kind == "retire" and backup_id == "-":
            result = call("proot.setup.retire.preview", {"alias": alias})
        elif kind == "restore" and re.fullmatch(r"[0-9a-f]{32}", backup_id):
            result = call("proot.setup.restore.preview", {"alias": alias, "backup_id": backup_id})
        elif kind == "migrate" and backup_id == "-":
            result = call("proot.setup.icd-migrate.preview", {"alias": alias})
        elif kind == "rollback" and re.fullmatch(r"[0-9a-f]{64}", backup_id):
            result = call("proot.setup.icd-migrate.rollback.preview", {"migration_id": backup_id})
        else:
            print(json.dumps({"ok": False, "error": {"code": "invalid_guest_lifecycle_target"}}))
            return 2
        if not result.get("ok"):
            print(management_presentation.format_report(result)); return 1
        data = result.get("data", {})
        plan_id = data.get("plan_id") if isinstance(data, dict) else None
        impact = data.get("operation", {}).get("impact", "") if isinstance(data, dict) else ""
        if not isinstance(plan_id, str) or not re.fullmatch(r"[0-9a-f]{64}", plan_id):
            print(json.dumps({"ok": False, "error": {"code": "invalid_guest_lifecycle_preview"}})); return 1
        print("\t".join(("G", kind, plan_id, alias, backup_id, clean(impact))))
        return 0
    if action == "guest-lifecycle-apply" and len(argv) == 5:
        kind, alias, backup_id, plan_id = argv[1:]
        replay = kind in {"retire", "restore"} and re.fullmatch(r"ternuxx-replay-[a-z0-9][a-z0-9-]{0,31}", alias)
        debian = kind in {"migrate", "rollback"} and alias == "debian"
        if (not (replay or debian) or not re.fullmatch(r"[0-9a-f]{64}", plan_id)
                or (kind in {"retire", "migrate"} and backup_id != "-")
                or (kind == "restore" and not re.fullmatch(r"[0-9a-f]{32}", backup_id))
                or (kind == "rollback" and not re.fullmatch(r"[0-9a-f]{64}", backup_id))):
            print(json.dumps({"ok": False, "error": {"code": "invalid_guest_lifecycle_target"}})); return 2
        if kind == "retire":
            result = call("proot.setup.retire.apply", {"alias": alias, "confirmed": True, "plan_id": plan_id})
        elif kind == "restore":
            result = call("proot.setup.restore.apply", {"alias": alias, "backup_id": backup_id,
                                                         "confirmed": True, "plan_id": plan_id})
        elif kind == "migrate":
            result = call("proot.setup.icd-migrate.apply", {"alias": alias, "confirmed": True, "plan_id": plan_id})
        else:
            result = call("proot.setup.icd-migrate.rollback.apply", {"migration_id": backup_id,
                "confirmed": True, "plan_id": plan_id})
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "shortcut-sync-rollback-list" and len(argv) == 1:
        result = call("proot.shortcuts.sync.rollback.list")
        if not result.get("ok"):
            print(management_presentation.format_report(result)); return 1
        rows = result.get("data", {}).get("rollbacks", [])
        emitted = False
        for item in rows:
            if (not isinstance(item, dict) or item.get("integrity") != "valid"
                    or item.get("status") != "applied"
                    or not re.fullmatch(r"[0-9a-f]{32}", str(item.get("rollback_id", "")))):
                continue
            print("R\t" + item["rollback_id"] + "\t" + clean(item.get("created_at"))
                  + "\t" + clean(item.get("entry_count")))
            emitted = True
        if not emitted: print("R\t-\t-\t-")
        return 0
    if action == "shortcut-sync-rollback-preview" and len(argv) == 2:
        rollback_id = argv[1]
        if not re.fullmatch(r"[0-9a-f]{32}", rollback_id):
            print("Invalid saved PRoot shortcut sync ID."); return 2
        result = call("proot.shortcuts.sync.rollback.preview", {"rollback_id": rollback_id})
        if not result.get("ok"):
            print(management_presentation.format_report(result)); return 1
        data = result.get("data", {}); plan_id = data.get("plan_id")
        changes = data.get("changes", [])
        summary = "; ".join(clean(item.get("action")) + " " + clean(item.get("path"))
                            for item in changes if isinstance(item, dict))
        if not isinstance(plan_id, str) or not re.fullmatch(r"[0-9a-f]{24}", plan_id):
            print("Could not verify the exact shortcut restore preview."); return 1
        print("P\t" + plan_id + "\t" + rollback_id + "\t" + clean(summary))
        return 0
    if action == "shortcut-sync-rollback-apply" and len(argv) == 3:
        rollback_id, plan_id = argv[1:]
        if not re.fullmatch(r"[0-9a-f]{32}", rollback_id) or not re.fullmatch(r"[0-9a-f]{24}", plan_id):
            print("The PRoot shortcut restore preview is invalid or expired."); return 2
        result = call("proot.shortcuts.sync.rollback.apply", {
            "rollback_id": rollback_id, "confirmed": True, "plan_id": plan_id})
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "shortcut-list" and len(argv) == 1:
        result = call("proot.shortcuts.list")
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "proot-session-list" and len(argv) == 1:
        result = call("proot.sessions.list")
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "terminal-session-options" and len(argv) == 1:
        result = call("proot.sessions.list")
        if not result.get("ok"):
            print(management_presentation.format_report(result))
            return 1
        sessions = result.get("data", {}).get("sessions", [])
        if not isinstance(sessions, list):
            print(json.dumps({"ok": False, "error": {"code": "invalid_session_inventory"}}))
            return 1
        for item in sessions:
            if not isinstance(item, dict):
                continue
            session_id = item.get("session_id")
            if (not isinstance(session_id, str)
                    or not re.fullmatch(r"proot-[0-9a-f]{32}", session_id)
                    or item.get("profile") != "debian-interactive"
                    or item.get("state") != "running"
                    or item.get("ownership") != "ternuxx_verified"):
                continue
            print("S\t" + session_id + "\tDebian " + session_id[-8:] + " · Running")
        return 0
    if action == "proot-session-recovery" and len(argv) == 2:
        if not re.fullmatch(r"proot-[0-9a-f]{32}", argv[1]):
            print(json.dumps({"ok": False, "error": {"code": "invalid_session_id"}}))
            return 2
        result = call("proot.recovery.inspect", {"session_id": argv[1]})
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "proot-probe-preview" and len(argv) == 1:
        result = call("proot.start.preview", {"profile": "isolated-probe"})
        if not result.get("ok"):
            print(management_presentation.format_report(result))
            return 1
        data = result.get("data", {})
        plan_id = data.get("plan_id") if isinstance(data, dict) else None
        impact = clean(data.get("impact")) if isinstance(data, dict) else ""
        if not isinstance(plan_id, str) or not re.fullmatch(r"plan-[0-9a-f]{64}", plan_id):
            print(json.dumps({"ok": False, "error": {"code": "invalid_session_preview"}}))
            return 1
        print("P\t" + plan_id + "\t" + impact)
        return 0
    if action == "proot-probe-apply" and len(argv) == 2:
        if not re.fullmatch(r"plan-[0-9a-f]{64}", argv[1]):
            print(json.dumps({"ok": False, "error": {"code": "invalid_plan_id"}}))
            return 2
        result = call("proot.start", {"profile": "isolated-probe", "confirmed": True,
                                      "plan_id": argv[1], "timeout_seconds": 300})
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "proot-session-stop-preview" and len(argv) == 2:
        session_id = argv[1]
        if not re.fullmatch(r"proot-[0-9a-f]{32}", session_id):
            print(json.dumps({"ok": False, "error": {"code": "invalid_session_id"}}))
            return 2
        result = call("proot.stop.preview", {"session_id": session_id})
        if not result.get("ok"):
            print(management_presentation.format_report(result))
            return 1
        data = result.get("data", {})
        allowed_contracts = {
            ("isolated-probe", "signal_owned_process_group", "SIGTERM", "verified_process_group"),
            ("debian-interactive", "hangup_owned_terminal_session", "SIGHUP",
             "verified_private_session_job_groups"),
        }
        contract = (data.get("profile"), data.get("action"), data.get("signal"),
                    data.get("scope")) if isinstance(data, dict) else None
        if (not isinstance(data, dict) or data.get("ownership") != "ternuxx_verified"
                or contract not in allowed_contracts
                or not isinstance(data.get("plan_id"), str)
                or not re.fullmatch(r"plan-[0-9a-f]{64}", data["plan_id"])):
            print(json.dumps({"ok": False, "error": {"code": "session_stop_not_verified"}}))
            return 1
        print("P\t" + data["plan_id"] + "\t" + clean(
            management_presentation.human_value(data["profile"])) + "\t" + clean(session_id)
            + "\t" + data["signal"] + "\t" + clean(
                management_presentation.human_value(data["scope"])) + "\t" + clean(data.get("impact")))
        return 0
    if action == "proot-session-stop-apply" and len(argv) == 3:
        session_id, plan_id = argv[1:]
        if (not re.fullmatch(r"proot-[0-9a-f]{32}", session_id)
                or not re.fullmatch(r"plan-[0-9a-f]{64}", plan_id)):
            print(json.dumps({"ok": False, "error": {"code": "invalid_session_plan"}}))
            return 2
        result = call("proot.stop", {"session_id": session_id, "confirmed": True, "plan_id": plan_id})
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action in {"proot-app-options", "proot-shortcut-options"} and len(argv) == 1:
        import proot_shortcuts
        result = call("proot.shortcuts.list")
        if not result.get("ok"):
            print(management_presentation.format_report(result)); return 1
        for app_id, item in proot_shortcuts.CATALOG.items():
            print("C\t" + clean(app_id) + "\t" + clean(item.get("name")))
        inventory = result.get("data", {}).get("desktop_applications", {})
        for item in inventory.get("items", []) if isinstance(inventory, dict) else []:
            desktop_id, name = item.get("desktop_id"), item.get("name")
            if (item.get("status") == "available" and isinstance(desktop_id, str)
                    and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,254}", desktop_id)
                    and isinstance(name, str) and name.strip()):
                print("D\t" + desktop_id + "\t" + clean(name))
        return 0
    if action == "proot-app-launch" and len(argv) == 2:
        import proot_shortcuts
        if argv[1].startswith("desktop:"):
            desktop_id = argv[1][8:]
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,254}", desktop_id):
                print(json.dumps({"ok": False, "error": {"code": "invalid_desktop_app"}}))
                return 2
            result = call("proot.app.launch", {"desktop_id": desktop_id})
        else:
            if argv[1] not in proot_shortcuts.CATALOG:
                print(json.dumps({"ok": False, "error": {"code": "unknown_proot_app"}}))
                return 2
            result = call("proot.app.launch", {"app_id": argv[1]})
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
    if action == "shortcut-preview" and len(argv) == 3:
        import proot_shortcuts
        shortcut_action, selected = argv[1:]
        if shortcut_action not in {"add", "remove"}:
            print(json.dumps({"ok": False, "error": {"code": "invalid_shortcut_target"}}))
            return 2
        if selected.startswith("desktop:"):
            desktop_id = selected[8:]
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,254}", desktop_id):
                print(json.dumps({"ok": False, "error": {"code": "invalid_shortcut_target"}}))
                return 2
            shortcut_args = {"action": shortcut_action, "desktop_id": desktop_id}
        elif selected in proot_shortcuts.CATALOG:
            shortcut_args = {"action": shortcut_action, "app_id": selected}
        else:
            print(json.dumps({"ok": False, "error": {"code": "invalid_shortcut_target"}}))
            return 2
        result = call("proot.shortcuts.preview", shortcut_args)
        if not result.get("ok"):
            print(management_presentation.format_report(result))
            return 1
        data = result.get("data", {})
        changed = str(bool(data.get("changed"))).lower()
        affected = data.get("affected_resources") or []
        target = clean(affected[0].get("path")) if affected and isinstance(affected[0], dict) else "-"
        before = clean(affected[0].get("before")) if affected and isinstance(affected[0], dict) else "-"
        after = clean(affected[0].get("after")) if affected and isinstance(affected[0], dict) else "-"
        print("\t".join(("P", clean(data.get("plan_id")) or "-", changed, target, before + " -> " + after)))
        return 0
    if action == "shortcut-apply" and len(argv) == 4:
        import proot_shortcuts
        shortcut_action, selected, plan_id = argv[1:]
        if shortcut_action not in {"add", "remove"} or not re.fullmatch(r"[0-9a-f]{24}", plan_id):
            print(json.dumps({"ok": False, "error": {"code": "invalid_shortcut_target"}}))
            return 2
        if selected.startswith("desktop:"):
            desktop_id = selected[8:]
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,254}", desktop_id):
                print(json.dumps({"ok": False, "error": {"code": "invalid_shortcut_target"}}))
                return 2
            target_args = {"desktop_id": desktop_id}
        elif selected in proot_shortcuts.CATALOG:
            target_args = {"app_id": selected}
        else:
            print(json.dumps({"ok": False, "error": {"code": "invalid_shortcut_target"}}))
            return 2
        result = call("proot.shortcuts.apply", {
            "action": shortcut_action, **target_args, "confirmed": True, "plan_id": plan_id,
        })
        print(management_presentation.format_report(result))
        return 0 if result.get("ok") else 1
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
