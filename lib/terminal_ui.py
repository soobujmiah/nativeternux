#!/usr/bin/env python3
"""Keyboard-first categorized client for the shared Ternuxx management service."""
from __future__ import annotations

import curses
import json
import os
from pathlib import Path
from pathlib import Path
import re
import stat
import sys
import textwrap
import uuid
from typing import Any

import management_service
import management_sessions
import management_presentation
import proot_shortcuts
import terminal_broker
import terminal_cli


BRANDING_TAGLINE = "Workstation in your pocket — by Sobuj Miah"
BRANDING_URL = "soobujmiah.github.io"


READ_WITHOUT_ARGUMENTS = {
    op for op, spec in management_service.OPERATIONS.items()
    if not spec["args"] and op in management_sessions.READ_ONLY_OPERATIONS
}


def _call(operation: str, args: dict[str, object] | None = None) -> dict[str, object]:
    request = {"api_version": management_service.API_VERSION, "request_id": uuid.uuid4().hex,
               "operation": operation, "args": args or {}}
    return management_service.dispatch(request, caller="local_cli", env=dict(os.environ))


def _prompt(screen: "curses._CursesWindow", label: str, limit: int = 2048) -> str:
    height, width = screen.getmaxyx()
    screen.erase()
    screen.addnstr(0, 0, label, max(width - 1, 0))
    screen.addnstr(2, 0, "Enter=submit  Esc=cancel", max(width - 1, 0))
    screen.move(1, 0)
    curses.echo()
    try:
        value = screen.getstr(1, 0, min(limit, max(width - 1, 1)))
    except curses.error:
        value = b""
    finally:
        curses.noecho()
    return value.decode("utf-8", errors="replace").strip()


def _choose(screen: "curses._CursesWindow", title: str, options: list[tuple[str, str]]) -> str:
    """Compact keyboard menu: arrows or number, Enter selects, Esc cancels."""
    if not options:
        return ""
    index = offset = 0
    while True:
        screen.erase()
        height, width = screen.getmaxyx()
        if height < 4 or width < 4:
            return ""
        visible = min(len(options), height - 3)
        offset = min(offset, max(0, len(options) - visible))
        if index < offset:
            offset = index
        elif index >= offset + visible:
            offset = index - visible + 1
        screen.addnstr(0, 0, title, width - 1)
        for row, item_index in enumerate(range(offset, offset + visible), 2):
            _value, label = options[item_index]
            marker = ">" if item_index == index else " "
            screen.addnstr(row, 0, f"{marker} {item_index + 1}. {label}", width - 1)
        screen.addnstr(height - 1, 0, "↑/↓ move · 1–9 shortcut · Enter choose · Esc cancel", width - 1)
        screen.refresh()
        key = screen.getch()
        if key in (27, ord("q"), ord("Q")):
            return ""
        if key in (curses.KEY_UP, ord("k")):
            index = (index - 1) % len(options)
        elif key in (curses.KEY_DOWN, ord("j")):
            index = (index + 1) % len(options)
        elif key in (curses.KEY_ENTER, 10, 13):
            return options[index][0]
        elif ord("1") <= key <= ord("9") and key - ord("1") < len(options):
            return options[key - ord("1")][0]


def _launch_proot_app(screen: "curses._CursesWindow") -> dict[str, object] | None:
    inventory = _call("proot.shortcuts.list")
    if not inventory.get("ok"):
        return inventory
    data = inventory.get("data", {})
    static_items = data.get("items", []) if isinstance(data, dict) else []
    desktop_catalog = data.get("desktop_applications", {}) if isinstance(data, dict) else {}
    dynamic_items = desktop_catalog.get("items", []) if isinstance(desktop_catalog, dict) else []
    options: list[tuple[str, str]] = []
    names: dict[str, str] = {}
    for item in static_items:
        if not isinstance(item, dict) or item.get("id") not in proot_shortcuts.CATALOG:
            continue
        app_id = item["id"]
        names["app:" + app_id] = str(item.get("name") or proot_shortcuts.CATALOG[app_id]["name"])
        options.append(("app:" + app_id, names["app:" + app_id] + " · shortcut " + str(item.get("shortcut_state", "unknown"))))
    for item in dynamic_items:
        if not isinstance(item, dict) or item.get("status") != "available":
            continue
        desktop_id = item.get("desktop_id")
        if not isinstance(desktop_id, str):
            continue
        key = "desktop:" + desktop_id
        names[key] = str(item.get("name") or desktop_id)
        options.append((key, names[key] + " · Debian app · shortcut " + str(item.get("shortcut_state", "unknown"))))
    selected = _choose(screen, "Choose a PRoot app", options)
    if not selected or selected not in names:
        return {"ok": False, "error": {"code": "cancelled" if not selected else "unknown_proot_app"}}
    display = _prompt(screen, "Native Ternuxx X11 display (blank=verified session default)")
    if display and not re.fullmatch(r":[0-9]{1,2}", display):
        return {"ok": False, "error": {"code": "invalid_display"}}
    name = names[selected]
    target = "Native Ternuxx display" + (f" {display}" if display else "")
    if _prompt(screen, f"Launch {name} through PRoot in {target}? type yes").lower() != "yes":
        return {"ok": False, "error": {"code": "cancelled"}}
    args: dict[str, object] = {"app_id": selected[4:]} if selected.startswith("app:") else {
        "desktop_id": selected[8:]}
    if display:
        args["display"] = display
    return _call("proot.app.launch", args)


def _manage_proot_shortcut(screen: "curses._CursesWindow") -> dict[str, object]:
    inventory = _call("proot.shortcuts.list")
    if not inventory.get("ok"):
        return inventory
    data = inventory.get("data", {})
    items = data.get("items", []) if isinstance(data, dict) else []
    options = [(item["id"], f"{item.get('name', item['id'])} · {item.get('shortcut_state', 'unknown')}")
               for item in items if isinstance(item, dict) and item.get("id") in proot_shortcuts.CATALOG]
    dynamic = data.get("desktop_applications", {}) if isinstance(data, dict) else {}
    for item in dynamic.get("items", []) if isinstance(dynamic, dict) else []:
        if item.get("status") == "available" and isinstance(item.get("desktop_id"), str):
            options.append(("desktop:" + item["desktop_id"],
                            f"{item.get('name', item['desktop_id'])} · {item.get('shortcut_state', 'unknown')} · Debian app"))
    action = _choose(screen, "Shortcut action", [("add", "Add shortcut"), ("remove", "Remove owned shortcut")])
    if action not in {"add", "remove"}:
        return {"ok": False, "error": {"code": "cancelled"}}
    app_id = _choose(screen, "Choose a named PRoot app shortcut", options)
    if not app_id:
        return {"ok": False, "error": {"code": "cancelled"}}
    dynamic_app = app_id.startswith("desktop:")
    target_args = {"desktop_id": app_id[8:]} if dynamic_app else {"app_id": app_id}
    app_name = next((label.split(" · ", 1)[0] for value, label in options if value == app_id), app_id)
    preview = _call("proot.shortcuts.preview", {"action": action, **target_args})
    if not preview.get("ok"):
        return preview
    plan = preview.get("data", {})
    if not isinstance(plan, dict):
        return {"ok": False, "error": {"code": "invalid_shortcut_preview"}}
    if not plan.get("changed"):
        return preview
    plan_id = plan.get("plan_id")
    if not isinstance(plan_id, str):
        return {"ok": False, "error": {"code": "invalid_shortcut_preview"}}
    affected = plan.get("affected_resources") or []
    target = affected[0].get("path", "the selected launcher") if affected and isinstance(affected[0], dict) else "the selected launcher"
    before = affected[0].get("before", "unknown") if affected and isinstance(affected[0], dict) else "unknown"
    after = affected[0].get("after", "unknown") if affected and isinstance(affected[0], dict) else "unknown"
    confirm = _prompt(screen, f"{action.title()} {app_name} at {target} ({before} → {after}). Type yes")
    if confirm.lower() != "yes":
        return {"ok": False, "error": {"code": "cancelled"}}
    return _call("proot.shortcuts.apply", {
        "action": action, **target_args, "confirmed": True, "plan_id": plan_id,
    })


