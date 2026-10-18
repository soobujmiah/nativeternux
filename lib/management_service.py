#!/usr/bin/env python3
"""Versioned, local application-service boundary for Ternuxx CLI operations.

This is an in-process/local CLI backend, not an HTTP server. It deliberately
accepts a narrow operation allowlist and has no generic shell or file API.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid

import boot_profiles
import continuity
import config_recovery
import operation_journal
import reboot_recovery
import runtime_diagnostics
import ssh_diagnostics
import runit_service
import runit_deployment
import operation_recovery
import wakelock_manager
import proot_diagnostics
import remote_access_policy
import proot_shortcuts
import doctor_report
import management_catalog


API_VERSION = 1
OPERATIONS = {
    "management.catalog": {"args": set()},
    "doctor.report": {"args": {"graphics"}},
    "ssh.inspect": {"args": set()},
    "proot.status": {"args": set()},
    "proot.app.launch": {"args": {"app_id"}},
    "proot.shortcuts.list": {"args": set()},
    "proot.shortcuts.preview": {"args": {"action", "app_id"}},
    "proot.shortcuts.apply": {"args": {"action", "app_id", "confirmed", "plan_id"}},
    "proot.guest.verify": {"args": {"distro", "user", "user_source", "display", "backend"}},
    "remote.access.preview": {"args": {"policy"}},
    "ssh.service.start": {"args": {"confirmed", "plan_id"}},
    "ssh.service.stop": {"args": {"confirmed", "plan_id"}},
    "ssh.service.deploy": {"args": {"confirmed", "plan_id"}},
    "ssh.service.deploy.rollback.preview": {"args": {"operation_id"}},
    "ssh.service.deploy.rollback.apply": {"args": {"operation_id", "confirmed", "plan_id"}},
    "native.ssh.status": {"args": set()},
    "boot.status": {"args": set()},
    "boot.profile.status": {"args": set()},
    "boot.profile.preview": {"args": {"profile"}},
    "boot.enable": {"args": {"profile", "confirmed"}},
    "boot.disable": {"args": {"confirmed"}},
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

    process_env = os.environ if env is None else env
    if process_env.get("TERMUX_VERSION") is None or process_env.get("PREFIX") != "/data/data/com.termux/files/usr":
        return _error(request_id, "native_termux_required", "operation requires the native Termux shell")
    home = process_env.get("HOME", "")
    state_dir = process_env.get("TERNUXX_STATE_DIR", "")
    if not home or ((operation.startswith(("continuity.", "wakelock.", "boot.profile.", "backup.", "restore.", "recovery.rollback.", "recovery.service.", "recovery.resolve", "ssh.service."))) and not state_dir):
        return _error(request_id, "configuration_missing", "HOME and the native state directory must be configured")

    try:
        if operation == "management.catalog":
            data = management_catalog.build_catalog(set(OPERATIONS))
        elif operation == "doctor.report":
            graphics = args.get("graphics", False)
            if type(graphics) is not bool:
                return _error(request_id, "invalid_arguments", "graphics must be boolean")
            data = doctor_report.build_report(graphics, __import__("pathlib").Path(state_dir or home))
        elif operation == "remote.access.preview":
            data = remote_access_policy.preview(args["policy"]) if "policy" in args else remote_access_policy.preview()
        elif operation in {"ssh.inspect", "native.ssh.status"}:
            data = ssh_diagnostics.inspect_native(prefix=process_env["PREFIX"], home=home)
        elif operation == "proot.status":
            data = proot_diagnostics.inspect_installed()
        elif operation == "proot.app.launch":
            app_id = args.get("app_id")
            if not isinstance(app_id, str):
                return _error(request_id, "invalid_arguments", "app ID is required")
            data = proot_shortcuts.launch(
                app_id, prefix=process_env["PREFIX"],
                repo_root=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                env=process_env,
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
                    or not isinstance(source, str) or source not in {"explicit", "ternux-state"}
                    or (source == "explicit" and not isinstance(args.get("user"), str))
                    or (source == "ternux-state" and "user" in args)):
                return _error(request_id, "invalid_arguments", "PRoot guest verification requires a supported, unambiguous profile and display/backend selection")
            try:
                user = args.get("user")
                if source == "ternux-state":
                    user = proot_diagnostics.resolve_ternux_guest_user(
                        home=home, path=process_env.get("PATH", ""),
                    )
                data = proot_diagnostics.verify_ternux_guest(
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
        elif operation in {"ssh.service.start", "ssh.service.stop"}:
            confirmed = args.get("confirmed", False)
            plan_id = args.get("plan_id")
            if type(confirmed) is not bool or (plan_id is not None and not isinstance(plan_id, str)):
                return _error(request_id, "invalid_arguments", "service confirmation or plan ID is invalid")
            action = "start" if operation.endswith(".start") else "stop"
            data = runit_service.apply(
                action, prefix=process_env["PREFIX"], home=home, state_dir=state_dir,
                confirmed=confirmed, plan_id=plan_id,
            )
        elif operation == "boot.status":
            data = runtime_diagnostics.inspect_boot(home=home)
        elif operation == "boot.profile.status":
            data = boot_profiles.status(home=home, state_dir=state_dir,
                                        prefix=process_env["PREFIX"])
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
    except runit_deployment.DeploymentError as exc:
        return _error(request_id, "deployment_failed", str(exc))
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
    except (KeyError, TypeError, ValueError, OSError, RuntimeError) as exc:
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
    parser.add_argument("--guest-user-source", choices=("ternux-state",))
    parser.add_argument("--display", choices=tuple(f":{number}" for number in range(11)))
    parser.add_argument("--backend", choices=("zink", "virgl"))
    parser.add_argument("--policy-stdin", action="store_true",
                        help="read a secret-free remote-access desired policy JSON object from stdin")
    parser.add_argument("--current-boot-id")
    parser.add_argument("--owner")
    parser.add_argument("--profile", choices=boot_profiles.PROFILES)
    parser.add_argument("--name")
    parser.add_argument("--backup-id")
    parser.add_argument("--operation-id")
    parser.add_argument("--shortcut-action", choices=("add", "remove"))
    parser.add_argument("--app-id")
    parser.add_argument("--plan-id")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--persistent", action="store_true")
    parser.add_argument("--graphics", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


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
        state_user = args.guest_user_source == "ternux-state"
        if (not all((args.distro, args.display, args.backend))
                or explicit_user == state_user):
            response = _error(request_id, "invalid_arguments", "proot guest verify requires exactly one of --guest-user USER or --guest-user-source ternux-state")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print(f"Ternuxx operation failed [{response['error']['code']}]: {response['error']['message']}", file=sys.stderr)
            return 1
        payload = {"distro": args.distro, "display": args.display, "backend": args.backend}
        if explicit_user:
            payload["user"] = args.guest_user
        else:
            payload["user_source"] = "ternux-state"
    elif args.operation in {"management.catalog", "ssh.inspect", "proot.status", "native.ssh.status", "boot.status", "wakelock.status", "continuity.status", "boot.profile.status", "backup.list", "recovery.status"}:
        payload = {}
        if args.operation == "continuity.status" and args.test_id:
            payload["test_id"] = args.test_id
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
    elif args.operation in {"ssh.service.start", "ssh.service.stop", "ssh.service.deploy"}:
        if args.yes != bool(args.plan_id):
            response = _error(request_id, "invalid_arguments", "service apply requires --yes and --plan-id from its exact preview")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print(f"Ternuxx operation failed [{response['error']['code']}]: {response['error']['message']}", file=sys.stderr)
            return 1
        payload = {"confirmed": args.yes, "plan_id": args.plan_id}
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
        if not args.app_id or args.shortcut_action or args.yes or args.plan_id:
            response = _error(request_id, "invalid_arguments", "--app-id is required for a PRoot app launch")
            if args.json:
                print(json.dumps(response, sort_keys=True))
            else:
                print("Ternuxx operation failed [invalid_arguments]: --app-id is required", file=sys.stderr)
            return 1
        payload = {"app_id": args.app_id}
    elif args.operation == "proot.shortcuts.list":
        if args.shortcut_action or args.app_id or args.yes or args.plan_id:
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
    elif args.operation == "ssh.inspect":
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
