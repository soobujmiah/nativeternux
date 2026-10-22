#!/usr/bin/env python3
"""Versioned, local application-service boundary for Ternuxx CLI and TUI operations.

This is an in-process/local CLI backend, not an HTTP server. It deliberately
accepts a narrow operation allowlist and has no generic shell or file API.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

import boot_profiles
import boot_helpers
import termux_boot_cron
import continuity
import config_recovery
import operation_journal
import reboot_recovery
import runtime_diagnostics
import ssh_diagnostics
import ssh_key_inventory
import runit_service
import runit_deployment
import operation_recovery
import wakelock_manager
import proot_diagnostics
import remote_access_policy
import proot_shortcuts
import doctor_report
import management_catalog
import management_log_reader
import graphics_manager
import gui_monitoring
import hermes_adapter
import cron_registry
import cron_execution
import cron_scheduler
import cron_daemon
import proot_sessions
import terminal_broker
import timezone_support


API_VERSION = 1
OPERATIONS = {
    "management.catalog": {"args": {"category", "query", "status"}},
    "management.logs.list": {"args": set()},
    "management.logs.read": {"args": {"source_id", "limit"}},
    "graphics.provider.status": {"args": {"provider"}},
    "graphics.provider.verify": {"args": {"provider", "api", "display"}},
    "graphics.provider.select": {"args": {"provider", "backend", "confirmed"}},
    "agent.hermes.status": {"args": set()},
    "cron.status": {"args": set()},
    "cron.scheduler.start": {"args": {"poll_seconds", "confirmed"}},
    "cron.scheduler.stop": {"args": {"confirmed"}},
    "cron.executor.self_test": {"args": set()},
    "cron.jobs.list": {"args": set()},
    "cron.jobs.show": {"args": {"job_id"}},
    "cron.jobs.validate": {"args": {"job", "job_id"}},
    "cron.jobs.next_runs": {"args": {"job_id", "count"}},
    "cron.jobs.mutation.preview": {"args": {"action", "job", "job_id", "changes"}},
    "cron.jobs.mutation.apply": {"args": {"plan_id", "confirmed"}},
    "cron.executions.list": {"args": {"job_id", "limit"}},
    "cron.executions.show": {"args": {"execution_id"}},
    "timezone.status": {"args": set()},
    "timezone.list": {"args": set()},
    "timezone.set": {"args": {"timezone"}},
    "desktop.status": {"args": set()},
    "desktop.monitor.status": {"args": set()},
    "desktop.monitor.configure": {"args": {"enabled", "interval_value", "unit", "activity_launch", "focus_check"}},
    "desktop.start": {"args": {"display"}},
    "desktop.stop": {"args": set()},
    "desktop.restart": {"args": {"display"}},
    "doctor.report": {"args": {"graphics"}},
    "ssh.inspect": {"args": set()},
    "ssh.keys.list": {"args": set()},
    "proot.status": {"args": set()},
    "proot.profiles.list": {"args": set()},
    "proot.profiles.show": {"args": {"profile"}},
    "proot.sessions.list": {"args": set()},
    "proot.sessions.show": {"args": {"session_id"}},
    "proot.sessions.health": {"args": {"session_id"}},
    "proot.recovery.inspect": {"args": {"session_id"}},
    "proot.recovery.reconcile.preview": {"args": {"session_id"}},
    "proot.recovery.reconcile": {"args": {"session_id", "confirmed", "plan_id"}},
    "proot.start.preview": {"args": {"profile"}},
    "proot.start": {"args": {"profile", "confirmed", "plan_id", "timeout_seconds"}},
    "proot.stop.preview": {"args": {"session_id"}},
    "proot.stop": {"args": {"session_id", "confirmed", "plan_id"}},
    "proot.app.launch": {"args": {"app_id", "desktop_id", "display"}},
    "proot.shortcuts.sync": {"args": set()},
    "proot.shortcuts.list": {"args": set()},
    "proot.shortcuts.preview": {"args": {"action", "app_id"}},
    "proot.shortcuts.apply": {"args": {"action", "app_id", "confirmed", "plan_id"}},
    "proot.guest.verify": {"args": {"distro", "user", "user_source", "display", "backend"}},
    "terminal.broker.status": {"args": set()},
    "terminal.start.preview": {"args": set()},
    "terminal.start": {"args": {"confirmed", "plan_id"}},
    "terminal.attach": {"args": {"session_id"}},
    "terminal.input": {"args": {"session_id", "generation", "attachment_id", "data_base64"}},
    "terminal.resize": {"args": {"session_id", "generation", "attachment_id", "columns", "rows"}},
    "terminal.output": {"args": {"session_id", "generation", "attachment_id", "after_sequence"}},
    "terminal.detach": {"args": {"session_id", "generation", "attachment_id"}},
    "terminal.close.preview": {"args": {"session_id", "generation", "attachment_id"}},
    "terminal.close": {"args": {"session_id", "generation", "attachment_id", "confirmed", "plan_id"}},
    "remote.access.preview": {"args": {"policy"}},
    "ssh.service.start": {"args": {"confirmed", "plan_id"}},
    "ssh.service.stop": {"args": {"confirmed", "plan_id"}},
    "ssh.service.restart": {"args": {"confirmed", "plan_id"}},
    "ssh.service.deploy": {"args": {"confirmed", "plan_id"}},
    "ssh.service.deploy.rollback.preview": {"args": {"operation_id"}},
    "ssh.service.deploy.rollback.apply": {"args": {"operation_id", "confirmed", "plan_id"}},
    "native.ssh.status": {"args": set()},
    "boot.status": {"args": set()},
    "boot.profile.status": {"args": set()},
    "boot.profile.preview": {"args": {"profile"}},
    "boot.helpers.status": {"args": set()},
    "boot.helpers.preview": {"args": {"helper_id", "action", "snapshot_id"}},
    "boot.helpers.apply": {"args": {"helper_id", "action", "snapshot_id", "confirmed", "plan_id"}},
    "boot.enable": {"args": {"profile", "confirmed"}},
    "boot.disable": {"args": {"confirmed"}},
    "boot.cron.status": {"args": set()},
    "boot.cron.validate": {"args": set()},
    "boot.cron.preview": {"args": {"action"}},
    "boot.cron.enable": {"args": {"confirmed", "plan_id"}},
    "boot.cron.disable": {"args": {"confirmed", "plan_id"}},
    "backup.create": {"args": {"name", "confirmed", "plan_id"}},
    "backup.list": {"args": set()},
    "backup.inspect": {"args": {"backup_id"}},
    "restore.preview": {"args": {"backup_id"}},
    "restore.apply": {"args": {"backup_id", "confirmed", "plan_id"}},
    "recovery.status": {"args": set()},
    "recovery.resolve": {"args": {"operation_id", "confirmed", "plan_id"}},
    "recovery.inspect": {"args": {"operation_id"}},
    "recovery.rollback.preview": {"args": {"operation_id"}},
    "recovery.rollback.apply": {"args": {"operation_id", "confirmed", "plan_id"}},
    "wakelock.status": {"args": set()},
    "wakelock.acquire": {"args": {"owner", "persistent"}},
    "wakelock.release": {"args": {"owner", "persistent"}},
    "continuity.status": {"args": {"test_id"}},
    "continuity.prepare": {
        "args": {"test_id", "repository", "commit", "worktree_state", "task_state", "pending_tests", "next_safe_action"},
    },
    "continuity.verify": {"args": {"checkpoint_id"}},
    "continuity.prepare-reboot-test": {"args": {"test_id", "baseline", "boot_id"}},
    "continuity.verify-reboot-test": {"args": {"test_id", "current_boot_id"}},
    "continuity.resume-info": {"args": {"test_id"}},
}


def dispatch(request: object, *, caller: str = "local_cli", env: dict[str, str] | None = None) -> dict[str, object]:
    request_id = uuid.uuid4().hex
    if not isinstance(request, dict):
        return _error(request_id, "invalid_request", "request must be an object")
    request_id = str(request.get("request_id") or request_id)
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", request_id):
        return _error("invalid-request", "invalid_request_id", "request ID is malformed")
    if set(request) != {"api_version", "request_id", "operation", "args"}:
        return _error(request_id, "invalid_request", "request fields do not match management API v1")
    if type(request.get("api_version")) is not int or request.get("api_version") != API_VERSION:
        return _error(request_id, "unsupported_api_version", "supported management API version is 1")
    operation = request.get("operation")
    if not isinstance(operation, str) or operation not in OPERATIONS:
        return _error(request_id, "operation_not_supported", "requested operation is not available")
    spec = OPERATIONS[operation]
    args = request.get("args")
    if not isinstance(args, dict) or set(args) - spec["args"]:
        return _error(request_id, "invalid_arguments", "operation arguments are invalid")
    if caller != "local_cli":
        return _error(request_id, "unauthorized", "this local backend accepts only its trusted CLI adapter")
    if operation == "cron.scheduler.start" and (
            set(args) - {"poll_seconds", "confirmed"} or type(args.get("poll_seconds", 5)) is not int
            or not 1 <= args.get("poll_seconds", 5) <= 60):
        return _error(request_id, "invalid_arguments", "scheduler poll interval must be 1..60 seconds")
    if operation == "cron.scheduler.start" and args.get("confirmed") is not True:
        return _error(request_id, "confirmation_required", "scheduler start requires explicit confirmation")
    if operation == "cron.scheduler.stop" and (set(args) != {"confirmed"} or args.get("confirmed") is not True):
        return _error(request_id, "confirmation_required", "scheduler stop requires explicit confirmation")
    if operation in {"proot.sessions.show", "proot.sessions.health"} and (set(args) != {"session_id"} or not isinstance(args.get("session_id"), str)):
        return _error(request_id, "invalid_arguments", "a Ternuxx session ID is required")
    if operation in {"proot.recovery.inspect", "proot.recovery.reconcile.preview"} and (
            set(args) != {"session_id"} or not isinstance(args.get("session_id"), str)):
        return _error(request_id, "invalid_arguments", "a Ternuxx session ID is required")
    if operation == "proot.recovery.reconcile" and (
            set(args) != {"session_id", "confirmed", "plan_id"}
            or not isinstance(args.get("session_id"), str) or args.get("confirmed") is not True
            or not isinstance(args.get("plan_id"), str)):
        return _error(request_id, "confirmation_required", "reconciliation requires an exact preview plan and confirmation")
    if operation in {"proot.profiles.show", "proot.start.preview"} and (
            set(args) != {"profile"} or not isinstance(args.get("profile"), str)):
        return _error(request_id, "invalid_arguments", "a supported PRoot profile is required")
    if operation == "proot.start" and (
            set(args) != {"profile", "confirmed", "plan_id", "timeout_seconds"}
            or not isinstance(args.get("profile"), str) or args.get("confirmed") is not True
            or not isinstance(args.get("plan_id"), str) or type(args.get("timeout_seconds")) is not int
            or not 30 <= args["timeout_seconds"] <= 1800):
        return _error(request_id, "confirmation_required", "PRoot start requires a profile, exact preview plan, confirmation, and bounded timeout")
    if operation == "proot.stop.preview" and (
            set(args) != {"session_id"} or not isinstance(args.get("session_id"), str)):
        return _error(request_id, "invalid_arguments", "a Ternuxx session ID is required")
    if operation == "proot.stop" and (
            set(args) != {"session_id", "confirmed", "plan_id"}
            or not isinstance(args.get("session_id"), str) or args.get("confirmed") is not True
            or not isinstance(args.get("plan_id"), str)):
        return _error(request_id, "confirmation_required", "PRoot stop requires an exact preview plan and confirmation")
    if operation == "timezone.set" and (set(args) != {"timezone"} or not isinstance(args.get("timezone"), str)):
        return _error(request_id, "invalid_arguments", "timezone.set requires one IANA timezone name")
    if operation == "cron.jobs.validate":
        if (set(args) not in ({"job"}, {"job_id"})
                or ("job" in args and not isinstance(args["job"], dict))
                or ("job_id" in args and not isinstance(args["job_id"], str))):
            return _error(request_id, "invalid_arguments", "validation requires one typed job or job ID")
    if operation == "cron.jobs.show" and (set(args) != {"job_id"} or not isinstance(args.get("job_id"), str)):
        return _error(request_id, "invalid_arguments", "a job ID is required")
    if operation == "cron.jobs.next_runs" and (set(args) - {"job_id", "count"} or not isinstance(args.get("job_id"), str) or type(args.get("count", 5)) is not int):
        return _error(request_id, "invalid_arguments", "job ID and bounded run count are required")
    if operation == "cron.jobs.mutation.preview":
        action = args.get("action")
        valid = (
            (action == "create" and set(args) == {"action", "job"} and isinstance(args.get("job"), dict))
            or (action == "update" and set(args) == {"action", "job_id", "changes"}
                and isinstance(args.get("job_id"), str) and isinstance(args.get("changes"), dict))
            or (action == "remove" and set(args) == {"action", "job_id"}
                and isinstance(args.get("job_id"), str))
        )
        if not valid:
            return _error(request_id, "invalid_arguments", "Cron preview requires a typed create, update, or remove request")
    if operation == "cron.jobs.mutation.apply" and (
            set(args) != {"plan_id", "confirmed"} or not isinstance(args.get("plan_id"), str)
            or args.get("confirmed") is not True):
        return _error(request_id, "confirmation_required", "Cron apply requires an exact plan ID and explicit confirmation")
    process_env = os.environ if env is None else env
    if process_env.get("TERMUX_VERSION") is None or process_env.get("PREFIX") != "/data/data/com.termux/files/usr":
        return _error(request_id, "native_termux_required", "operation requires the native Termux shell")
    home = process_env.get("HOME", "")
    state_dir = process_env.get("TERNUXX_STATE_DIR", "")
    if not home or ((operation.startswith(("continuity.", "wakelock.", "boot.profile.", "boot.helpers.", "backup.", "restore.", "recovery.rollback.", "recovery.service.", "recovery.resolve", "ssh.service.")) or operation == "desktop.monitor.configure") and not state_dir):
        return _error(request_id, "configuration_missing", "HOME and the native state directory must be configured")

    try:
        if operation == "agent.hermes.status":
            data = hermes_adapter.inspect(prefix=process_env["PREFIX"], home=home)
        elif operation == "timezone.status":
            data = timezone_support.status(state_dir or os.path.join(home, ".local/share/ternuxx"),
                                          prefix=process_env["PREFIX"])
        elif operation == "timezone.list":
            data = {"timezones": timezone_support.available_timezones(prefix=process_env["PREFIX"]),
                    "database": timezone_support.database_status(prefix=process_env["PREFIX"])}
        elif operation == "timezone.set":
            data = timezone_support.set_timezone(
                state_dir or os.path.join(home, ".local/share/ternuxx"), args["timezone"],
                prefix=process_env["PREFIX"])
        elif operation == "cron.status":
            cron_state = state_dir or os.path.join(home, ".local/share/ternuxx")
            data = cron_registry.status(cron_state)
            runtime = cron_scheduler.status(cron_state)
            data["scheduler"] = runtime["status"]
            data["process"] = "running" if runtime.get("process_alive") else "not_running"
            data["execution"] = ("dispatch_healthy" if runtime.get("dispatch_healthy") else
                                 "scheduler_stopped" if runtime["status"] == "stopped" else "dispatch_unqualified")
            data["scheduler_runtime"] = runtime
            data["execution_ledger"] = cron_execution.status(cron_state)
        elif operation == "cron.scheduler.start":
            data = cron_daemon.start(state_dir or os.path.join(home, ".local/share/ternuxx"),
                                     poll_seconds=args.get("poll_seconds", 5))
        elif operation == "cron.scheduler.stop":
            data = cron_daemon.stop(state_dir or os.path.join(home, ".local/share/ternuxx"),
                                    confirmed=args["confirmed"])
        elif operation == "cron.executor.self_test":
            data = {"status": "ok", "action": "scheduler.self_test",
                    "side_effects": False, "execution": "diagnostic-only"}
        elif operation == "cron.executions.list":
            if set(args) - {"job_id", "limit"} or ("job_id" in args and not isinstance(args["job_id"], str)) or type(args.get("limit", 100)) is not int:
                return _error(request_id, "invalid_arguments", "execution history query is invalid")
            data = {"executions": cron_execution.list_executions(
                state_dir or os.path.join(home, ".local/share/ternuxx"), job_id=args.get("job_id"), limit=args.get("limit", 100))}
        elif operation == "cron.executions.show":
            if set(args) != {"execution_id"} or not isinstance(args.get("execution_id"), str):
                return _error(request_id, "invalid_arguments", "execution ID is required")
            data = {"execution": cron_execution.show_execution(
                state_dir or os.path.join(home, ".local/share/ternuxx"), args["execution_id"])}
        elif operation == "cron.jobs.list":
            data = {"jobs": cron_registry.list_jobs(state_dir or os.path.join(home, ".local/share/ternuxx"))}
        elif operation == "cron.jobs.show":
            data = {"job": cron_registry.show_job(state_dir or os.path.join(home, ".local/share/ternuxx"), args["job_id"])}
        elif operation == "cron.jobs.validate":
            job = args.get("job")
            if job is None and isinstance(args.get("job_id"), str):
                job = cron_registry.show_job(state_dir or os.path.join(home, ".local/share/ternuxx"), args["job_id"])
            data = {"valid": True, "job": cron_registry.validate_job(job)}
        elif operation == "cron.jobs.next_runs":
            count = args.get("count", 5)
            job = cron_registry.show_job(state_dir or os.path.join(home, ".local/share/ternuxx"), args["job_id"])
            data = {"job_id": args["job_id"], "runs": cron_registry.next_runs(job, count=count)}
        elif operation == "cron.jobs.mutation.preview":
            plan_args = {key: args[key] for key in ("job_id", "job", "changes") if key in args}
            data = cron_registry.preview_job_mutation(
                state_dir or os.path.join(home, ".local/share/ternuxx"),
                action=args["action"], **plan_args)
        elif operation == "cron.jobs.mutation.apply":
            data = cron_registry.apply_job_mutation(
                state_dir or os.path.join(home, ".local/share/ternuxx"),
                plan_id=args["plan_id"], confirmed=args["confirmed"])
        elif operation == "graphics.provider.status":
            provider = args.get("provider")
            if provider not in {"native", "debian"}:
                return _error(request_id, "invalid_arguments", "provider must be native or debian")
            data = graphics_manager.status(provider, home=home, state_dir=state_dir or os.path.join(home, ".local/share/ternuxx"), process_env=process_env, prefix=process_env["PREFIX"])
        elif operation == "graphics.provider.select":
            if args.get("provider") != "native" or args.get("backend") not in {"kgsl-freedreno", "system"} or args.get("confirmed") is not True:
                return _error(request_id, "confirmation_required", "Native graphics selection requires a supported backend and explicit confirmation")
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data = graphics_manager.configure_native(args["backend"], home=home,
                state_dir=state_dir or os.path.join(home, ".local/share/ternuxx"), repo_root=repo_root)
        elif operation == "graphics.provider.verify":
            provider, api = args.get("provider"), args.get("api")
            display = args.get("display", ":1")
            if provider not in {"native", "debian"} or api not in {"opengl", "gles", "vulkan"} or not isinstance(display, str) or not re.fullmatch(r":[0-9]{1,2}", display):
                return _error(request_id, "invalid_arguments", "provider, graphics API, or display is invalid")
            if provider == "debian":
                process_env = dict(process_env)
                process_env["TERNUXX_GRAPHICS_DISPLAY"] = display
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data = graphics_manager.verify(provider, api, home=home, state_dir=state_dir or os.path.join(home, ".local/share/ternuxx"), process_env=process_env, prefix=process_env["PREFIX"], repo_root=repo_root)
        elif operation == "management.catalog":
            data = management_catalog.build_catalog(
                set(OPERATIONS), category=args.get("category"),
                query=args.get("query"), status=args.get("status"))
        elif operation == "management.logs.list":
            data = management_log_reader.list_logs(
                state_dir or os.path.join(home, ".local/share/ternuxx"), home=home)
        elif operation == "management.logs.read":
            source_id, limit = args.get("source_id"), args.get("limit", 100)
            if not isinstance(source_id, str) or type(limit) is not int:
                return _error(request_id, "invalid_arguments", "a supported source ID and integer line limit are required")
            data = management_log_reader.read_log(
                state_dir or os.path.join(home, ".local/share/ternuxx"),
                home=home, source_id=source_id, limit=limit)
        elif operation in {"desktop.status", "desktop.start", "desktop.stop", "desktop.restart"}:
            action = operation.removeprefix("desktop.")
            display = args.get("display")
            if display is not None and (not isinstance(display, str)
                                        or not re.fullmatch(r":?[0-9]{1,2}", display)):
                return _error(request_id, "invalid_arguments", "desktop display must be a numeric X11 display")
            command = [process_env["PREFIX"] + "/bin/bash",
                       os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin", "tx"),
                       "--json", action]
            if action in {"start", "restart"} and display is not None:
                command.extend(("--display", display.lstrip(":")))
            completed = subprocess.run(command, env=dict(process_env), capture_output=True,
                                       text=True, timeout=180, check=False)
            if completed.returncode != 0:
                return _error(request_id, "desktop_operation_failed", "desktop action did not complete")
            try:
                data = json.loads(completed.stdout)
            except json.JSONDecodeError:
                return _error(request_id, "desktop_operation_failed", "desktop command returned no structured result")
        elif operation == "desktop.monitor.status":
            data = gui_monitoring.status(state_dir or os.path.join(home, ".local/share/ternuxx"),
                                        home=home, tmp_root=process_env.get("TMPDIR"))
        elif operation == "desktop.monitor.configure":
            values = {}
            for key in ("enabled", "activity_launch", "focus_check"):
                if key in args:
                    if type(args[key]) is not bool:
                        return _error(request_id, "invalid_arguments", f"{key} must be boolean")
                    values[key] = args[key]
            interval_value = args.get("interval_value")
            unit = args.get("unit")
            if interval_value is not None and type(interval_value) is not int:
                return _error(request_id, "invalid_arguments", "interval_value must be an integer")
            if unit is not None and not isinstance(unit, str):
                return _error(request_id, "invalid_arguments", "unit must be a string")
            data = gui_monitoring.configure(state_dir or os.path.join(home, ".local/share/ternuxx"),
                                            interval_value=interval_value, unit=unit, **values)
            data["linux_gui_health"] = gui_monitoring._linux_gui_state(
                home, state_dir or os.path.join(home, ".local/share/ternuxx"),
                process_env.get("TMPDIR", "/data/data/com.termux/files/usr/tmp"))
        elif operation == "doctor.report":
            graphics = args.get("graphics", False)
            if type(graphics) is not bool:
                return _error(request_id, "invalid_arguments", "graphics must be boolean")
            data = doctor_report.build_report(graphics, __import__("pathlib").Path(state_dir or home))
        elif operation == "remote.access.preview":
            data = remote_access_policy.preview(args["policy"]) if "policy" in args else remote_access_policy.preview()
        elif operation == "ssh.keys.list":
            data = ssh_key_inventory.list_managed_authorized_keys(home=home)
        elif operation in {"ssh.inspect", "native.ssh.status"}:
            data = ssh_diagnostics.inspect_native(prefix=process_env["PREFIX"], home=home)
        elif operation == "proot.status":
            data = proot_diagnostics.inspect_installed()
            data["ternuxx_sessions"] = proot_sessions.list_sessions(
                state_dir or os.path.join(home, ".local/share/ternuxx"))
        elif operation == "terminal.broker.status":
            try:
                data = terminal_broker.UnixBrokerClient(
                    state_dir or os.path.join(home, ".local/share/ternuxx")
                ).request("broker.status")
                data.setdefault("component", "terminal_broker")
                data.setdefault("provider_optional", True)
            except terminal_broker.BrokerError:
                data = {"component": "terminal_broker", "status": "not_running",
                        "provider_optional": True, "pty_relay": "unavailable"}
        elif operation.startswith("terminal.") and operation not in {"terminal.broker.status", "terminal.channel.issue"}:
            try:
                fields = dict(args)
                session_id = fields.pop("session_id", None)
                generation = fields.pop("generation", None)
                attachment_id = fields.pop("attachment_id", None)
                data = terminal_broker.UnixBrokerClient(
                    state_dir or os.path.join(home, ".local/share/ternuxx")
                ).request(operation, session_id=session_id, generation=generation,
                          attachment_id=attachment_id, args=fields)
            except terminal_broker.BrokerError as exc:
                return _error(request_id, "terminal_operation_failed", str(exc))
        elif operation == "proot.profiles.list":
            data = proot_sessions.profile_inventory(prefix=process_env["PREFIX"])
        elif operation == "proot.profiles.show":
            data = proot_sessions.show_profile(args["profile"], prefix=process_env["PREFIX"])
        elif operation == "proot.sessions.list":
            data = {"sessions": proot_sessions.list_sessions(
                state_dir or os.path.join(home, ".local/share/ternuxx"))}
        elif operation == "proot.sessions.show":
            data = {"session": proot_sessions.show_session(
                state_dir or os.path.join(home, ".local/share/ternuxx"), args["session_id"])}
        elif operation == "proot.sessions.health":
            data = proot_sessions.session_health(
                state_dir or os.path.join(home, ".local/share/ternuxx"), args["session_id"])
        elif operation == "proot.recovery.inspect":
            data = proot_sessions.inspect_recovery(
                state_dir or os.path.join(home, ".local/share/ternuxx"), args["session_id"])
        elif operation == "proot.recovery.reconcile.preview":
            data = proot_sessions.preview_reconcile(
                state_dir or os.path.join(home, ".local/share/ternuxx"), args["session_id"])
        elif operation == "proot.recovery.reconcile":
            data = proot_sessions.reconcile_session(
                state_dir or os.path.join(home, ".local/share/ternuxx"), args["session_id"],
                confirmed=args["confirmed"], plan_id=args["plan_id"])
        elif operation == "proot.start.preview":
            data = proot_sessions.preview_start(args["profile"], prefix=process_env["PREFIX"])
        elif operation == "proot.start":
            data = proot_sessions.start_profile(
                state_dir or os.path.join(home, ".local/share/ternuxx"), prefix=process_env["PREFIX"],
                profile=args["profile"], confirmed=args["confirmed"], plan_id=args["plan_id"],
                timeout_seconds=args["timeout_seconds"])
        elif operation == "proot.stop.preview":
            data = proot_sessions.preview_stop(
                state_dir or os.path.join(home, ".local/share/ternuxx"), args["session_id"])
        elif operation == "proot.stop":
            data = proot_sessions.stop_session(
                state_dir or os.path.join(home, ".local/share/ternuxx"), args["session_id"],
                confirmed=args["confirmed"], plan_id=args["plan_id"])
        elif operation == "proot.app.launch":
            app_id = args.get("app_id")
            desktop_id = args.get("desktop_id")
            if (isinstance(app_id, str)) == (isinstance(desktop_id, str)):
                return _error(request_id, "invalid_arguments", "exactly one app ID or desktop ID is required")
            display = args.get("display")
            if display is not None and (not isinstance(display, str) or not re.fullmatch(r":[0-9]{1,2}", display)):
                return _error(request_id, "invalid_arguments", "display must be an X11 display such as :1")
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if isinstance(desktop_id, str):
                data = proot_shortcuts.launch_desktop_application(
                    desktop_id, prefix=process_env["PREFIX"], repo_root=repo_root,
                    env=process_env, display=display,
                )
            else:
                data = proot_shortcuts.launch(
                    app_id, prefix=process_env["PREFIX"], repo_root=repo_root,
                    env=process_env, display=display,
                )
        elif operation == "proot.shortcuts.sync":
            data = proot_shortcuts.sync_desktop_applications(
                home=home, prefix=process_env["PREFIX"],
                repo_root=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                xdg_data_home=process_env.get("XDG_DATA_HOME") or os.path.join(
                    state_dir or os.path.join(home, ".local/share/ternuxx"), "xfce/data"),
                xdg_config_home=process_env.get("XDG_CONFIG_HOME") or os.path.join(
                    state_dir or os.path.join(home, ".local/share/ternuxx"), "xfce/config"),
            )
        elif operation == "proot.shortcuts.list":
            data = proot_shortcuts.list_shortcuts(
                home=home, prefix=process_env["PREFIX"],
                xdg_data_home=process_env.get("XDG_DATA_HOME"),
                repo_root=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            )
        elif operation in {"proot.shortcuts.preview", "proot.shortcuts.apply"}:
            action = args.get("action")
            app_id = args.get("app_id")
            if not isinstance(action, str) or not isinstance(app_id, str):
                return _error(request_id, "invalid_arguments", "shortcut action and app ID are required")
            shortcut_args = {
                "action": action, "app_id": app_id, "home": home,
                "prefix": process_env["PREFIX"],
                "repo_root": os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "xdg_data_home": process_env.get("XDG_DATA_HOME"),
                "path": process_env.get("PATH", ""),
            }
            if operation == "proot.shortcuts.preview":
                data = proot_shortcuts.preview(**shortcut_args)
            else:
                confirmed = args.get("confirmed", False)
                plan_id = args.get("plan_id")
                if type(confirmed) is not bool or (plan_id is not None and not isinstance(plan_id, str)):
                    return _error(request_id, "invalid_arguments", "shortcut confirmation or plan ID is invalid")
                data = proot_shortcuts.apply(**shortcut_args, confirmed=confirmed, plan_id=plan_id)
        elif operation == "proot.guest.verify":
            source = args.get("user_source", "explicit")
            if (not isinstance(args.get("distro"), str)
                    or not isinstance(args.get("display"), str)
                    or not isinstance(args.get("backend"), str)
                    or not isinstance(source, str) or source not in {"explicit", "rootfs"}
                    or (source == "explicit" and not isinstance(args.get("user"), str))
                    or (source == "rootfs" and "user" in args)):
                return _error(request_id, "invalid_arguments", "PRoot guest verification requires a supported, unambiguous profile and display/backend selection")
            try:
                user = args.get("user")
                if source == "rootfs":
                    user = proot_diagnostics.resolve_proot_guest_user(
                        distro=args["distro"], prefix=process_env["PREFIX"],
                    )
                data = proot_diagnostics.verify_proot_guest(
                    distro=args["distro"], user=user, display=args["display"], backend=args["backend"],
                    prefix=process_env["PREFIX"],
                )
            except ValueError as exc:
                return _error(request_id, "invalid_arguments", str(exc))
        elif operation == "ssh.service.deploy":
            confirmed = args.get("confirmed", False)
            plan_id = args.get("plan_id")
            if type(confirmed) is not bool or (plan_id is not None and not isinstance(plan_id, str)):
                return _error(request_id, "invalid_arguments", "deployment confirmation or plan ID is invalid")
            data = runit_deployment.apply(
                prefix=process_env["PREFIX"], home=home, state_dir=state_dir,
                confirmed=confirmed, plan_id=plan_id,
            )
        elif operation in {"ssh.service.deploy.rollback.preview", "ssh.service.deploy.rollback.apply"}:
            operation_id = args.get("operation_id")
            confirmed = args.get("confirmed", False)
            plan_id = args.get("plan_id")
            if (not isinstance(operation_id, str) or type(confirmed) is not bool
                    or (plan_id is not None and not isinstance(plan_id, str))):
                return _error(request_id, "invalid_arguments", "deployment rollback arguments are invalid")
            rollback_args = {"prefix": process_env["PREFIX"], "home": home,
                             "state_dir": state_dir, "operation_id": operation_id}
            if operation.endswith(".preview"):
                data = runit_deployment.preview_rollback(**rollback_args)
            else:
                data = runit_deployment.apply_rollback(
                    **rollback_args, confirmed=confirmed, plan_id=plan_id,
                )
        elif operation in {"ssh.service.start", "ssh.service.stop", "ssh.service.restart"}:
            confirmed = args.get("confirmed", False)
            plan_id = args.get("plan_id")
            if type(confirmed) is not bool or (plan_id is not None and not isinstance(plan_id, str)):
                return _error(request_id, "invalid_arguments", "service confirmation or plan ID is invalid")
            action = operation.rsplit(".", 1)[1]
            data = runit_service.apply(
                action, prefix=process_env["PREFIX"], home=home, state_dir=state_dir,
                confirmed=confirmed, plan_id=plan_id,
            )
        elif operation == "boot.status":
            data = runtime_diagnostics.inspect_boot(home=home)
        elif operation == "boot.profile.status":
            data = boot_profiles.status(home=home, state_dir=state_dir,
                                        prefix=process_env["PREFIX"])
        elif operation == "boot.helpers.status":
            data = boot_helpers.status(home=home, state_dir=state_dir,
                source_root=Path(__file__).resolve().parents[1])
        elif operation == "boot.helpers.preview":
            helper_id, action, snapshot_id = args.get("helper_id"), args.get("action"), args.get("snapshot_id")
            if (helper_id not in boot_helpers.HELPERS or action not in {"deploy", "rollback"}
                    or (snapshot_id is not None and not isinstance(snapshot_id, str))
                    or (action == "rollback" and not snapshot_id)
                    or (action == "deploy" and snapshot_id is not None)):
                return _error(request_id, "invalid_arguments", "preview requires one managed helper and a valid deploy/rollback request")
            data = boot_helpers.preview(helper_id=helper_id, action=action,
                home=home, state_dir=state_dir, source_root=Path(__file__).resolve().parents[1],
                snapshot_id=snapshot_id)
        elif operation == "boot.helpers.apply":
            helper_id, action = args.get("helper_id"), args.get("action")
            snapshot_id, confirmed, plan_id = args.get("snapshot_id"), args.get("confirmed"), args.get("plan_id")
            if (helper_id not in boot_helpers.HELPERS or action not in {"deploy", "rollback"}
                    or type(confirmed) is not bool or not isinstance(plan_id, str)
                    or (snapshot_id is not None and not isinstance(snapshot_id, str))
                    or (action == "rollback" and not snapshot_id)
                    or (action == "deploy" and snapshot_id is not None)):
                return _error(request_id, "invalid_arguments", "apply requires a managed helper, exact action, plan ID, and confirmation")
            data = boot_helpers.apply(helper_id=helper_id, action=action,
                home=home, state_dir=state_dir, source_root=Path(__file__).resolve().parents[1],
                confirmed=confirmed, plan_id=plan_id, snapshot_id=snapshot_id)
        elif operation == "boot.profile.preview":
            profile = args.get("profile")
            if not isinstance(profile, str):
                return _error(request_id, "invalid_arguments", "profile must be a string")
            data = boot_profiles.preview(profile, home=home, state_dir=state_dir,
                                         prefix=process_env["PREFIX"])
        elif operation == "boot.enable":
            profile = args.get("profile")
            confirmed = args.get("confirmed", False)
            if not isinstance(profile, str) or type(confirmed) is not bool:
                return _error(request_id, "invalid_arguments", "profile or confirmation is invalid")
            boot_app = runtime_diagnostics.inspect_boot(home=home).get("app", "unknown")
            data = boot_profiles.enable(
                profile=profile, home=home, state_dir=state_dir, prefix=process_env["PREFIX"],
                confirmed=confirmed, boot_app_status=str(boot_app),
            )
        elif operation == "boot.disable":
            confirmed = args.get("confirmed", False)
            if type(confirmed) is not bool:
                return _error(request_id, "invalid_arguments", "confirmation is invalid")
            data = boot_profiles.disable(home=home, state_dir=state_dir, confirmed=confirmed)
        elif operation == "boot.cron.status":
            data = termux_boot_cron.status(home=home, state_dir=state_dir or os.path.join(home, ".local/share/ternuxx"))
        elif operation == "boot.cron.validate":
            data = termux_boot_cron.validate(home=home, state_dir=state_dir or os.path.join(home, ".local/share/ternuxx"), prefix=process_env["PREFIX"])
        elif operation == "boot.cron.preview":
            action = args.get("action")
            if action not in {"enable", "disable"}:
                return _error(request_id, "invalid_arguments", "action must be enable or disable")
            data = termux_boot_cron.preview(action, home=home)
        elif operation in {"boot.cron.enable", "boot.cron.disable"}:
            confirmed = args.get("confirmed", False)
            plan_id = args.get("plan_id")
            if type(confirmed) is not bool or (plan_id is not None and not isinstance(plan_id, str)):
                return _error(request_id, "invalid_arguments", "boot integration confirmation is invalid")
            if confirmed and not plan_id:
                return _error(request_id, "confirmation_required", "apply requires --yes and the exact preview --plan-id")
            action = "enable" if operation.endswith("enable") else "disable"
            data = termux_boot_cron.apply(action, home=home, state_dir=state_dir or os.path.join(home, ".local/share/ternuxx"), confirmed=confirmed, plan_id=plan_id)
        elif operation == "wakelock.status":
            data = wakelock_manager.status(state_dir=state_dir)
        elif operation in {"wakelock.acquire", "wakelock.release"}:
            owner = args.get("owner")
            persistent = args.get("persistent", False)
            if not isinstance(owner, str) or type(persistent) is not bool:
                return _error(request_id, "invalid_arguments", "owner or persistence policy is invalid")
            raw_pid = process_env.get("TERNUXX_WAKELOCK_CALLER_PID")
            try:
                caller_pid = int(raw_pid) if raw_pid else os.getppid()
            except ValueError:
                return _error(request_id, "invalid_arguments", "caller process identity is invalid")
            if not wakelock_manager.is_ancestor(caller_pid, os.getpid()):
                return _error(request_id, "unauthorized", "Wake Lock lease must be owned by the invoking process")
            operation_fn = wakelock_manager.acquire if operation == "wakelock.acquire" else wakelock_manager.release
            data = operation_fn(state_dir=state_dir, owner=owner, persistent=persistent,
                                caller_pid=caller_pid, prefix=process_env["PREFIX"])
        elif operation == "backup.list":
            data = config_recovery.list_backups(home=home, state_dir=state_dir)
        elif operation == "backup.inspect":
            backup_id = args.get("backup_id")
            if not isinstance(backup_id, str):
                return _error(request_id, "invalid_arguments", "backup_id must be a string")
            data = config_recovery.inspect_backup(home=home, state_dir=state_dir, backup_id=backup_id)
        elif operation == "backup.create":
            name = args.get("name")
            confirmed = args.get("confirmed", False)
            plan_id = args.get("plan_id")
            if not isinstance(name, str) or type(confirmed) is not bool or (plan_id is not None and not isinstance(plan_id, str)):
                return _error(request_id, "invalid_arguments", "backup name, confirmation, or plan ID is invalid")
            data = config_recovery.create_backup(home=home, state_dir=state_dir, name=name,
                                                 confirmed=confirmed, plan_id=plan_id)
        elif operation == "restore.preview":
            backup_id = args.get("backup_id")
            if not isinstance(backup_id, str):
                return _error(request_id, "invalid_arguments", "backup_id must be a string")
            data = config_recovery.restore_preview(home=home, state_dir=state_dir, backup_id=backup_id)
        elif operation == "restore.apply":
            backup_id = args.get("backup_id")
            confirmed = args.get("confirmed", False)
            plan_id = args.get("plan_id")
            if not isinstance(backup_id, str) or type(confirmed) is not bool or (plan_id is not None and not isinstance(plan_id, str)):
                return _error(request_id, "invalid_arguments", "restore ID, confirmation, or plan ID is invalid")
            data = config_recovery.restore_backup(home=home, state_dir=state_dir, backup_id=backup_id,
                                                  confirmed=confirmed, plan_id=plan_id)
        elif operation == "recovery.resolve":
            operation_id = args.get("operation_id")
            confirmed = args.get("confirmed", False)
            plan_id = args.get("plan_id")
            if (not isinstance(operation_id, str) or type(confirmed) is not bool
                    or (plan_id is not None and not isinstance(plan_id, str))):
                return _error(request_id, "invalid_arguments", "recovery operation ID, confirmation, or plan ID is invalid")
            data = operation_recovery.resolve(operation_id, prefix=process_env["PREFIX"], home=home,
                                              state_dir=state_dir, confirmed=confirmed, plan_id=plan_id)
        elif operation == "recovery.status":
            records = operation_journal.list_records(state_dir, home_dir=home)
            data = {"operations": records,
                    "unresolved_count": sum(record["status"] in operation_journal.ACTIVE for record in records),
                    "read_only": True}
        elif operation == "recovery.inspect":
            operation_id = args.get("operation_id")
            if not isinstance(operation_id, str):
                return _error(request_id, "invalid_arguments", "operation_id must be a string")
            data = {"operation": operation_journal.inspect_record(state_dir, operation_id, home_dir=home),
                    "read_only": True}
        elif operation == "recovery.rollback.preview":
            operation_id = args.get("operation_id")
            if not isinstance(operation_id, str):
                return _error(request_id, "invalid_arguments", "operation_id must be a string")
            data = config_recovery.rollback_preview(home=home, state_dir=state_dir, operation_id=operation_id)
        elif operation == "recovery.rollback.apply":
            operation_id = args.get("operation_id")
            confirmed = args.get("confirmed", False)
            plan_id = args.get("plan_id")
            if (not isinstance(operation_id, str) or type(confirmed) is not bool
                    or (plan_id is not None and not isinstance(plan_id, str))):
                return _error(request_id, "invalid_arguments", "rollback operation, confirmation, or plan ID is invalid")
            data = config_recovery.rollback_restore(home=home, state_dir=state_dir, operation_id=operation_id,
                                                   confirmed=confirmed, plan_id=plan_id)
        elif operation == "continuity.status":
            data = reboot_recovery.status(home=home, state_dir=state_dir, test_id=args.get("test_id"))
        elif operation == "continuity.prepare":
            data = continuity.prepare(
                home=home,
                state_dir=state_dir,
                test_id=args.get("test_id", "manual-checkpoint"),
                repository=args.get("repository", "soobujmiah/ternuxx"),
                commit=args.get("commit", "unknown"),
                worktree_state=args.get("worktree_state", "unknown"),
                task_state=args.get("task_state", "prepared"),
                pending_tests=args.get("pending_tests", []),
                next_safe_action=args.get("next_safe_action", "owner_verify_after_reboot"),
            )
        elif operation == "continuity.verify":
            data = continuity.verify(home=home, state_dir=state_dir, checkpoint_id=args["checkpoint_id"])
        elif operation == "continuity.prepare-reboot-test":
            data = reboot_recovery.prepare(home=home, state_dir=state_dir, test_id=args["test_id"],
                                           evidence=args["baseline"],
                                           boot_id=args.get("boot_id"))
        elif operation == "continuity.verify-reboot-test":
            data = reboot_recovery.verify_pending(home=home, state_dir=state_dir, test_id=args["test_id"],
                                                  current_boot_id=args.get("current_boot_id"))
        else:
            data = reboot_recovery.resume_info(home=home, state_dir=state_dir, test_id=args["test_id"])
    except boot_helpers.BootHelperError as exc:
        return _error(request_id, "boot_helper_operation_failed", str(exc))
    except timezone_support.TimezoneError as exc:
        return _error(request_id, "timezone_configuration_error", str(exc))
    except cron_execution.ExecutionError as exc:
        return _error(request_id, "cron_execution_error", str(exc))
    except cron_registry.CronError as exc:
        return _error(request_id, "cron_registry_error", str(exc))
    except runit_deployment.DeploymentError as exc:
        return _error(request_id, "deployment_failed", str(exc))
    except proot_sessions.SessionError as exc:
        return _error(request_id, "proot_operation_failed", str(exc))
    except proot_shortcuts.ShortcutError as exc:
        return _error(request_id, "shortcut_operation_failed", str(exc))
    except config_recovery.RecoveryError as exc:
        return _error(request_id, "recovery_failed", str(exc))
    except remote_access_policy.RemoteAccessPolicyError as exc:
        return _error(request_id, "invalid_remote_access_policy", str(exc))
    except continuity.CheckpointError as exc:
        return _error(request_id, "operation_failed", str(exc))
    except reboot_recovery.RecoveryError as exc:
        return _error(request_id, "operation_failed", str(exc))
    except wakelock_manager.WakeLockError as exc:
        return _error(request_id, "operation_failed", str(exc))
    except ValueError as exc:
        if operation == "management.catalog":
            return _error(request_id, "invalid_arguments", str(exc))
        return _error(request_id, "operation_failed", f"operation could not complete ({exc.__class__.__name__})")
    except (KeyError, TypeError, OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        return _error(request_id, "operation_failed", f"operation could not complete ({exc.__class__.__name__})")
    return {"api_version": API_VERSION, "request_id": request_id, "ok": True, "operation": operation, "data": data}


def _error(request_id: str, code: str, message: str) -> dict[str, object]:
    return {"api_version": API_VERSION, "request_id": request_id, "ok": False, "error": {"code": code, "message": message}}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ternuxx management-service", add_help=False)
    parser.add_argument("--operation", required=True, choices=sorted(OPERATIONS))
    parser.add_argument("--test-id")
    parser.add_argument("--repository", default="soobujmiah/ternuxx")
    parser.add_argument("--commit", default="unknown")
    parser.add_argument("--worktree-state", default="unknown", choices=("clean", "dirty", "unknown"))
    parser.add_argument("--task-state", default="prepared", choices=("prepared", "pending", "blocked", "verified"))
    parser.add_argument("--pending-test", action="append", default=[])
    parser.add_argument("--next-safe-action", default="owner_verify_after_reboot", choices=sorted(continuity.NEXT_ACTIONS))
    parser.add_argument("--checkpoint-id")
    parser.add_argument("--baseline-json")
    parser.add_argument("--distro", choices=("debian",))
    parser.add_argument("--guest-user")
    parser.add_argument("--guest-user-source", choices=("rootfs",))
    parser.add_argument("--display", choices=tuple(f":{number}" for number in range(11)))
    parser.add_argument("--backend", choices=("zink", "virgl"))
    parser.add_argument("--provider", choices=("native", "debian"))
    parser.add_argument("--graphics-api", choices=("opengl", "gles", "vulkan"))
    parser.add_argument("--graphics-backend", choices=("kgsl-freedreno", "system"))
    parser.add_argument("--policy-stdin", action="store_true",
                        help="read a secret-free remote-access desired policy JSON object from stdin")
    parser.add_argument("--current-boot-id")
    parser.add_argument("--owner")
    parser.add_argument("--profile", choices=tuple(sorted(set(boot_profiles.PROFILES) | set(proot_sessions.PROFILES))))
    parser.add_argument("--boot-action", choices=("enable", "disable"))
    parser.add_argument("--helper-id", choices=tuple(boot_helpers.HELPERS))
    parser.add_argument("--helper-action", choices=("deploy", "rollback"))
    parser.add_argument("--snapshot-id")
    parser.add_argument("--name")
    parser.add_argument("--backup-id")
    parser.add_argument("--operation-id")
    parser.add_argument("--job-id")
    parser.add_argument("--mutation-action", choices=("create", "update", "remove"))
    parser.add_argument("--execution-id")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--source-id", choices=tuple(management_log_reader.SOURCES))
    parser.add_argument("--poll-seconds", type=int, default=5)
    parser.add_argument("--job-name")
    parser.add_argument("--job-description", default="Scheduled Ternuxx action")
    parser.add_argument("--job-action", choices=sorted(cron_registry._ALLOWED_ACTIONS))
    parser.add_argument("--schedule-type", choices=sorted(cron_registry._SCHEDULE_TYPES))
    parser.add_argument("--cron-expression")
    parser.add_argument("--timezone")
    parser.add_argument("--interval-seconds", type=int)
    parser.add_argument("--anchor-at")
    parser.add_argument("--calendar-mode", choices=("daily", "specific"))
    parser.add_argument("--calendar-time")
    parser.add_argument("--datetime")
    parser.add_argument("--at")
    parser.add_argument("--job-environment", choices=("native-termux", "debian-proot"), default="native-termux")
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--max-attempts", type=int, default=1)
    parser.add_argument("--retry-delay-seconds", type=int, default=0)
    parser.add_argument("--retry-backoff", choices=("fixed", "exponential"), default="fixed")
    parser.add_argument("--missed-run-policy", choices=sorted(cron_registry._MISSED), default="skip")
    parser.add_argument("--concurrency-policy", choices=sorted(cron_registry._CONCURRENCY), default="skip_overlap")
    job_toggle = parser.add_mutually_exclusive_group()
    job_toggle.add_argument("--job-enabled", dest="job_enabled", action="store_true", default=None)
    job_toggle.add_argument("--job-disabled", dest="job_enabled", action="store_false")
    boot_toggle = parser.add_mutually_exclusive_group()
    boot_toggle.add_argument("--run-after-device-boot", dest="device_boot", action="store_true", default=None)
    boot_toggle.add_argument("--no-device-boot", dest="device_boot", action="store_false")
    recovery_toggle = parser.add_mutually_exclusive_group()
    recovery_toggle.add_argument("--run-after-scheduler-recovery", dest="scheduler_recovery", action="store_true", default=None)
    recovery_toggle.add_argument("--no-scheduler-recovery", dest="scheduler_recovery", action="store_false")
    parser.add_argument("--job-json-stdin", action="store_true", help="read typed job/changes JSON from stdin")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--shortcut-action", choices=("add", "remove"))
    parser.add_argument("--app-id")
    parser.add_argument("--desktop-id")
    parser.add_argument("--plan-id")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--persistent", action="store_true")
    parser.add_argument("--graphics", action="store_true")
    parser.add_argument("--category")
    parser.add_argument("--query")
    parser.add_argument("--status", choices=("implemented", "partial", "external", "unverified", "unavailable", "planned"))
    monitor_toggle = parser.add_mutually_exclusive_group()
    monitor_toggle.add_argument("--monitor-enabled", dest="monitor_enabled", action="store_true", default=None)
    monitor_toggle.add_argument("--monitor-disabled", dest="monitor_enabled", action="store_false")
    parser.add_argument("--monitor-interval", type=int)
    parser.add_argument("--monitor-unit", choices=("seconds", "minutes", "hours"))
    parser.add_argument("--monitor-activity-launch", action="store_true", default=None)
    parser.add_argument("--monitor-no-activity-launch", action="store_false", dest="monitor_activity_launch", default=None)
    parser.add_argument("--monitor-focus-check", action="store_true", default=None)
    parser.add_argument("--monitor-no-focus-check", action="store_false", dest="monitor_focus_check", default=None)
    parser.add_argument("--json", action="store_true")
    return parser


def _cli_job(args: argparse.Namespace) -> dict[str, object] | None:
    if not all((args.job_name, args.job_action, args.schedule_type)):
        return None
    if args.timezone is not None and args.schedule_type not in {"cron", "calendar"}:
        return None
    if args.schedule_type == "calendar" and args.calendar_mode == "specific" and args.timezone is not None:
        return None
    schedule: dict[str, object]
    if args.schedule_type == "cron":
        if not args.cron_expression: return None
        schedule = {"expression": args.cron_expression}
        if args.timezone is not None:
            schedule["timezone"] = args.timezone
    elif args.schedule_type == "interval":
        if args.interval_seconds is None or not args.anchor_at: return None
        schedule = {"interval_seconds": args.interval_seconds, "anchor_at": args.anchor_at}
    elif args.schedule_type == "calendar":
        if args.calendar_mode == "daily" and args.calendar_time:
            schedule = {"mode": "daily", "time": args.calendar_time}
            if args.timezone is not None:
                schedule["timezone"] = args.timezone
        elif args.calendar_mode == "specific" and args.datetime:
            schedule = {"mode": "specific", "datetime": args.datetime}
        else: return None
    else:
        if not args.at: return None
        schedule = {"at": args.at}
    try:
        timezone_name = args.timezone
        if timezone_name is None and args.schedule_type in {"cron", "calendar"}:
            home = os.environ.get("HOME", "")
            state_dir = os.environ.get("TERNUXX_STATE_DIR") or os.path.join(home, ".local/share/ternuxx")
            timezone_name = timezone_support.current_timezone(
                state_dir, installation_timezone=os.environ.get("TERNUXX_INSTALL_TIMEZONE"))
        if args.schedule_type == "cron" and schedule.get("timezone") is None:
            schedule["timezone"] = timezone_name
        if args.schedule_type == "calendar" and schedule.get("mode") == "daily" and schedule.get("timezone") is None:
            schedule["timezone"] = timezone_name
        return cron_registry.new_job(name=args.job_name, description=args.job_description,
            action_id=args.job_action, schedule_type=args.schedule_type, schedule=schedule,
            enabled=bool(args.job_enabled), run_after_device_boot=bool(args.device_boot),
            run_after_scheduler_recovery=bool(args.scheduler_recovery), timeout_seconds=args.timeout_seconds,
            retry_policy={"max_attempts": args.max_attempts, "delay_seconds": args.retry_delay_seconds,
                          "backoff": args.retry_backoff}, missed_run_policy=args.missed_run_policy,
            concurrency_policy=args.concurrency_policy, environment=args.job_environment)
    except ValueError:
        return None


def _cli_job_changes(args: argparse.Namespace) -> dict[str, object]:
    changes: dict[str, object] = {}
    if args.job_name is not None: changes["name"] = args.job_name
    if args.job_description != "Scheduled Ternuxx action": changes["description"] = args.job_description
    if args.job_enabled is not None: changes["enabled"] = args.job_enabled
    if args.device_boot is not None: changes["run_after_device_boot"] = args.device_boot
    if args.scheduler_recovery is not None: changes["run_after_scheduler_recovery"] = args.scheduler_recovery
    return changes


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    request_id = uuid.uuid4().hex
    payload: dict[str, object]
    if args.policy_stdin and args.operation != "remote.access.preview":
        response = _error(request_id, "invalid_arguments", "--policy-stdin is only valid for remote.access.preview")
        if args.json:
            print(json.dumps(response, sort_keys=True))
        else:
            print(f"Ternuxx operation failed [{response['error']['code']}]: {response['error']['message']}", file=sys.stderr)
        return 1
    if args.operation == "remote.access.preview":
        if args.policy_stdin:
            if sys.stdin.isatty():
                response = _error(request_id, "invalid_arguments", "--policy-stdin requires piped JSON input")
                if args.json:
                    print(json.dumps(response, sort_keys=True))
                else:
                    print(f"Ternuxx operation failed [{response['error']['code']}]: {response['error']['message']}", file=sys.stderr)
                return 1
            try:
                policy = json.load(sys.stdin)
            except (json.JSONDecodeError, UnicodeDecodeError):
                policy = []
            payload = {"policy": policy}
        else:
            payload = {}
    elif args.operation == "proot.guest.verify":
        explicit_user = bool(args.guest_user)
        rootfs_user = args.guest_user_source == "rootfs"
        if (not all((args.distro, args.display, args.backend))
                or explicit_user == rootfs_user):
            response = _error(request_id, "invalid_arguments", "proot guest verify requires exactly one of --guest-user USER or --guest-user-source rootfs")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print(f"Ternuxx operation failed [{response['error']['code']}]: {response['error']['message']}", file=sys.stderr)
            return 1
        payload = {"distro": args.distro, "display": args.display, "backend": args.backend}
        if explicit_user:
            payload["user"] = args.guest_user
        else:
            payload["user_source"] = "rootfs"
    elif args.operation == "management.catalog":
        payload = {key: value for key, value in (("category", args.category), ("query", args.query), ("status", args.status)) if value is not None}
    elif args.operation == "management.logs.list":
        payload = {}
    elif args.operation == "management.logs.read":
        if not args.source_id:
            response = _error(request_id, "invalid_arguments", "--source-id is required")
            print(json.dumps(response, sort_keys=True) if args.json else "Provide --source-id.", file=None if args.json else sys.stderr)
            return 1
        payload = {"source_id": args.source_id, "limit": args.limit}
    elif args.operation == "graphics.provider.status":
        if not args.provider:
            response = _error(request_id, "invalid_arguments", "--provider is required")
            print(json.dumps(response, sort_keys=True) if args.json else "Provide --provider native|debian.", file=None if args.json else sys.stderr)
            return 1
        payload = {"provider": args.provider}
    elif args.operation == "graphics.provider.select":
        if args.provider != "native" or not args.graphics_backend or not args.yes:
            response = _error(request_id, "confirmation_required", "select requires --provider native, --graphics-backend, and --yes")
            print(json.dumps(response, sort_keys=True) if args.json else "Confirm native graphics backend selection with --yes.", file=None if args.json else sys.stderr)
            return 1
        payload = {"provider": args.provider, "backend": args.graphics_backend, "confirmed": True}
    elif args.operation == "graphics.provider.verify":
        if not args.provider or not args.graphics_api:
            response = _error(request_id, "invalid_arguments", "--provider and --graphics-api are required")
            print(json.dumps(response, sort_keys=True) if args.json else "Provide --provider and --graphics-api.", file=None if args.json else sys.stderr)
            return 1
        payload = {"provider": args.provider, "api": args.graphics_api, "display": args.display or ":1"}
    elif args.operation == "cron.scheduler.start":
        payload = {"poll_seconds": args.poll_seconds, "confirmed": bool(args.yes)}
    elif args.operation == "cron.scheduler.stop":
        payload = {"confirmed": bool(args.yes)}
    elif args.operation in {"proot.sessions.list", "proot.profiles.list"}:
        payload = {}
    elif args.operation in {"proot.profiles.show", "proot.start.preview"}:
        if not args.profile:
            response = _error(request_id, "invalid_arguments", "--profile is required")
            if args.json: print(json.dumps(response, sort_keys=True))
            else: print("Provide --profile.", file=sys.stderr)
            return 1
        payload = {"profile": args.profile}
    elif args.operation == "proot.start":
        if not args.profile or not args.yes or not args.plan_id:
            response = _error(request_id, "confirmation_required", "start requires --profile, --yes, and the exact --plan-id")
            if args.json: print(json.dumps(response, sort_keys=True))
            else: print("Preview first, then provide --profile, --yes, and --plan-id.", file=sys.stderr)
            return 1
        payload = {"profile": args.profile, "confirmed": True, "plan_id": args.plan_id,
                   "timeout_seconds": args.timeout_seconds}
    elif args.operation == "proot.stop.preview":
        if not args.operation_id:
            response = _error(request_id, "invalid_arguments", "session ID is required")
            if args.json: print(json.dumps(response, sort_keys=True))
            else: print("Provide a Ternuxx session ID.", file=sys.stderr)
            return 1
        payload = {"session_id": args.operation_id}
    elif args.operation == "proot.stop":
        if not args.operation_id or not args.yes or not args.plan_id:
            response = _error(request_id, "confirmation_required", "stop requires a session ID, --yes, and exact --plan-id")
            if args.json: print(json.dumps(response, sort_keys=True))
            else: print("Preview first, then provide SESSION_ID, --yes, and --plan-id.", file=sys.stderr)
            return 1
        payload = {"session_id": args.operation_id, "confirmed": True, "plan_id": args.plan_id}
    elif args.operation == "proot.recovery.reconcile":
        if not args.operation_id or not args.yes or not args.plan_id:
            response = _error(request_id, "confirmation_required", "reconciliation requires session ID, --yes, and exact --plan-id")
            if args.json: print(json.dumps(response, sort_keys=True))
            else: print("Preview first, then provide SESSION_ID, --yes, and --plan-id.", file=sys.stderr)
            return 1
        payload = {"session_id": args.operation_id, "confirmed": True, "plan_id": args.plan_id}
    elif args.operation in {"proot.sessions.show", "proot.sessions.health", "proot.recovery.inspect",
                                   "proot.recovery.reconcile.preview"}:
        if not args.operation_id:
            response = _error(request_id, "invalid_arguments", "--operation-id must contain the session ID")
            if args.json: print(json.dumps(response, sort_keys=True))
            else: print("Provide the Ternuxx PRoot session ID.", file=sys.stderr)
            return 1
        payload = {"session_id": args.operation_id}
    elif args.operation == "timezone.set":
        if not args.timezone:
            response = _error(request_id, "invalid_arguments", "--timezone is required")
            if args.json: print(json.dumps(response, sort_keys=True))
            else: print("Provide --timezone IANA_NAME.", file=sys.stderr)
            return 1
        payload = {"timezone": args.timezone}
    elif args.operation in {"timezone.status", "timezone.list"}:
        payload = {}
    elif args.operation == "cron.executions.list":
        payload = {"limit": args.limit}
        if args.job_id:
            payload["job_id"] = args.job_id
    elif args.operation == "cron.executions.show":
        if not args.execution_id:
            response = _error(request_id, "invalid_arguments", "--execution-id is required")
            if args.json: print(json.dumps(response, sort_keys=True))
            else: print("Provide --execution-id.", file=sys.stderr)
            return 1
        payload = {"execution_id": args.execution_id}
    elif args.operation.startswith("cron."):
        payload = {}
        if args.operation in {"cron.jobs.show", "cron.jobs.validate", "cron.jobs.next_runs"}:
            if args.job_id:
                payload["job_id"] = args.job_id
            elif args.operation != "cron.jobs.validate":
                response = _error(request_id, "invalid_arguments", "--job-id is required")
                if args.json: print(json.dumps(response, sort_keys=True))
                else: print(f"Ternuxx operation failed [{response['error']['code']}]: {response['error']['message']}", file=sys.stderr)
                return 1
        if args.operation == "cron.jobs.next_runs":
            payload["count"] = args.count
        if args.operation == "cron.jobs.validate" and not args.job_id:
            job = _cli_job(args)
            if job is None:
                response = _error(request_id, "invalid_arguments", "typed job fields are incomplete or invalid")
                if args.json: print(json.dumps(response, sort_keys=True))
                else: print("Provide the documented typed job fields and schedule options.", file=sys.stderr)
                return 1
            payload["job"] = job
        if args.operation == "cron.jobs.mutation.preview":
            action = args.mutation_action
            if action == "create":
                job = _cli_job(args)
                if job is None:
                    response = _error(request_id, "invalid_arguments", "typed job fields are incomplete or invalid")
                    if args.json: print(json.dumps(response, sort_keys=True))
                    else: print("Provide the documented typed job fields and schedule options.", file=sys.stderr)
                    return 1
                payload = {"action": action, "job": job}
            elif action == "update":
                changes = _cli_job_changes(args)
                if not args.job_id or not changes:
                    response = _error(request_id, "invalid_arguments", "update preview requires --job-id and at least one typed change")
                    if args.json: print(json.dumps(response, sort_keys=True))
                    else: print("Provide a job ID and a new name, enabled state, or supported change.", file=sys.stderr)
                    return 1
                payload = {"action": action, "job_id": args.job_id, "changes": changes}
            elif action == "remove":
                if not args.job_id:
                    response = _error(request_id, "invalid_arguments", "remove preview requires --job-id")
                    if args.json: print(json.dumps(response, sort_keys=True))
                    else: print("Provide --job-id.", file=sys.stderr)
                    return 1
                payload = {"action": action, "job_id": args.job_id}
            else:
                response = _error(request_id, "invalid_arguments", "--mutation-action is required")
                if args.json: print(json.dumps(response, sort_keys=True))
                else: print("Provide --mutation-action create|update|remove.", file=sys.stderr)
                return 1
            if args.yes or args.plan_id:
                response = _error(request_id, "invalid_arguments", "Cron preview does not accept --yes or --plan-id")
                if args.json: print(json.dumps(response, sort_keys=True))
                else: print("Preview does not accept apply flags.", file=sys.stderr)
                return 1
        if args.operation == "cron.jobs.mutation.apply":
            if not args.yes or not args.plan_id:
                response = _error(request_id, "confirmation_required", "Cron apply requires --yes and the exact --plan-id from preview")
                if args.json: print(json.dumps(response, sort_keys=True))
                else: print("Preview first, then apply with --yes --plan-id PLAN_ID.", file=sys.stderr)
                return 1
            payload = {"plan_id": args.plan_id, "confirmed": True}
    elif args.operation in {"cron.status", "agent.hermes.status", "ssh.inspect", "proot.status", "terminal.broker.status", "native.ssh.status", "ssh.keys.list", "boot.status", "wakelock.status", "continuity.status", "boot.profile.status", "boot.helpers.status", "boot.cron.status", "boot.cron.validate", "backup.list", "recovery.status"}:
        payload = {}
        if args.operation == "continuity.status" and args.test_id:
            payload["test_id"] = args.test_id
    elif args.operation == "desktop.monitor.configure":
        payload = {}
        for source, target in ((args.monitor_enabled, "enabled"),
                               (args.monitor_activity_launch, "activity_launch"),
                               (args.monitor_focus_check, "focus_check")):
            if source is not None:
                payload[target] = source
        if args.monitor_interval is not None:
            payload["interval_value"] = args.monitor_interval
            payload["unit"] = args.monitor_unit or "seconds"
        elif args.monitor_unit is not None:
            response = _error(request_id, "invalid_arguments", "--monitor-unit requires --monitor-interval")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print(f"Ternuxx operation failed [{response['error']['code']}]: {response['error']['message']}", file=sys.stderr)
            return 1
    elif args.operation == "desktop.monitor.status":
        payload = {}
    elif args.operation == "doctor.report":
        payload = {"graphics": bool(args.graphics)}
    elif args.operation in {"ssh.service.deploy.rollback.preview", "ssh.service.deploy.rollback.apply"}:
        if not args.operation_id:
            response = _error(request_id, "invalid_arguments", "--operation-id is required")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print(f"Ternuxx operation failed [{response['error']['code']}]: {response['error']['message']}", file=sys.stderr)
            return 1
        is_preview = args.operation.endswith(".preview")
        if is_preview and (args.yes or args.plan_id):
            response = _error(request_id, "invalid_arguments", "rollback preview does not accept apply confirmation")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print(f"Ternuxx operation failed [{response['error']['code']}]: {response['error']['message']}", file=sys.stderr)
            return 1
        if not is_preview and (not args.yes or not args.plan_id):
            response = _error(request_id, "invalid_arguments", "rollback apply requires --yes and --plan-id")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print(f"Ternuxx operation failed [{response['error']['code']}]: {response['error']['message']}", file=sys.stderr)
            return 1
        payload = {"operation_id": args.operation_id}
        if not is_preview:
            payload.update({"confirmed": True, "plan_id": args.plan_id})
    elif args.operation in {"ssh.service.start", "ssh.service.stop", "ssh.service.restart", "ssh.service.deploy"}:
        if args.yes != bool(args.plan_id):
            response = _error(request_id, "invalid_arguments", "service apply requires --yes and --plan-id from its exact preview")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print(f"Ternuxx operation failed [{response['error']['code']}]: {response['error']['message']}", file=sys.stderr)
            return 1
        payload = {"confirmed": args.yes, "plan_id": args.plan_id}
    elif args.operation == "boot.helpers.preview":
        if not args.helper_id or not args.helper_action or (args.helper_action == "rollback" and not args.snapshot_id):
            response = _error(request_id, "invalid_arguments", "helper ID, action, and rollback snapshot are required")
            if args.json: print(json.dumps(response, sort_keys=True))
            else: print("Provide --helper-id, --helper-action, and --snapshot-id for rollback.", file=sys.stderr)
            return 1
        payload = {"helper_id": args.helper_id, "action": args.helper_action, "snapshot_id": args.snapshot_id}
    elif args.operation == "boot.helpers.apply":
        if not args.helper_id or not args.helper_action or not args.plan_id or not args.yes or (args.helper_action == "rollback" and not args.snapshot_id):
            response = _error(request_id, "confirmation_required", "boot helper apply requires helper, action, exact plan, and --yes")
            if args.json: print(json.dumps(response, sort_keys=True))
            else: print("Preview first, then apply with --yes --plan-id.", file=sys.stderr)
            return 1
        payload = {"helper_id": args.helper_id, "action": args.helper_action,
                   "snapshot_id": args.snapshot_id, "confirmed": True, "plan_id": args.plan_id}
    elif args.operation == "boot.profile.preview":
        if not args.profile:
            response = _error(request_id, "invalid_arguments", "--profile is required")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print("Ternuxx operation failed [invalid_arguments]: --profile is required", file=sys.stderr)
            return 1
        payload = {"profile": args.profile}
    elif args.operation == "boot.enable":
        if not args.profile:
            response = _error(request_id, "invalid_arguments", "--profile is required")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print("Ternuxx operation failed [invalid_arguments]: --profile is required", file=sys.stderr)
            return 1
        payload = {"profile": args.profile, "confirmed": args.yes}
    elif args.operation == "boot.disable":
        payload = {"confirmed": args.yes}
    elif args.operation == "boot.cron.preview":
        if not args.boot_action:
            response = _error(request_id, "invalid_arguments", "--boot-action is required")
            print(json.dumps(response, sort_keys=True) if args.json else "Ternuxx operation failed [invalid_arguments]: --boot-action is required", file=None if args.json else sys.stderr)
            return 1
        payload = {"action": args.boot_action}
    elif args.operation in {"boot.cron.enable", "boot.cron.disable"}:
        payload = {"confirmed": args.yes}
        if args.plan_id is not None:
            payload["plan_id"] = args.plan_id
    elif args.operation in {"wakelock.acquire", "wakelock.release"}:
        if not args.owner:
            response = _error(request_id, "invalid_arguments", "--owner is required")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print("Ternuxx operation failed [invalid_arguments]: --owner is required", file=sys.stderr)
            return 1
        payload = {"owner": args.owner, "persistent": args.persistent}
    elif args.operation == "continuity.prepare-reboot-test":
        try:
            baseline = json.loads(args.baseline_json or "")
        except json.JSONDecodeError:
            baseline = None
        if not args.test_id or not isinstance(baseline, dict):
            response = _error(request_id, "invalid_arguments", "--test-id and a valid --baseline-json object are required")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print("Ternuxx operation failed [invalid_arguments]: reboot-test evidence is missing or invalid", file=sys.stderr)
            return 1
        if not args.test_id:
            response = _error(request_id, "invalid_arguments", "--test-id is required")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print("Ternuxx operation failed [invalid_arguments]: --test-id is required", file=sys.stderr)
            return 1
        payload = {"test_id": args.test_id, "baseline": baseline}
    elif args.operation == "continuity.verify-reboot-test":
        if not args.test_id:
            response = _error(request_id, "invalid_arguments", "--test-id is required")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print("Ternuxx operation failed [invalid_arguments]: --test-id is required", file=sys.stderr)
            return 1
        payload = {"test_id": args.test_id, "current_boot_id": args.current_boot_id}
    elif args.operation == "continuity.resume-info":
        if not args.test_id:
            response = _error(request_id, "invalid_arguments", "--test-id is required")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print("Ternuxx operation failed [invalid_arguments]: --test-id is required", file=sys.stderr)
            return 1
        payload = {"test_id": args.test_id}
    elif args.operation == "backup.create":
        if not args.name:
            response = _error(request_id, "invalid_arguments", "--name is required for an explicit backup preview")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print(f"Ternuxx operation failed [{response['error']['code']}]: {response['error']['message']}", file=sys.stderr)
            return 1
        payload = {"name": args.name, "confirmed": args.yes, "plan_id": args.plan_id}
    elif args.operation == "recovery.inspect":
        if not args.operation_id:
            response = _error(request_id, "invalid_arguments", "--operation-id is required")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print(f"Ternuxx operation failed [{response['error']['code']}]: {response['error']['message']}", file=sys.stderr)
            return 1
        payload = {"operation_id": args.operation_id}
    elif args.operation == "recovery.resolve":
        if not args.operation_id:
            response = _error(request_id, "invalid_arguments", "--operation-id is required")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print("Ternuxx operation failed [invalid_arguments]: --operation-id is required", file=sys.stderr)
            return 1
        if args.yes != bool(args.plan_id):
            response = _error(request_id, "invalid_arguments", "recovery apply requires --yes and --plan-id from the exact preview")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print(f"Ternuxx operation failed [{response['error']['code']}]: {response['error']['message']}", file=sys.stderr)
            return 1
        payload = {"operation_id": args.operation_id, "confirmed": args.yes, "plan_id": args.plan_id}
    elif args.operation in {"recovery.rollback.preview", "recovery.rollback.apply"}:
        if not args.operation_id:
            response = _error(request_id, "invalid_arguments", "--operation-id is required")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print(f"Ternuxx operation failed [{response['error']['code']}]: {response['error']['message']}", file=sys.stderr)
            return 1
        if args.operation == "recovery.rollback.preview":
            if args.yes or args.plan_id:
                response = _error(request_id, "invalid_arguments", "rollback preview does not accept --yes or --plan-id")
                if args.json:
                    print(json.dumps(response, sort_keys=True))
                else:
                    print(f"Ternuxx operation failed [{response['error']['code']}]: {response['error']['message']}", file=sys.stderr)
                return 1
            payload = {"operation_id": args.operation_id}
        else:
            if not args.yes or not args.plan_id:
                response = _error(request_id, "invalid_arguments", "rollback apply requires --yes and --plan-id from its exact preview")
                if args.json:
                    print(json.dumps(response, sort_keys=True))
                else:
                    print(f"Ternuxx operation failed [{response['error']['code']}]: {response['error']['message']}", file=sys.stderr)
                return 1
            payload = {"operation_id": args.operation_id, "confirmed": True, "plan_id": args.plan_id}
    elif args.operation in {"backup.inspect", "restore.preview", "restore.apply"}:
        if not args.backup_id:
            response = _error(request_id, "invalid_arguments", "--backup-id is required")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print(f"Ternuxx operation failed [{response['error']['code']}]: {response['error']['message']}", file=sys.stderr)
            return 1
        if args.operation == "backup.inspect":
            payload = {"backup_id": args.backup_id}
        elif args.operation == "restore.preview":
            payload = {"backup_id": args.backup_id}
        else:
            payload = {"backup_id": args.backup_id, "confirmed": args.yes, "plan_id": args.plan_id}
    elif args.operation == "proot.app.launch":
        if (bool(args.app_id) == bool(args.desktop_id) or args.shortcut_action or args.yes or args.plan_id):
            response = _error(request_id, "invalid_arguments", "exactly one of --app-id or --desktop-id is required for a PRoot app launch")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print("Ternuxx operation failed [invalid_arguments]: provide exactly one of --app-id or --desktop-id", file=sys.stderr)
            return 1
        payload = {"app_id": args.app_id} if args.app_id else {"desktop_id": args.desktop_id}
        if args.display is not None:
            payload["display"] = args.display
    elif args.operation == "proot.shortcuts.sync":
        if args.shortcut_action or args.app_id or args.desktop_id or args.yes or args.plan_id:
            response = _error(request_id, "invalid_arguments", "PRoot Apps sync takes no arguments")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print(f"Ternuxx operation failed [{response['error']['code']}]: {response['error']['message']}", file=sys.stderr)
            return 1
        payload = {}
    elif args.operation == "proot.shortcuts.list":
        if args.shortcut_action or args.app_id or args.desktop_id or args.yes or args.plan_id:
            response = _error(request_id, "invalid_arguments", "shortcut list takes no arguments")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print("Ternuxx operation failed [invalid_arguments]: shortcut list takes no arguments", file=sys.stderr)
            return 1
        payload = {}
    elif args.operation in {"proot.shortcuts.preview", "proot.shortcuts.apply"}:
        if not args.shortcut_action or not args.app_id:
            response = _error(request_id, "invalid_arguments", "--shortcut-action and --app-id are required")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print("Ternuxx operation failed [invalid_arguments]: --shortcut-action and --app-id are required", file=sys.stderr)
            return 1
        if args.operation == "proot.shortcuts.preview":
            if args.yes or args.plan_id:
                response = _error(request_id, "invalid_arguments", "shortcut preview does not accept --yes or --plan-id")
                if args.json:
                    print(json.dumps(response, sort_keys=True))
                else:
                    print("Ternuxx operation failed [invalid_arguments]: shortcut preview does not accept apply flags", file=sys.stderr)
                return 1
            payload = {"action": args.shortcut_action, "app_id": args.app_id}
        else:
            if not args.yes or not args.plan_id:
                response = _error(request_id, "invalid_arguments", "shortcut apply requires --yes and --plan-id from its exact preview")
                if args.json:
                    print(json.dumps(response, sort_keys=True))
                else:
                    print("Ternuxx operation failed [invalid_arguments]: shortcut apply requires --yes and --plan-id", file=sys.stderr)
                return 1
            payload = {"action": args.shortcut_action, "app_id": args.app_id,
                       "confirmed": True, "plan_id": args.plan_id}
    elif args.operation in {"ssh.inspect", "ssh.keys.list"}:
        payload = {}
    elif args.operation == "continuity.prepare":
        payload = {"test_id": args.test_id or "manual-checkpoint", "repository": args.repository, "commit": args.commit,
                   "worktree_state": args.worktree_state, "task_state": args.task_state,
                   "pending_tests": args.pending_test, "next_safe_action": args.next_safe_action}
    else:
        if not args.checkpoint_id:
            response = _error(request_id, "invalid_arguments", "--checkpoint-id is required")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print("Ternuxx operation failed [invalid_arguments]: --checkpoint-id is required", file=sys.stderr)
            return 1
        payload = {"checkpoint_id": args.checkpoint_id}
    response = dispatch({"api_version": API_VERSION, "request_id": request_id, "operation": args.operation, "args": payload})
    if args.json:
        print(json.dumps(response, sort_keys=True))
    elif response["ok"]:
        print(json.dumps(response["data"], indent=2, sort_keys=True))
    else:
        error = response["error"]
        assert isinstance(error, dict)
        print(f"Ternuxx operation failed [{error['code']}]: {error['message']}", file=sys.stderr)
    return 0 if response["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