def _manage_proot_shortcut_sync(screen: "curses._CursesWindow") -> dict[str, object]:
    preview = _call("proot.shortcuts.sync.preview")
    if not preview.get("ok"):
        return preview
    plan = preview.get("data", {})
    if not isinstance(plan, dict):
        return {"ok": False, "error": {"code": "invalid_shortcut_sync_preview"}}
    if not plan.get("changed"):
        return preview
    plan_id = plan.get("plan_id")
    if not isinstance(plan_id, str):
        return {"ok": False, "error": {"code": "invalid_shortcut_sync_preview"}}
    changes = plan.get("changes", [])
    summary = "; ".join(f"{item.get('action')} {item.get('path')}"
                        for item in changes if isinstance(item, dict))
    confirm = _prompt(screen, f"Sync discovered PRoot apps ({plan.get('discovered', 0)} apps): {summary}. Type yes")
    if confirm.lower() != "yes":
        return {"ok": False, "error": {"code": "cancelled"}}
    return _call("proot.shortcuts.sync.apply", {"confirmed": True, "plan_id": plan_id})

def _manage_proot_shortcut_rollback(screen: "curses._CursesWindow") -> dict[str, object]:
    """Select a saved bulk sync, review its exact paths, then confirm restore."""
    inventory = _call("proot.shortcuts.sync.rollback.list")
    if not inventory.get("ok"):
        return inventory
    data = inventory.get("data", {})
    rows = data.get("rollbacks", []) if isinstance(data, dict) else []
    eligible = [item for item in rows if isinstance(item, dict)
                and item.get("integrity") == "valid" and item.get("status") == "applied"
                and isinstance(item.get("rollback_id"), str)]
    options = [(item["rollback_id"],
                f"{item.get('created_at', 'Saved sync')} · {item.get('entry_count', 0)} changes")
               for item in eligible]
    rollback_id = _choose(screen, "Saved PRoot shortcut syncs", options)
    if not rollback_id:
        return {"ok": False, "error": {"code": "cancelled"}}
    preview = _call("proot.shortcuts.sync.rollback.preview", {"rollback_id": rollback_id})
    if not preview.get("ok"):
        return preview
    plan = preview.get("data", {})
    if not isinstance(plan, dict) or not isinstance(plan.get("plan_id"), str):
        return {"ok": False, "error": {"code": "invalid_rollback_preview"}}
    changes = plan.get("changes", [])
    summary = "; ".join(
        f"{item.get('action')} {item.get('path')}" for item in changes if isinstance(item, dict))
    confirmation = _prompt(
        screen, f"Restore this PRoot menu state: {summary}. Type yes")
    if confirmation.lower() != "yes":
        return {"ok": False, "error": {"code": "cancelled"}}
    return _call("proot.shortcuts.sync.rollback.apply", {
        "rollback_id": rollback_id, "confirmed": True, "plan_id": plan["plan_id"],
    })


def _select_session(screen, title, sessions):
    options = []
    for item in sessions:
        session_id = item.get("session_id")
        if not isinstance(session_id, str) or not re.fullmatch(r"proot-[0-9a-f]{32}", session_id):
            continue
        name = "Interactive Debian" if item.get("profile") == "debian-interactive" else "Diagnostic probe"
        state = str(item.get("state", "unknown")).replace("_", " ")
        options.append((session_id, f"{name} · {state} · {session_id[-8:]}"))
    return _choose(screen, title, options)


def _attached_terminal(screen, client, *, session_id=None, plan_id=None):
    """Restore curses after the shared terminal relay, including failures."""
    curses.def_prog_mode()
    curses.endwin()
    try:
        lease = None
        if plan_id is not None:
            started = terminal_cli._ok(client.request("terminal.start", args={
                "confirmed": True, "plan_id": plan_id}))
            lease = started.get("result")
            if not isinstance(lease, dict):
                return {"ok": False, "error": {"code": "invalid_terminal_start"}}
            session_id = lease.get("session_id")
        if not isinstance(session_id, str) or not re.fullmatch(r"proot-[0-9a-f]{32}", session_id):
            return {"ok": False, "error": {"code": "invalid_terminal_session"}}
        terminal_cli.attach(session_id, client=client, lease=lease)
        return {"ok": True, "data": {"session_id": session_id, "state": "detached_or_closed"}}
    except (OSError, terminal_broker.BrokerError) as exc:
        return {"ok": False, "error": {"code": "terminal_attach_failed", "detail": str(exc)}}
    finally:
        curses.reset_prog_mode()
        screen.clear()
        screen.refresh()


def _manage_replay_guest(screen: "curses._CursesWindow") -> dict[str, object]:
    action = _choose(screen, "Ternuxx replay guest", [
        ("retire", "Retire an idle replay guest (keeps exact backup)"),
        ("restore", "Restore a retired replay guest"),
    ])
    alias = _prompt(screen, "Exact alias (ternuxx-replay-NAME)")
    if not re.fullmatch(r"ternuxx-replay-[a-z0-9][a-z0-9-]{0,31}", alias):
        return {"ok": False, "error": {"code": "invalid_replay_alias"}}
    backup_id = ""
    if action == "retire":
        preview = _call("proot.setup.retire.preview", {"alias": alias})
    elif action == "restore":
        backup_id = _prompt(screen, "Backup ID (32 lowercase hex characters)", 32)
        if not re.fullmatch(r"[0-9a-f]{32}", backup_id):
            return {"ok": False, "error": {"code": "invalid_backup_id"}}
        preview = _call("proot.setup.restore.preview", {"alias": alias, "backup_id": backup_id})
    else:
        return {"ok": False, "error": {"code": "cancelled"}}
    if not preview.get("ok"):
        return preview
    plan = preview.get("data", {})
    plan_id = plan.get("plan_id") if isinstance(plan, dict) else None
    if not isinstance(plan_id, str) or not re.fullmatch(r"[0-9a-f]{64}", plan_id):
        return {"ok": False, "error": {"code": "invalid_guest_lifecycle_preview"}}
    _show_details(screen, preview)
    if _prompt(screen, "Apply this exact guest change? Type yes").lower() != "yes":
        return {"ok": False, "error": {"code": "cancelled"}}
    if action == "retire":
        return _call("proot.setup.retire.apply", {"alias": alias, "confirmed": True, "plan_id": plan_id})
    return _call("proot.setup.restore.apply", {"alias": alias, "backup_id": backup_id,
                                                "confirmed": True, "plan_id": plan_id})


