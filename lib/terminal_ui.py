#!/usr/bin/env python3
"""Keyboard-first categorized client for the shared Ternuxx management service."""
from __future__ import annotations

import curses
import json
import os
import re
import sys
import textwrap
import uuid
from typing import Any

import management_service
import management_sessions
import management_presentation
import proot_shortcuts


BRANDING_LINE = "Workstation in your pocket — by Sobuj Miah · soobujmiah.github.io"


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


def _launch_proot_app(screen: "curses._CursesWindow") -> dict[str, object] | None:
    """Guide a named app launch through the shared provider-aware operation."""
    app_id = _prompt(screen, "App name (" + ", ".join(proot_shortcuts.CATALOG) + ")")
    if not app_id:
        return None
    if app_id not in proot_shortcuts.CATALOG:
        return {"ok": False, "error": {"code": "unknown_proot_app"}}
    display = _prompt(screen, "Native Ternuxx X11 display (blank=verified session default)")
    if display and not re.fullmatch(r":[0-9]{1,2}", display):
        return {"ok": False, "error": {"code": "invalid_display"}}
    name = proot_shortcuts.CATALOG[app_id]["name"]
    target = "Native Ternuxx display" + (f" {display}" if display else "")
    if _prompt(screen, f"Launch {name} through PRoot in {target}? type yes").lower() != "yes":
        return {"ok": False, "error": {"code": "cancelled"}}
    args: dict[str, object] = {"app_id": app_id}
    if display:
        args["display"] = display
    return _call("proot.app.launch", args)


def _desktop_action(screen: "curses._CursesWindow", resource: dict[str, Any]) -> dict[str, object]:
    action = _prompt(screen, "Desktop action: start or stop (blank cancels)").lower()
    operation = {"start": "desktop.start", "stop": "desktop.stop"}.get(action)
    if not operation or operation not in resource.get("supported_operations", []):
        return {"ok": False, "error": {"code": "action_unavailable"}}
    if _prompt(screen, f"Confirm {action} native desktop? type yes").lower() != "yes":
        return {"ok": False, "error": {"code": "cancelled"}}
    return _call(operation)


def _managed_ssh_action(screen: "curses._CursesWindow", resource: dict[str, Any]) -> dict[str, object]:
    if resource.get("id") != "network.ssh.managed-8023":
        return {"ok": False, "error": {"code": "externally_managed_resource"}}
    action = _prompt(screen, "Managed SSH 8023 action: start or stop (blank cancels)").lower()
    operation = {"start": "ssh.service.start", "stop": "ssh.service.stop"}.get(action)
    if not operation or operation not in resource.get("supported_operations", []):
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


def _available_action_labels(resource: dict[str, Any]) -> list[str]:
    """Describe only guided controls implemented by this TUI for this resource."""
    resource_id = resource.get("id")
    operations = set(resource.get("supported_operations", []))
    labels: list[str] = []
    if _selected_status_operation(resource):
        labels.append("check status")
    if resource_id == "native.desktop.session":
        labels.extend(name for op, name in (("desktop.start", "start desktop"),
                                            ("desktop.stop", "stop desktop")) if op in operations)
    elif resource_id in {"graphics.native", "graphics.debian"}:
        labels.extend(("check graphics status", "verify OpenGL", "verify Vulkan", "select Native backend"))
    elif resource_id == "native.gui.activity-monitor":
        labels.append("configure monitoring policy")
    elif resource_id == "proot.debian.workloads":
        labels.append("launch named PRoot app")
    elif resource_id == "network.ssh.managed-8023":
        labels.extend(name for op, name in (("ssh.service.start", "start SSH 8023 (preview)"),
                                            ("ssh.service.stop", "stop SSH 8023 (preview)")) if op in operations)
    elif resource_id == "recovery.native-state" and "recovery.status" in operations:
        labels.append("view operation history")
    elif resource_id == "automation.cron-registry" and "cron.jobs.list" in operations:
        labels.append("list persisted job definitions")
    return labels