def _manage_proot_sessions(screen: "curses._CursesWindow") -> dict[str, object]:
    """Manage fixed Ternuxx PRoot sessions through the shared typed service."""
    listed = _call("proot.sessions.list")
    if not listed.get("ok"):
        return listed
    data = listed.get("data", {})
    sessions = data.get("sessions", []) if isinstance(data, dict) else []
    if not isinstance(sessions, list):
        return {"ok": False, "error": {"code": "invalid_session_inventory"}}
    choice = _choose(screen, "Debian sessions", [
        ("status", "View session status"), ("recovery", "Inspect session recovery"),
        ("start-probe", "Start a bounded diagnostic probe"),
        ("start-login", "Start an interactive terminal"),
        ("attach", "Attach to an existing terminal"), ("stop", "Close a managed session"),
        ("guest-lifecycle", "Retire or restore a Ternuxx replay guest"),
    ])
    if choice in {"status", "list"}:
        return listed
    if choice == "recovery":
        session_id = _select_session(screen, "Inspect recovery", [x for x in sessions if isinstance(x, dict)])
        if not session_id:
            return {"ok": False, "error": {"code": "cancelled"}}
        return _call("proot.recovery.inspect", {"session_id": session_id})
    if choice == "start-probe":
        preview = _call("proot.start.preview", {"profile": "isolated-probe"})
        if not preview.get("ok"):
            return preview
        plan = preview.get("data", {})
        plan_id = plan.get("plan_id") if isinstance(plan, dict) else None
        if not isinstance(plan_id, str) or not re.fullmatch(r"plan-[0-9a-f]{64}", plan_id):
            return {"ok": False, "error": {"code": "invalid_session_preview"}}
        impact = str(plan.get("impact", "Starts one bounded headless Debian diagnostic process."))
        if _prompt(screen, f"Impact: {impact} Fixed sleep only; no GUI or package changes. Type yes").lower() != "yes":
            return {"ok": False, "error": {"code": "cancelled"}}
        return _call("proot.start", {"profile": "isolated-probe", "confirmed": True,
                                      "plan_id": plan_id, "timeout_seconds": 300})
    if choice == "start-login":
        client = terminal_cli._client()
        try:
            response = terminal_cli._ok(client.request("terminal.start.preview"))
        except (OSError, terminal_broker.BrokerError):
            return {"ok": False, "error": {"code": "terminal_broker_unavailable"}}
        plan = response.get("plan", {})
        plan_id = plan.get("plan_id") if isinstance(plan, dict) else None
        if (not isinstance(plan, dict) or plan.get("profile") != "debian-interactive"
                or plan.get("mode") != "foreground-tty"
                or not isinstance(plan_id, str) or not re.fullmatch(r"plan-[0-9a-f]{64}", plan_id)):
            return {"ok": False, "error": {"code": "invalid_session_preview"}}
        _show_details(screen, {"ok": True, "data": plan})
        if _prompt(screen, "Start the interactive Debian terminal shown in this plan? Type yes").lower() != "yes":
            return {"ok": False, "error": {"code": "cancelled"}}
        return _attached_terminal(screen, client, plan_id=plan_id)
    if choice == "attach":
        candidates = [item for item in sessions if isinstance(item, dict)
                      and item.get("ownership") == "ternuxx_verified"
                      and item.get("state") == "running"
                      and item.get("profile") == "debian-interactive"]
        if not candidates:
            return {"ok": False, "error": {"code": "no_verified_terminal_session"}}
        client = terminal_cli._client()
        try:
            status = terminal_cli._ok(client.request("broker.status"))
        except (OSError, terminal_broker.BrokerError):
            return {"ok": False, "error": {"code": "terminal_broker_unavailable"}}
        if status.get("pty_relay") != "running":
            return {"ok": False, "error": {"code": "terminal_not_attachable"}}
        session_id = _select_session(screen, "Attach to a managed terminal", candidates)
        if not any(item.get("session_id") == session_id for item in candidates):
            return {"ok": False, "error": {"code": "cancelled"}}
        return _attached_terminal(screen, client, session_id=session_id)
    if choice == "stop":
        candidates = [item for item in sessions if isinstance(item, dict)
                      and item.get("ownership") == "ternuxx_verified"
                      and item.get("state") in {"running", "stopping"}]
        if not candidates:
            return {"ok": False, "error": {"code": "no_verified_live_session"}}
        session_id = _select_session(screen, "Close a managed session", candidates)
        if not any(item.get("session_id") == session_id for item in candidates):
            return {"ok": False, "error": {"code": "session_not_in_verified_inventory"}}
        preview = _call("proot.stop.preview", {"session_id": session_id})
        if not preview.get("ok"):
            return preview
        plan = preview.get("data", {})
        plan_id = plan.get("plan_id") if isinstance(plan, dict) else None
        if (not isinstance(plan, dict) or plan.get("ownership") != "ternuxx_verified"
                or not isinstance(plan_id, str) or not re.fullmatch(r"plan-[0-9a-f]{64}", plan_id)):
            return {"ok": False, "error": {"code": "session_stop_not_verified"}}
        _show_details(screen, preview)
        if _prompt(screen, "Close only the managed session shown in this plan? Type yes").lower() != "yes":
            return {"ok": False, "error": {"code": "cancelled"}}
        return _call("proot.stop", {"session_id": session_id, "confirmed": True, "plan_id": plan_id})
    return {"ok": False, "error": {"code": "cancelled"}}


def _desktop_action(screen: "curses._CursesWindow", resource: dict[str, Any]) -> dict[str, object]:
    allowed = resource.get("supported_operations", [])
    action = _choose(screen, "Native desktop", [(name, f"{name.title()} desktop") for name in ("start", "stop")
                      if f"desktop.{name}" in allowed])
    operation = {"start": "desktop.start", "stop": "desktop.stop"}.get(action)
    if not operation or operation not in resource.get("supported_operations", []):
        return {"ok": False, "error": {"code": "action_unavailable"}}
    if _prompt(screen, f"Confirm {action} native desktop? type yes").lower() != "yes":
        return {"ok": False, "error": {"code": "cancelled"}}
    return _call(operation)


def _public_key_catalog() -> list[dict[str, str]]:
    ssh_dir = Path.home() / ".ssh"
    try:
        metadata = ssh_dir.lstat()
        if ssh_dir.is_symlink() or not ssh_dir.is_dir() or metadata.st_uid != os.getuid():
            return []
        candidates = sorted(ssh_dir.glob("*.pub"), key=lambda item: item.name.casefold())[:64]
    except OSError:
        return []
    found: list[dict[str, str]] = []
    for path in candidates:
        try:
            item = path.lstat()
            if path.is_symlink() or not path.is_file() or item.st_uid != os.getuid() or item.st_size > 16_384:
                continue
            fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) |
                         getattr(os, "O_CLOEXEC", 0))
            try:
                opened = os.fstat(fd)
                if (not stat.S_ISREG(opened.st_mode) or opened.st_ino != item.st_ino
                        or opened.st_dev != item.st_dev or opened.st_uid != os.getuid()
                        or opened.st_size > 16_384):
                    continue
                with os.fdopen(fd, "rb", closefd=False) as stream:
                    content = stream.read(16_385)
            finally:
                os.close(fd)
            if len(content) > 16_384:
                continue
            raw = content.decode("utf-8").splitlines()
            if len(raw) != 1:
                continue
            parsed = management_service.ssh_key_inventory._parse_line(raw[0])
            if parsed and parsed.get("status") == "valid":
                found.append({"name": path.name, "public_key": raw[0],
                              "fingerprint": parsed["fingerprint"], "key_type": parsed["key_type"]})
        except (OSError, UnicodeError):
            continue
    return found


def _wakelock_action(screen: "curses._CursesWindow") -> dict[str, object]:
    choice = _choose(screen, "Wake Lock", [
        ("status", "Check current Wake Lock status"),
        ("ssh-policy", "Set managed SSH keep-awake preference"),
    ])
    if choice != "ssh-policy":
        return _call("wakelock.status")
    current = _call("wakelock.ssh-policy.status")
    if not current.get("ok"):
        return current
    enabled = current.get("data", {}).get("persistent_lease_enabled") is True
    answer = _prompt(screen, "Keep managed SSH awake across idle? Current: "
                     + ("Yes" if enabled else "No") + "; enter yes or no").lower()
    if answer not in {"yes", "no"}:
        return {"ok": False, "error": {"code": "cancelled"}}
    desired = answer == "yes"
    preview = _call("wakelock.ssh-policy.preview", {"enabled": desired})
    if not preview.get("ok") or not preview.get("data", {}).get("changed"):
        return preview
    _show_details(screen, preview)
    if _prompt(screen, "This applies at the next managed SSH start; current lease stays unchanged. Type yes").lower() != "yes":
        return {"ok": False, "error": {"code": "cancelled"}}
    return _call("wakelock.ssh-policy.apply", {"enabled": desired, "confirmed": True,
                                                  "plan_id": preview.get("data", {}).get("plan_id")})


def _managed_ssh_action(screen: "curses._CursesWindow", resource: dict[str, Any]) -> dict[str, object]:
    if resource.get("id") != "network.ssh.managed-8023":
        return {"ok": False, "error": {"code": "externally_managed_resource"}}
    operations = set(resource.get("supported_operations", []))
    choices = [(name, f"{name.title()} SSH service") for name in ("start", "stop", "restart")
               if f"ssh.service.{name}" in operations]
    if "ssh.client-key.create.preview" in operations:
        choices.append(("generate", "Create a Native SSH recovery key"))
    if "ssh.service.autostart.status" in operations:
        choices.append(("autostart", "Change SSH start-with-Termux-services setting"))
    if "ssh.keys.list" in operations:
        choices.append(("keys", "View shared SSH key fingerprints"))
    if "ssh.keys.add.preview" in operations:
        choices.append(("enroll", "Enroll a public key from Native .ssh"))
    if "ssh.keys.remove.preview" in operations:
        choices.append(("revoke", "Remove an authorized key"))
    if "ssh.keys.rollback.list" in operations:
        choices.append(("rollback", "Restore a previous SSH key change"))
    action = _choose(screen, "Managed SSH · port 8023", choices)
    if action == "keys":
        return _call("ssh.keys.list")
    if action == "rollback":
        listed = _call("ssh.keys.rollback.list")
        if not listed.get("ok"):
            return listed
        entries = listed.get("data", {}).get("entries", [])
        eligible = [entry for entry in entries if isinstance(entry, dict)]
        if not eligible:
            _show_details(screen, {"message": "No saved SSH key changes are available to restore."})
            return listed
        selected = _choose(screen, "Select an SSH key change to restore",
            [(str(i), f"{entry.get('action', 'change').title()} - {entry.get('fingerprint', '')} - {entry.get('status', '')}")
             for i, entry in enumerate(eligible)])
        if not isinstance(selected, str) or not selected.isdigit() or int(selected) >= len(eligible):
            return {"ok": False, "error": {"code": "cancelled"}}
        rollback_id = eligible[int(selected)].get("rollback_id")
        preview = _call("ssh.keys.rollback.preview", {"rollback_id": rollback_id})
        if not preview.get("ok"):
            return preview
        plan = preview.get("data", {})
        _show_details(screen, plan)
        if not plan.get("can_restore"):
            return preview
        confirm = _prompt(screen, "Restore exact previous SSH access for shared ports 8022 and 8023? Type yes")
        if confirm.lower() != "yes":
            return {"ok": False, "error": {"code": "cancelled"}}
        result = _call("ssh.keys.rollback.apply", {"rollback_id": rollback_id,
            "confirmed": True, "plan_id": plan.get("plan_id")})
        if result.get("ok"):
            _call("ssh.keys.list")
        return result
    if action == "autostart":
        current = _call("ssh.service.autostart.status")
        if not current.get("ok"):
            return current
        enabled = current.get("data", {}).get("enabled") is True
        requested = _prompt(screen, "Start SSH automatically with Termux services? Current: "
                             + ("Yes" if enabled else "No") + "; enter yes or no").lower()
        if requested not in {"yes", "no"}:
            return {"ok": False, "error": {"code": "cancelled"}}
        desired = requested == "yes"
        preview = _call("ssh.service.autostart.preview", {"enabled": desired})
        if not preview.get("ok") or not preview.get("data", {}).get("changed"):
            return preview
        _show_details(screen, preview)
        if _prompt(screen, "This changes next-supervisor startup only; current sshd stays as-is. Type yes").lower() != "yes":
            return {"ok": False, "error": {"code": "cancelled"}}
        return _call("ssh.service.autostart.apply", {"enabled": desired, "confirmed": True,
                                                       "plan_id": preview.get("data", {}).get("plan_id")})
    if action == "generate":
        name = _prompt(screen, "Recovery key name (lowercase, numbers, hyphen, underscore)")
        preview = _call("ssh.client-key.create.preview", {"name": name})
        if not preview.get("ok"):
            return preview
        plan = preview.get("data", {})
        if not isinstance(plan, dict) or not plan.get("changed"):
            return preview
        _show_details(screen, plan)
        if _prompt(screen, "Private file is stored without passphrase, mode 0600. Type yes to create").lower() != "yes":
            return {"ok": False, "error": {"code": "cancelled"}}
        created = _call("ssh.client-key.create.apply", {
            "name": name, "confirmed": True, "plan_id": plan.get("plan_id")})
        if not created.get("ok"):
            return created
        data = created.get("data", {})
        public_key = data.get("public_key") if isinstance(data, dict) else None
        if not isinstance(public_key, str):
            return created
        key_preview = _call("ssh.keys.add.preview", {"public_key": public_key})
        if not key_preview.get("ok"):
            return {"ok": True, "data": {"key": data, "enrollment": key_preview}}
        key_plan = key_preview.get("data", {})
        if not isinstance(key_plan, dict) or not key_plan.get("changed"):
            return {"ok": True, "data": {"key": data, "enrollment": key_preview}}
        _show_details(screen, key_plan)
        if _prompt(screen, "Enroll this public key for both 8022 and 8023? Type yes").lower() != "yes":
            return {"ok": True, "data": {"key": data, "enrollment": "not enrolled"}}
        enrolled = _call("ssh.keys.add.apply", {"public_key": public_key,
            "confirmed": True, "plan_id": key_plan.get("plan_id")})
        if enrolled.get("ok"):
            _call("ssh.keys.list")
        return {"ok": bool(enrolled.get("ok")), "data": {"key": data, "enrollment": enrolled}}
    if action in {"enroll", "revoke"}:
        if action == "enroll":
            keys = _public_key_catalog()
            selected = _choose(screen, "Select a Native public key",
                [(str(i), f"{item['name']} · {item['key_type']} · {item['fingerprint']}")
                 for i, item in enumerate(keys)])
            if not selected.isdigit() or int(selected) >= len(keys):
                return {"ok": False, "error": {"code": "cancelled"}}
            key = keys[int(selected)]
            operation = "ssh.keys.add.preview"
            args: dict[str, object] = {"public_key": key["public_key"]}
            title = f"Enroll {key['name']} ({key['fingerprint']})"
        else:
            listed = _call("ssh.keys.list")
            inventory = listed.get("data", {}) if listed.get("ok") else {}
            keys = inventory.get("keys", []) if isinstance(inventory, dict) else []
            selected = _choose(screen, "Select a shared authorized key",
                [(str(i), f"{item.get('key_type')} · {item.get('fingerprint')} · {item.get('label')}")
                 for i, item in enumerate(keys) if isinstance(item, dict)])
            if not selected.isdigit() or int(selected) >= len(keys):
                return {"ok": False, "error": {"code": "cancelled"}}
            key = keys[int(selected)]
            operation = "ssh.keys.remove.preview"
            args = {"fingerprint": key["fingerprint"]}
            title = f"Remove {key.get('key_type')} · {key['fingerprint']}"
        preview = _call(operation, args)
        if not preview.get("ok"):
            return preview
        plan = preview.get("data", {})
        if not isinstance(plan, dict) or not plan.get("changed"):
            return preview
        _show_details(screen, plan)
        confirm = _prompt(screen,
            f"{title}. Affects SSH 8022 and 8023. Type yes to confirm")
        if confirm.lower() != "yes":
            return {"ok": False, "error": {"code": "cancelled"}}
        apply_op = operation.replace(".preview", ".apply")
        args.update({"confirmed": True, "plan_id": plan.get("plan_id")})
        result = _call(apply_op, args)
        if result.get("ok"):
            _call("ssh.keys.list")
        return result
    operation = {"start": "ssh.service.start", "stop": "ssh.service.stop", "restart": "ssh.service.restart"}.get(action)
    if not operation or operation not in operations:
        return {"ok": False, "error": {"code": "action_unavailable"}}
    preview = _call(operation, {"confirmed": False, "plan_id": None})
    if not preview.get("ok"):
        return preview
    data = preview.get("data", {})
    if not isinstance(data, dict):
        return {"ok": False, "error": {"code": "invalid_service_preview"}}
    if not data.get("requires_confirmation"):
        return preview
    plan_id = data.get("plan_id")
    if not isinstance(plan_id, str):
        return {"ok": False, "error": {"code": "invalid_service_preview"}}
    impact = str(data.get("impact", "Only the Ternuxx-managed SSH service on 127.0.0.1:8023 will change."))
    confirm = _prompt(screen, f"Impact: {impact} 8022 manual SSH is excluded. Type yes to {action}").lower()
    if confirm != "yes":
        return {"ok": False, "error": {"code": "cancelled"}}
    return _call(operation, {"confirmed": True, "plan_id": plan_id})