def _draw(screen: "curses._CursesWindow", categories: list[dict[str, Any]], category_index: int,
          resources: list[dict[str, Any]], selected: int, query: str,
          report: dict[str, object] | None, scroll: int = 0) -> int:
    screen.erase()
    height, width = screen.getmaxyx()
    title = " Ternuxx Management Center ".ljust(max(width - 1, 0))
    screen.attron(curses.color_pair(1) | curses.A_BOLD)
    screen.addnstr(0, 0, title, max(width - 1, 0))
    screen.attroff(curses.color_pair(1) | curses.A_BOLD)
    screen.addnstr(1, 1, BRANDING_LINE,
                   max(width - 2, 0))
    category = categories[category_index] if categories else {"name": "Resources"}
    screen.addnstr(2, 1, f"{category['name']}  ·  {len(resources)} resources", max(width - 2, 0))
    screen.addnstr(3, 1, f"Search: {query or '—'}  ·  ←/→ category  / search  Enter status  h history  v details",
                   max(width - 2, 0))
    selected_resource = resources[selected] if resources and selected < len(resources) else None
    action_text = ", ".join(_available_action_labels(selected_resource)) if selected_resource else "none"
    screen.addnstr(4, 1, f"Available: {action_text}", max(width - 2, 0))
    if height < 10 or width < 34:
        if height > 2 and width > 1:
            screen.addnstr(2, 1, "Resize terminal to at least 34x10", width - 2)
        screen.refresh()
        return 0
    capacity = max(1, height - 9)
    max_scroll = max(0, len(resources) - capacity)
    scroll = min(max(0, min(scroll, max_scroll)), max_scroll)
    for row, resource in enumerate(resources[scroll:scroll + capacity], 5):
        index = scroll + row - 5
        marker = ">" if index == selected else " "
        status = management_presentation.status_label(resource.get("status", "unknown"))
        text = f"{marker} {resource.get('name', 'Resource')} · {status} · {_resource_state(resource)}"
        if index == selected:
            screen.attron(curses.A_REVERSE)
        screen.addnstr(row, 1, text, max(width - 2, 0))
        if index == selected:
            screen.attroff(curses.A_REVERSE)
    if report:
        error = report.get("error") if isinstance(report.get("error"), dict) else {}
        code = error.get("code")
        message = "Last action: " + (str(code) if code else ("complete" if report.get("ok") else "failed"))
        screen.addnstr(height - 3, 1, message, max(width - 2, 0))
        data = report.get("data") if isinstance(report.get("data"), dict) else {}
        values = [f"{key.replace('_', ' ')}: {value}" for key, value in list(data.items())[:2]
                  if not isinstance(value, (dict, list))]
        if values:
            screen.addnstr(height - 2, 1, " · ".join(values), max(width - 2, 0))
    footer = " ←/→ categories · ↑/↓ resources · Enter status · h history · v details · a actions · q quit "
    screen.attron(curses.A_REVERSE)
    screen.addnstr(height - 1, 0, footer.ljust(max(width - 1, 0)), max(width - 1, 0))
    screen.attroff(curses.A_REVERSE)
    screen.refresh()
    return scroll


def _detail_lines(report: dict[str, object] | None, width: int) -> list[str]:
    if not report:
        return ["No operation details are available."]
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
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
        screen.attron(curses.color_pair(1) | curses.A_BOLD)
        screen.addnstr(0, 0, title, max(width - 1, 0))
        screen.attroff(curses.color_pair(1) | curses.A_BOLD)
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
        curses.init_pair(1, curses.COLOR_GREEN, -1)
    catalog_result = _call("management.catalog")
    if not catalog_result.get("ok"):
        raise RuntimeError("Could not load the shared resource catalog")
    catalog = catalog_result["data"]
    categories: list[dict[str, Any]] = catalog["categories"]
    all_resources: list[dict[str, Any]] = catalog["resources"]
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
        elif key in (ord("h"), ord("H")) and resources and resources[selected].get("id") == "recovery.native-state":
            report = _operation_history(resources[selected])
        elif key in (ord("v"), ord("V")):
            _show_details(screen, report)
        elif key in (ord("r"), ord("R")):
            report = _call("management.catalog")
            if report.get("ok"):
                catalog = report["data"]
                categories, all_resources = catalog["categories"], catalog["resources"]
                category_index = min(category_index, len(categories) - 1)
        elif key in (ord("a"), ord("A")) and resources:
            resource = resources[selected]
            if resource["id"] in {"graphics.native", "graphics.debian"}:
                provider = "native" if resource["id"] == "graphics.native" else "debian"
                action = _prompt(screen, "Graphics action: status, opengl, gles, or vulkan (blank cancels)").lower()
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
            elif resource["id"] == "native.desktop.session":
                report = _desktop_action(screen, resource)
            elif resource["id"] == "proot.debian.workloads":
                report = _launch_proot_app(screen)
            elif resource["id"] == "network.ssh.managed-8023":
                report = _managed_ssh_action(screen, resource)
            elif resource["id"] == "automation.cron-registry":
                report = _cron_jobs()
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