def _edit_monitor_policy(screen: "curses._CursesWindow") -> dict[str, object] | None:
    current = _call("desktop.monitor.status")
    if not current.get("ok"):
        return current
    data = current.get("data", {})
    enabled = _prompt(screen, f"Monitoring enabled [{str(data.get('enabled', False)).lower()}]? y/n")
    if enabled.lower() not in {"y", "n"}:
        return None
    interval = _prompt(screen, f"Interval value in seconds/minutes/hours (current {data.get('interval_seconds', 300)} seconds)")
    unit = _prompt(screen, "Interval unit: seconds, minutes, or hours (blank=seconds)").lower() or "seconds"
    if not interval.isdecimal() or unit not in {"seconds", "minutes", "hours"}:
        return {"ok": False, "error": {"code": "invalid_interval", "message": "Enter a whole interval and a supported unit."}}
    seconds = int(interval) * {"seconds": 1, "minutes": 60, "hours": 3600}[unit]
    if not 30 <= seconds <= 86400:
        return {"ok": False, "error": {"code": "invalid_interval", "message": "Use 30 seconds to 24 hours."}}
    focus = _prompt(screen, f"Check Android Activity focus [{str(data.get('focus_check', False)).lower()}]? y/n")
    launch = _prompt(screen, f"Request Activity when background [{str(data.get('activity_launch', False)).lower()}]? y/n")
    if focus.lower() not in {"y", "n"} or launch.lower() not in {"y", "n"}:
        return None
    if _prompt(screen, "Save monitoring policy? type yes").lower() != "yes":
        return {"ok": False, "error": {"code": "cancelled"}}
    return _call("desktop.monitor.configure", {
        "enabled": enabled.lower() == "y", "interval_value": int(interval), "unit": unit,
        "focus_check": focus.lower() == "y", "activity_launch": launch.lower() == "y",
    })


def _resource_state(resource: dict[str, Any]) -> str:
    state = resource.get("state") or {}
    return management_presentation.status_label(state.get("current", "unknown"))


def _manage_logs(screen: "curses._CursesWindow") -> dict[str, object]:
    """Read a bounded exact-source log tail through the shared service."""
    inventory = _call("management.logs.list")
    if not inventory.get("ok"):
        return inventory
    sources = inventory.get("data", {}).get("sources", [])
    available = [item for item in sources if isinstance(item, dict) and item.get("status") == "available"]
    if not available:
        return {"ok": True, "operation": "management.logs.list",
                "data": {"sources": sources, "message": "No Ternuxx log files are present."}}
    choices = ", ".join(str(item.get("source_id")) for item in available)
    source_id = _prompt(screen, "Log source (" + choices + ")")
    if not any(item.get("source_id") == source_id for item in available):
        return {"ok": False, "error": {"code": "unknown_log_source"}}
    return _call("management.logs.read", {"source_id": source_id, "limit": 100})


def _boot_action(screen: "curses._CursesWindow") -> dict[str, object]:
    """Guide a preview-first Native Termux startup-profile change."""
    choice = _prompt(screen, "Startup: status, preview, enable, disable (blank cancels)").lower()
    if choice == "status":
        return _call("boot.profile.status")
    if choice == "preview":
        profile = _prompt(screen, "Profile: cli-only or native (PRoot/hybrid are not ready)").lower()
        if profile not in {"cli-only", "native"}:
            return {"ok": False, "error": {"code": "unsupported_boot_profile"}}
        return _call("boot.profile.preview", {"profile": profile})
    if choice == "enable":
        profile = _prompt(screen, "Enable at Termux boot: cli-only or native").lower()
        if profile not in {"cli-only", "native"}:
            return {"ok": False, "error": {"code": "unsupported_boot_profile"}}
        preview = _call("boot.profile.preview", {"profile": profile})
        if not preview.get("ok") or preview.get("data", {}).get("ready") is not True:
            return preview
        _show_details(screen, preview)
        if _prompt(screen, "Review the startup profile and enable it? type yes").lower() != "yes":
            return {"ok": False, "error": {"code": "cancelled"}}
        return _call("boot.enable", {"profile": profile, "confirmed": True})
    if choice == "disable":
        current = _call("boot.profile.status")
        if not current.get("ok"):
            return current
        _show_details(screen, current)
        if _prompt(screen, "Disable only the Ternuxx-managed startup profile? type yes").lower() != "yes":
            return {"ok": False, "error": {"code": "cancelled"}}
        return _call("boot.disable", {"confirmed": True})
    return {"ok": False, "error": {"code": "cancelled"}}


def _cron_scheduler_action(screen: "curses._CursesWindow") -> dict[str, object]:
    """Start or stop the Ternuxx scheduler only after an explicit review."""
    choice = _prompt(screen, "Cron service: status, start, stop (blank cancels)").lower()
    if choice == "status":
        return _call("cron.status")
    if choice == "start":
        raw_interval = _prompt(screen, "Check interval in seconds (1-60, default 5)") or "5"
        if not raw_interval.isdigit() or not 1 <= int(raw_interval) <= 60:
            return {"ok": False, "error": {"code": "invalid_poll_interval"}}
        interval = int(raw_interval)
        _show_details(screen, {"ok": True, "data": {
            "action": "Start the Ternuxx Cron scheduler", "interval_seconds": interval,
            "boot_start": "not enabled by this action",
        }})
        if _prompt(screen, "Start this Ternuxx service now? type yes").lower() != "yes":
            return {"ok": False, "error": {"code": "cancelled"}}
        return _call("cron.scheduler.start", {"poll_seconds": interval, "confirmed": True})
    if choice == "stop":
        _show_details(screen, {"ok": True, "data": {"action": "Stop only the Ternuxx Cron scheduler"}})
        if _prompt(screen, "Stop the Ternuxx Cron scheduler now? type yes").lower() != "yes":
            return {"ok": False, "error": {"code": "cancelled"}}
        return _call("cron.scheduler.stop", {"confirmed": True})
    return {"ok": False, "error": {"code": "cancelled"}}


def _available_action_labels(resource: dict[str, Any]) -> list[str]:
    """Describe only guided controls implemented by this TUI for this resource."""
    resource_id = resource.get("id")
    operations = set(resource.get("supported_operations", []))
    labels: list[str] = []
    if _selected_status_operation(resource):
        labels.append("check status")
    if resource_id == "native.system.health" and "management.logs.list" in operations:
        labels.append("view bounded Ternuxx logs")
    if resource_id == "native.desktop.session":
        labels.extend(name for op, name in (("desktop.start", "start desktop"),
                                            ("desktop.stop", "stop desktop")) if op in operations)
    elif resource_id in {"graphics.native", "graphics.debian"}:
        labels.extend(("check graphics status", "verify OpenGL", "verify GLES", "verify Vulkan"))
        if resource_id == "graphics.native" and "graphics.provider.select" in operations:
            labels.append("select Native backend")
    elif resource_id == "native.gui.activity-monitor":
        labels.append("configure monitoring policy")
    elif resource_id == "native.timezone" and "timezone.set" in operations:
        labels.append("configure Ternuxx timezone preference")
    elif resource_id == "proot.debian.workloads":
        labels.append("launch named PRoot app")
        labels.append("preview and manage PRoot app shortcut")
        labels.append("review and restore a saved PRoot app menu")
        labels.append("inspect, start attached login, or manage bounded PRoot sessions")
    elif resource_id == "network.ssh.managed-8023":
        labels.extend(name for op, name in (("ssh.service.start", "start SSH 8023 (preview)"),
                                            ("ssh.service.stop", "stop SSH 8023 (preview)"),
                                            ("ssh.service.restart", "restart SSH 8023 (preview)")) if op in operations)
        if "ssh.client-key.create.preview" in operations:
            labels.append("create and optionally enroll a Native SSH recovery key")
        if "ssh.keys.add.preview" in operations:
            labels.append("enroll a public key from Native .ssh")
        if "ssh.keys.remove.preview" in operations:
            labels.append("remove an authorized key by fingerprint")
        labels.append("public-key login only; password login is disabled")
        if "ssh.service.autostart.status" in operations:
            labels.append("change SSH start-with-Termux-services preference")
    elif resource_id == "native.wakelock":
        labels.append("inspect Ternuxx-owned Wake Lock leases")
        if {"wakelock.acquire", "wakelock.release"} <= operations:
            labels.append("lease controls require a workload-bound owner and are not exposed in this TUI")
    elif resource_id == "boot.termux.profile":
        labels.extend(name for op, name in (("boot.profile.status", "check startup profile"),
                                            ("boot.profile.preview", "preview startup profile"),
                                            ("boot.enable", "enable startup profile"),
                                            ("boot.disable", "disable startup profile")) if op in operations)
    elif resource_id == "recovery.native-state" and "recovery.status" in operations:
        labels.append("view operation history")
    elif resource_id == "automation.cron-registry":
        if {"cron.scheduler.start", "cron.scheduler.stop"} <= operations:
            labels.append("check, start, or stop Cron scheduler")
        if "cron.jobs.list" in operations:
            labels.append("list persisted job definitions")
        if {"cron.jobs.mutation.preview", "cron.jobs.mutation.apply"} <= operations:
            labels.append("preview and apply Cron job changes")
        if "cron.executions.list" in operations:
            labels.append("view Cron execution history")
    return labels


def _wrap_line(value: object, width: int) -> list[str]:
    return textwrap.wrap(str(value), max(1, width), break_long_words=True,
                         break_on_hyphens=False) or [""]


def _put_wrapped(screen: "curses._CursesWindow", row: int, col: int, value: object,
                 width: int, color: int | None = None) -> int:
    height, screen_width = screen.getmaxyx()
    lines = _wrap_line(value, min(width, max(1, screen_width - col - 1)))
    for line in lines:
        if row >= height:
            break
        if color is not None:
            screen.attron(curses.color_pair(color))
        screen.addnstr(row, col, line, max(0, screen_width - col - 1))
        if color is not None:
            screen.attroff(curses.color_pair(color))
        row += 1
    return row


def _put_fixed_line(screen: "curses._CursesWindow", row: int, col: int, value: object,
                    width: int, color: int | None = None) -> None:
    """Write a single clipped line so selection changes never move the list."""
    height, screen_width = screen.getmaxyx()
    if row < 0 or row >= height or col >= screen_width:
        return
    limit = max(0, min(width, screen_width - col - 1))
    text = str(value)
    if len(text) > limit:
        text = text[:max(0, limit - 1)] + ("…" if limit else "")
    if color is not None:
        screen.attron(curses.color_pair(color))
    screen.addnstr(row, col, text, limit)
    if color is not None:
        screen.attroff(curses.color_pair(color))


def _footer_layout(width: int) -> list[list[tuple[str, int]]]:
    limit = max(1, width - 2)
    groups = [
        ("←/→", "category", 2), ("↑/↓", "resource", 2), ("Enter", "status", 1),
        ("1–9/0", "jump", 2), ("PgUp/PgDn", "page", 2),
        ("H", "history", 3), ("v", "details", 4), ("a", "actions", 1),
        ("r", "refresh", 3), ("q", "quit", 6),
    ]
    rows: list[list[tuple[str, int]]] = [[]]
    used = 0
    for key, label, color in groups:
        pieces = _wrap_line(f"{key} {label}", limit)
        for piece in pieces:
            extra = len(piece) + (3 if rows[-1] else 0)
            if rows[-1] and used + extra > limit:
                rows.append([])
                used = 0
                extra = len(piece)
            if rows[-1]:
                rows[-1].append((" · ", 5))
                used += 3
            rows[-1].append((piece, color))
            used += len(piece)
    return rows


def _draw(screen: "curses._CursesWindow", categories: list[dict[str, Any]], category_index: int,
          resources: list[dict[str, Any]], selected: int, query: str,
          report: dict[str, object] | None, scroll: int = 0) -> int:
    screen.erase()
    height, width = screen.getmaxyx()
    content_width = max(1, width - 2)
    header = [
        ("Ternuxx Management Center", 1),
        (BRANDING_TAGLINE, 2),
        (BRANDING_URL, 4),
    ]
    row = 0
    for value, color in header:
        for line in _wrap_line(value, content_width):
            if row >= height:
                break
            col = max(0, (width - len(line)) // 2)
            screen.attron(curses.color_pair(color))
            screen.addnstr(row, col, line, max(0, width - col - 1))
            screen.attroff(curses.color_pair(color))
            row += 1
    category = categories[category_index] if categories else {"name": "Resources"}
    counts = {state: sum(1 for item in resources if item.get("status") == state)
              for state in ("implemented", "partial", "external", "unverified", "unavailable", "planned")}
    selected_resource = resources[selected] if resources and selected < len(resources) else None
    action_text = ", ".join(_available_action_labels(selected_resource)) if selected_resource else "none"

    def divider(at: int) -> int:
        if at < height:
            screen.attron(curses.color_pair(5))
            screen.addnstr(at, 1, "─" * content_width, max(0, width - 2))
            screen.attroff(curses.color_pair(5))
        return at + 1

    row = divider(row)
    row = _put_wrapped(screen, row, 1,
                       f"{category['name']}  ·  category {category_index + 1}/{len(categories)}  ·  {len(resources)} resources",
                       content_width, color=2)
    summary = (f"Available: {counts['implemented']} implemented · {counts['partial']} partial · "
               f"{counts['external']} external · {counts['planned']} planned")
    row = _put_wrapped(screen, row, 1, summary, content_width, color=3)
    row = _put_wrapped(screen, row, 1,
                       f"Search: {query or '—'}  ·  ←/→ category  / search  Enter status  H history  v details",
                       content_width, color=4)
    row = divider(row)
    _put_fixed_line(screen, row, 1, f"Actions · {action_text}", content_width, color=2)
    row += 1

    footer_rows = _footer_layout(width)
    footer_top = max(0, height - len(footer_rows))
    feedback_top = max(row, footer_top - 2)
    if report:
        error = report.get("error") if isinstance(report.get("error"), dict) else {}
        code = error.get("code")
        message = "Last action · " + ("Complete" if report.get("ok") else management_presentation.human_value(code or "failed"))
        formatted = management_presentation.format_report(report).splitlines()
        values = [line.strip() for line in formatted if line.strip() and not line.lstrip().startswith(("Ok:", "Error:"))][:2]
        _put_fixed_line(screen, feedback_top, 1, message, content_width,
                        color=6 if not report.get("ok") else 1)
        _put_fixed_line(screen, feedback_top + 1, 1, " · ".join(values), content_width, color=5)
    content_bottom = feedback_top

    item_lines = []
    for resource_index, resource in enumerate(resources, 1):
        status = management_presentation.status_label(resource.get("status", "unknown"))
        label = f"{resource_index:>2}. {resource.get('name', 'Resource')} · {status} · {_resource_state(resource)}"
        item_lines.append(_wrap_line(label, content_width))
    scroll = min(max(0, scroll), max(0, len(resources) - 1))
    while scroll < selected and sum(len(item_lines[index]) for index in range(scroll, selected + 1)) > max(0, content_bottom - row):
        scroll += 1
    cursor = row
    for index in range(scroll, len(resources)):
        lines = item_lines[index]
        if cursor + len(lines) > content_bottom:
            break
        resource = resources[index]
        state = resource.get("status", "unknown")
        color = 1 if state == "implemented" else (3 if state in ("partial", "external", "unverified") else 6)
        for line_index, line in enumerate(lines):
            shown = (">" if index == selected else " ") + line[1:] if line_index == 0 else line
            screen.attron(curses.color_pair(color))
            if index == selected:
                screen.attron(curses.A_REVERSE)
            screen.addnstr(cursor, 1, shown, max(0, width - 2))
            if index == selected:
                screen.attroff(curses.A_REVERSE)
            screen.attroff(curses.color_pair(color))
            cursor += 1
    if not resources and row < content_bottom:
        _put_wrapped(screen, row, 1, "No resources match this search.", content_width, color=5)
    if row >= content_bottom and height:
        _put_wrapped(screen, max(0, footer_top - 1), 1,
                     "Make the terminal wider or reduce zoom to see more.", content_width, color=3)

    for offset, segments in enumerate(footer_rows):
        footer_row = footer_top + offset
        col = 1
        for value, color in segments:
            if footer_row >= height:
                break
            screen.attron(curses.color_pair(color))
            screen.addnstr(footer_row, col, value, max(0, width - col - 1))
            screen.attroff(curses.color_pair(color))
            col += len(value)
    screen.refresh()
    return scroll


def _detail_lines(report: dict[str, object] | None, width: int) -> list[str]:
    if not report:
        return ["No operation details are available."]
    rendered = management_presentation.format_report(report)
    lines: list[str] = []
    for raw in rendered.splitlines():
        indent = len(raw) - len(raw.lstrip())
        prefix = " " * min(indent, max(0, width - 1))
        content = raw[indent:]
        lines.extend(textwrap.wrap(content, max(1, width - len(prefix)),
                                   subsequent_indent="") or [""])
        if prefix and lines:
            lines[-1] = prefix + lines[-1]
    return lines


def _show_details(screen: "curses._CursesWindow", report: dict[str, object] | None) -> None:
    offset = 0
    while True:
        screen.erase()
        height, width = screen.getmaxyx()
        title = " Operation details ".ljust(max(width - 1, 0))
        screen.attron(curses.color_pair(1))
        screen.addnstr(0, 0, title, max(width - 1, 0))
        screen.attroff(curses.color_pair(1))
        lines = _detail_lines(report, max(1, width - 3))
        page = max(1, height - 4)
        offset = min(max(0, offset), max(0, len(lines) - page))
        for row, line in enumerate(lines[offset:offset + page], 2):
            screen.addnstr(row, 1, line, max(0, width - 2))
        screen.addnstr(height - 1, 0, " ↑/↓ scroll · PgUp/PgDn · q back ".ljust(max(width - 1, 0)), max(width - 1, 0))
        screen.refresh()
        key = screen.getch()
        if key in (ord("q"), ord("Q"), 27):
            return
        if key in (curses.KEY_DOWN, ord("j")):
            offset += 1
        elif key in (curses.KEY_UP, ord("k")):
            offset -= 1
        elif key == curses.KEY_NPAGE:
            offset += page
        elif key == curses.KEY_PPAGE:
            offset -= page


def _cron_jobs() -> dict[str, object]:
    """Read persisted Cron definitions via the shared management service."""
    return _call("cron.jobs.list")


def _timezone_action(screen: "curses._CursesWindow") -> dict[str, object]:
    current = _call("timezone.status")
    if not current.get("ok"):
        return current
    current_zone = str(current.get("data", {}).get("timezone", "unknown"))
    zones = _call("timezone.list")
    if not zones.get("ok"):
        return zones
    available = zones.get("data", {}).get("timezones", [])
    selected = _prompt(screen, f"IANA timezone (current {current_zone}; available zones via tx mng timezone list)")
    if not selected:
        return {"ok": False, "error": {"code": "cancelled"}}
    if selected not in available:
        return {"ok": False, "error": {"code": "timezone_unavailable"}}
    if _prompt(screen, f"Set Ternuxx preference to {selected}? type yes").lower() != "yes":
        return {"ok": False, "error": {"code": "cancelled"}}
    return _call("timezone.set", {"timezone": selected})


def _cron_mutation(screen: "curses._CursesWindow") -> dict[str, object]:
    """Preview one typed Cron definition change, then apply that saved plan."""
    action = _prompt(screen, "Cron change: create, update, remove (blank cancels)").lower()
    if action not in {"create", "update", "remove"}:
        return {"ok": False, "error": {"code": "cancelled"}}
    if action == "create":
        name = _prompt(screen, "Job name")
        action_id = _prompt(screen, "Safe action ID: diagnostics.doctor, management.catalog.refresh, hermes.status, scheduler.self_test")
        expression = _prompt(screen, "Five-field cron expression (minute hour day month weekday)")
        if not name or action_id not in management_service.cron_registry._ALLOWED_ACTIONS or not expression:
            return {"ok": False, "error": {"code": "invalid_cron_input"}}
        timezone_name = management_service.timezone_support.current_timezone(
            os.environ.get("TERNUXX_STATE_DIR") or os.path.join(os.environ.get("HOME", ""), ".local/share/ternuxx"),
            installation_timezone=os.environ.get("TERNUXX_INSTALL_TIMEZONE"))
        try:
            job = management_service.cron_registry.new_job(
                name=name, description="Scheduled Ternuxx action", action_id=action_id,
                schedule_type="cron", schedule={"expression": expression, "timezone": timezone_name})
        except ValueError:
            return {"ok": False, "error": {"code": "invalid_cron_input"}}
        args = {"action": "create", "job": job}
    else:
        listing = _cron_jobs()
        if not listing.get("ok"):
            return listing
        jobs = listing.get("data", {}).get("jobs", [])
        if not jobs:
            return {"ok": False, "error": {"code": "no_cron_jobs"}}
        choices = ", ".join(f"{j.get('job_id')} ({j.get('name')})" for j in jobs if isinstance(j, dict))
        job_id = _prompt(screen, "Job ID from saved jobs: " + choices)
        if not any(isinstance(j, dict) and j.get("job_id") == job_id for j in jobs):
            return {"ok": False, "error": {"code": "unknown_job_id"}}
        if action == "remove":
            args = {"action": action, "job_id": job_id}
        else:
            field = _prompt(screen, "Update field: name or enabled").lower()
            if field == "name":
                value = _prompt(screen, "New job name")
                changes: dict[str, object] = {"name": value}
            elif field == "enabled":
                value = _prompt(screen, "Set enabled? yes or no").lower()
                if value not in {"yes", "no"}:
                    return {"ok": False, "error": {"code": "invalid_enabled_value"}}
                changes = {"enabled": value == "yes"}
            else:
                return {"ok": False, "error": {"code": "invalid_update_field"}}
            args = {"action": action, "job_id": job_id, "changes": changes}
    preview = _call("cron.jobs.mutation.preview", args)
    if not preview.get("ok"):
        return preview
    plan = preview.get("data", {}).get("plan", {})
    plan_id = plan.get("plan_id") if isinstance(plan, dict) else None
    if not isinstance(plan_id, str):
        return {"ok": False, "error": {"code": "invalid_cron_preview"}}
    _show_details(screen, preview)
    if _prompt(screen, f"Apply this exact saved Cron plan {plan_id}? type yes").lower() != "yes":
        return {"ok": False, "error": {"code": "cancelled"}}
    return _call("cron.jobs.mutation.apply", {"plan_id": plan_id, "confirmed": True})


def _cron_executions() -> dict[str, object]:
    """Read bounded Cron execution history via the shared management service."""
    return _call("cron.executions.list", {"limit": 20})


def _operation_history(resource: dict[str, Any]) -> dict[str, object]:
    if resource.get("id") != "recovery.native-state" or "recovery.status" not in resource.get("supported_operations", []):
        return {"ok": False, "error": {"code": "history_unavailable"}}
    return _call("recovery.status")


def _selected_status_operation(resource: dict[str, Any]) -> str | None:
    for operation in resource.get("supported_operations", []):
        if operation in READ_WITHOUT_ARGUMENTS and operation != "management.catalog":
            return operation
    return None


def _run(screen: "curses._CursesWindow") -> int:
    curses.curs_set(0)
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        palette = (
            (1, curses.COLOR_GREEN), (2, curses.COLOR_CYAN), (3, curses.COLOR_YELLOW),
            (4, curses.COLOR_BLUE), (5, curses.COLOR_WHITE), (6, curses.COLOR_RED),
        )
        for pair, color in palette:
            try:
                curses.init_pair(pair, color, -1)
            except curses.error:
                pass
    catalog_result = _call("management.catalog")
    if not catalog_result.get("ok"):
        raise RuntimeError("Could not load the shared resource catalog")
    catalog = catalog_result["data"]
    categories: list[dict[str, Any]] = list(catalog["categories"])
    all_resources: list[dict[str, Any]] = sorted(catalog["resources"], key=lambda item: (item["category_id"], item["name"].casefold()))
    category_index = selected = scroll = 0
    query = ""
    report: dict[str, object] | None = None

    while True:
        category = categories[category_index]
        resources = [r for r in all_resources if r["category_id"] == category["id"]
                     and (not query or query.casefold() in (r["name"] + " " + r["description"]).casefold())]
        if resources:
            selected = min(selected, len(resources) - 1)
        else:
            selected = scroll = 0
        scroll = _draw(screen, categories, category_index, resources, selected, query, report, scroll)
        key = screen.getch()
        if key in (ord("q"), ord("Q"), 27):
            return 0
        if key == curses.KEY_RESIZE:
            try:
                curses.update_lines_cols()
                screen.clearok(True)
            except curses.error:
                pass
        elif key in (curses.KEY_LEFT, ord("h")):
            category_index = (category_index - 1) % len(categories)
            selected = scroll = 0
        elif key in (curses.KEY_RIGHT, ord("l")):
            category_index = (category_index + 1) % len(categories)
            selected = scroll = 0
        elif key in (curses.KEY_DOWN, ord("j")) and resources:
            selected = min(len(resources) - 1, selected + 1)
            if selected >= scroll + max(1, screen.getmaxyx()[0] - 7):
                scroll += 1
        elif key in (curses.KEY_UP, ord("k")) and resources:
            selected = max(0, selected - 1)
            scroll = min(scroll, selected)
        elif key in (curses.KEY_NPAGE, ord("}")) and resources:
            page_size = max(1, screen.getmaxyx()[0] - 9)
            selected = min(len(resources) - 1, selected + page_size)
            scroll = min(max(0, selected - page_size + 1), max(0, len(resources) - 1))
        elif key in (curses.KEY_PPAGE, ord("{")) and resources:
            page_size = max(1, screen.getmaxyx()[0] - 9)
            selected = max(0, selected - page_size)
            scroll = max(0, min(scroll, selected))
        elif ord("0") <= key <= ord("9") and resources:
            target = 9 if key == ord("0") else key - ord("1")
            if target < len(resources):
                selected = target
                scroll = max(0, min(scroll, selected))
        elif key in (ord("/"),):
            query = _prompt(screen, "Search resources (blank clears)")[:120]
            selected = scroll = 0
        elif key in (curses.KEY_ENTER, 10, 13) and resources:
            resource = resources[selected]
            operation = _selected_status_operation(resource)
            if operation:
                report = _call(operation)
            else:
                report = {"ok": False, "error": {"code": "live_status_unavailable"}}
        elif key in (ord("h"), ord("H")) and resources:
            resource = resources[selected]
            if resource.get("id") == "recovery.native-state":
                report = _operation_history(resource)
            elif resource.get("id") == "automation.cron-registry" and "cron.executions.list" in resource.get("supported_operations", []):
                report = _cron_executions()
        elif key in (ord("v"), ord("V")):
            _show_details(screen, report)
        elif key in (ord("r"), ord("R")):
            report = _call("management.catalog")
            if report.get("ok"):
                catalog = report["data"]
                categories = list(catalog["categories"])
                all_resources = sorted(catalog["resources"], key=lambda item: (item["category_id"], item["name"].casefold()))
                category_index = min(category_index, len(categories) - 1)
        elif key in (ord("a"), ord("A")) and resources:
            resource = resources[selected]
            if resource["id"] in {"graphics.native", "graphics.debian"}:
                provider = "native" if resource["id"] == "graphics.native" else "debian"
                actions = "status, opengl, gles, vulkan"
                if provider == "native" and "graphics.provider.select" in resource.get("supported_operations", []):
                    actions += ", select"
                action = _choose(screen, "Graphics verification", [
                    (name, label) for name, label in (("status", "Check provider status"),
                    ("opengl", "Verify OpenGL"), ("gles", "Verify OpenGL ES"),
                    ("vulkan", "Verify Vulkan"), ("select", "Select Native backend"))
                    if name != "select" or provider == "native" and "graphics.provider.select" in resource.get("supported_operations", [])
                ]).lower()
                if action == "status":
                    report = _call("graphics.provider.status", {"provider": provider})
                elif action == "select" and provider == "native":
                    backend = _prompt(screen, "Choose backend: kgsl-freedreno or system")
                    if backend not in {"kgsl-freedreno", "system"}:
                        report = {"ok": False, "error": {"code": "invalid_backend"}}
                    elif _prompt(screen, f"Set Native backend to {backend} for future desktop starts? type yes").lower() == "yes":
                        report = _call("graphics.provider.select", {"provider": "native", "backend": backend, "confirmed": True})
                    else:
                        report = {"ok": False, "error": {"code": "cancelled"}}
                elif action in {"opengl", "gles", "vulkan"}:
                    display = ":1" if provider == "debian" else None
                    if provider == "debian":
                        chosen = _prompt(screen, "Debian display (default :1)")
                        display = chosen or ":1"
                    args = {"provider": provider, "api": action}
                    if display:
                        args["display"] = display
                    report = _call("graphics.provider.verify", args)
                else:
                    report = {"ok": False, "error": {"code": "cancelled"}}
            elif resource["id"] == "native.gui.activity-monitor":
                report = _edit_monitor_policy(screen)
            elif resource["id"] == "native.system.health":
                report = _manage_logs(screen)
            elif resource["id"] == "native.desktop.session":
                report = _desktop_action(screen, resource)
            elif resource["id"] == "proot.replay-guests":
                report = _manage_replay_guest(screen)
            elif resource["id"] == "proot.debian.workloads":
                choice = _choose(screen, "PRoot workloads", [("launch", "Launch named app"),
                    ("shortcut", "Add or remove named shortcut"), ("sync", "Sync discovered Debian apps"),
                    ("rollback", "Review and restore saved shortcut sync"),
                    ("sessions", "Inspect or manage sessions"),
                    ("guest", "Retire or restore a Ternuxx replay guest")]).lower()
                report = (_launch_proot_app(screen) if choice == "launch" else
                          _manage_proot_shortcut(screen) if choice == "shortcut" else
                          _manage_proot_shortcut_sync(screen) if choice == "sync" else
                          _manage_proot_shortcut_rollback(screen) if choice == "rollback" else
                          _manage_proot_sessions(screen) if choice == "sessions" else
                          _manage_replay_guest(screen) if choice == "guest" else
                          {"ok": False, "error": {"code": "cancelled"}})
            elif resource["id"] == "network.ssh.managed-8023":
                report = _managed_ssh_action(screen, resource)
            elif resource["id"] == "native.timezone":
                report = _timezone_action(screen)
            elif resource["id"] == "automation.cron-registry":
                choice = _choose(screen, "Cron automation", [("status", "Check scheduler status"),
                    ("service", "Start or stop scheduler"), ("jobs", "List saved jobs"),
                    ("change", "Create, edit, or remove a job"), ("history", "View recent runs")]).lower()
                report = (_call("cron.status") if choice == "status" else
                          _cron_jobs() if choice == "jobs" else
                          _cron_mutation(screen) if choice == "change" else
                          _cron_executions() if choice == "history" else
                          _cron_scheduler_action(screen) if choice == "service" else
                          {"ok": False, "error": {"code": "cancelled"}})
            elif resource["id"] == "boot.termux.profile":
                report = _boot_action(screen)
            elif resource["id"] == "native.wakelock":
                report = _wakelock_action(screen)
            else:
                report = {"ok": False, "error": {"code": "guided_action_unavailable"}}


def main() -> int:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("tx tui needs an interactive terminal.", file=sys.stderr)
        return 2
    try:
        return curses.wrapper(_run)
    except (curses.error, RuntimeError) as exc:
        print(f"tx tui could not start: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
