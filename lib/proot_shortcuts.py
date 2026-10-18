"""Provider-scoped catalog and safe preview/apply for PRoot X11 launchers."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import tempfile
from typing import Any


CATALOG: dict[str, dict[str, str]] = {
    "terminal": {
        "name": "PRoot Terminal", "comment": "Open a Debian PRoot terminal in this desktop",
        "icon": "utilities-terminal", "program": "xfce4-terminal",
    },
    "files": {
        "name": "PRoot Files", "comment": "Browse Debian PRoot files in this desktop",
        "icon": "system-file-manager", "program": "thunar",
    },
    "firefox": {
        "name": "PRoot Firefox", "comment": "Browse the web with Debian PRoot Firefox",
        "icon": "firefox", "program": "firefox-esr",
    },
    "shortcut-manager": {
        "name": "Manage PRoot Shortcuts", "comment": "Add, remove, and view PRoot app shortcuts",
        "icon": "preferences-desktop", "program": "manager",
    },
}


class ShortcutError(RuntimeError):
    pass


def _paths(home: str, xdg_data_home: str | None) -> tuple[Path, Path]:
    home_path = Path(home).expanduser().resolve()
    root = Path(xdg_data_home).expanduser() if xdg_data_home else home_path / ".local" / "share"
    if not root.is_absolute():
        root = home_path / root
    root = root.resolve()
    try:
        root.relative_to(home_path)
    except ValueError as exc:
        raise ShortcutError("XDG data directory must remain inside the native home directory") from exc
    app_dir = (root / "applications").resolve()
    try:
        app_dir.relative_to(home_path)
    except ValueError as exc:
        raise ShortcutError("Applications menu directory must remain inside the native home directory") from exc
    return home_path, app_dir


def _target(app_dir: Path, app_id: str) -> Path:
    if app_id not in CATALOG:
        raise ShortcutError("unknown PRoot shortcut ID")
    return app_dir / f"ternuxx-proot-{app_id}.desktop"


def _file_bytes(path: Path) -> bytes | None:
    if path.is_symlink():
        raise ShortcutError("shortcut target is a symbolic link; refusing to follow it")
    if not path.exists():
        return None
    if not path.is_file():
        raise ShortcutError("shortcut target is not a regular file")
    return path.read_bytes()


def _desktop_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$")
    return f'"{escaped.replace("%", "%%")}"'


def _entry(app_id: str, *, repo_root: str) -> bytes:
    item = CATALOG[app_id]
    cli = Path(repo_root) / "ternuxx"
    command = f"{_desktop_quote(str(cli))} management app launch {app_id}"
    lines = [
        "[Desktop Entry]", "Version=1.0", "Type=Application",
        f"Name={item['name']}", f"Comment={item['comment']}",
        f"Exec={command}", f"Icon={item['icon']}", "Terminal=false",
        "StartupNotify=true", "Categories=System;X-Ternuxx;",
        "X-Ternuxx-Managed=true", f"X-Ternuxx-App-ID={app_id}",
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _legacy_entry(app_id: str, *, prefix: str, repo_root: str) -> bytes:
    """Exact old helper output, recognized for safe migration without overwriting edits."""
    item = CATALOG[app_id]
    if item["program"] == "manager":
        name = "Manage PRoot Shortcuts"
    else:
        name = f"{item['name']} (Ternux)"
    launcher = Path(repo_root) / "scripts" / (
        "proot-x11-shortcut-manager.sh" if item["program"] == "manager" else "proot-x11-app.sh"
    )
    command = f"{prefix}/bin/bash {launcher}"
    if item["program"] != "manager":
        command += f" {item['program']}"
    lines = ["[Desktop Entry]", "Version=1.0", "Type=Application", f"Name={name}",
             f"Comment={item['comment']}", f"Exec={command}", f"Icon={item['icon']}",
             "Terminal=false", "StartupNotify=true", "Categories=System;X-Ternuxx;"]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _managed(existing: bytes | None, app_id: str, *, prefix: str, repo_root: str) -> bool:
    if existing is None:
        return False
    return existing in {
        _entry(app_id, repo_root=repo_root),
        _legacy_entry(app_id, prefix=prefix, repo_root=repo_root),
    }


def _available(app_id: str, *, prefix: str, home: str, path: str, repo_root: str) -> bool:
    if CATALOG[app_id]["program"] == "manager":
        return (Path(repo_root) / "scripts" / "proot-x11-shortcut-manager.sh").is_file()
    try:
        from proot_diagnostics import resolve_ternux_guest_user
        user = resolve_ternux_guest_user(home=home, path=path)
        result = subprocess.run(
            [
                f"{prefix}/bin/proot-distro", "login", "debian", "--shared-tmp",
                "--user", user, "--", "sh", "-c",
                'command -v "$1" >/dev/null 2>&1', "sh", CATALOG[app_id]["program"],
            ],
            check=False, capture_output=True, timeout=20,
        )
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def list_shortcuts(*, home: str, prefix: str, xdg_data_home: str | None = None,
                   repo_root: str | None = None) -> dict[str, Any]:
    _, app_dir = _paths(home, xdg_data_home)
    repo_root = repo_root or str(Path(__file__).resolve().parents[1])
    items = []
    for app_id, item in CATALOG.items():
        path = _target(app_dir, app_id)
        raw = _file_bytes(path)
        if raw is None:
            state = "absent"
        elif _managed(raw, app_id, prefix=prefix, repo_root=repo_root):
            state = "installed"
        else:
            state = "conflict"
        items.append({
            "id": app_id, "name": item["name"], "provider": "proot_debian",
            "shortcut_owner": "native_termux", "shortcut_state": state,
            "application_availability": "unknown", "read_only": True,
        })
    return {"resource_id": "proot.x11.shortcuts", "items": items, "read_only": True}


def preview(action: str, app_id: str, *, home: str, prefix: str, repo_root: str,
            xdg_data_home: str | None = None, path: str = "") -> dict[str, Any]:
    if action not in {"add", "remove"} or app_id not in CATALOG:
        raise ShortcutError("shortcut action or ID is unsupported")
    home_path, app_dir = _paths(home, xdg_data_home)
    target = _target(app_dir, app_id)
    existing = _file_bytes(target)
    desired = _entry(app_id, repo_root=repo_root)
    managed = _managed(existing, app_id, prefix=prefix, repo_root=repo_root)
    if existing is not None and action == "add" and existing != desired and not managed:
        raise ShortcutError("a non-Ternuxx launcher already uses this shortcut ID; it was preserved")
    if existing is not None and action == "remove" and not managed:
        raise ShortcutError("the target is not a Ternuxx-managed launcher; it was preserved")
    if action == "add" and existing is None and not _available(
        app_id, prefix=prefix, home=str(home_path), path=path, repo_root=repo_root,
    ):
        raise ShortcutError("the PRoot application or launcher manager is unavailable")
    changed = (action == "add" and existing != desired) or (action == "remove" and existing is not None)
    before = hashlib.sha256(existing).hexdigest() if existing is not None else "absent"
    plan = {"provider": "proot_debian", "action": action, "app_id": app_id,
            "target": str(target.relative_to(home_path)), "before": before,
            "after": hashlib.sha256(desired).hexdigest() if action == "add" else "absent"}
    canonical_plan = json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
    plan_id = hashlib.sha256(canonical_plan).hexdigest()[:24]
    return {"resource_id": f"proot.x11.shortcut.{app_id}", "provider": "proot_debian",
            "storage_provider": "native_termux", "action": action, "app_id": app_id,
            "changed": changed, "requires_confirmation": changed, "plan_id": plan_id,
            "affected_resources": [{"provider": "native_termux", "path": str(target.relative_to(home_path)),
                                     "before": "absent" if existing is None else "present",
                                     "after": "present" if action == "add" else "absent"}],
            "safety": {"read_only": True, "running_apps_stopped": False}}


def apply(action: str, app_id: str, *, home: str, prefix: str, repo_root: str,
          confirmed: bool, plan_id: str | None, xdg_data_home: str | None = None,
          path: str = "") -> dict[str, Any]:
    plan = preview(action, app_id, home=home, prefix=prefix, repo_root=repo_root,
                   xdg_data_home=xdg_data_home, path=path)
    if not plan["changed"]:
        return {**plan, "status": "already_in_requested_state"}
    if not confirmed or not isinstance(plan_id, str):
        return {**plan, "status": "confirmation_required"}
    if plan_id != plan["plan_id"]:
        raise ShortcutError("shortcut state changed or plan ID does not match the current preview")
    _, app_dir = _paths(home, xdg_data_home)
    target = _target(app_dir, app_id)
    app_dir.mkdir(parents=True, exist_ok=True)
    if action == "remove":
        target.unlink()
    else:
        payload = _entry(app_id, repo_root=repo_root)
        fd, temporary = tempfile.mkstemp(prefix=".ternuxx-shortcut-", dir=app_dir)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, 0o644)
            os.replace(temporary, target)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
    return {**plan, "status": "complete", "changed": True,
            "safety": {"read_only": False, "running_apps_stopped": False}}


def launch(app_id: str, *, prefix: str, repo_root: str, env: dict[str, str],
           session_owner: str = "ternuxx", display: str | None = None) -> dict[str, Any]:
    if app_id not in CATALOG:
        raise ShortcutError("unknown PRoot application ID")
    if not isinstance(session_owner, str) or session_owner not in {"ternuxx", "ternux"}:
        raise ShortcutError("unknown X11 session owner")
    if session_owner == "ternux" and (display is None or not re.fullmatch(r":[0-9]{1,2}", display)):
        raise ShortcutError("Ternux session requires an explicit X11 display")
    if display is not None and not re.fullmatch(r":[0-9]{1,2}", display):
        raise ShortcutError("unsupported X11 display")
    if CATALOG[app_id]["program"] == "manager":
        if session_owner != "ternuxx":
            raise ShortcutError("the shortcut manager is available only in the Ternuxx desktop")
        script = Path(repo_root) / "scripts" / "proot-x11-shortcut-manager.sh"
        command = [f"{prefix}/bin/bash", str(script)]
    else:
        script = Path(repo_root) / "scripts" / "proot-x11-app.sh"
        command = [f"{prefix}/bin/bash", str(script)]
    if session_owner != "ternuxx" or display is not None:
        command += ["--session", session_owner]
        if display is not None:
            command += ["--display", display]
    if CATALOG[app_id]["program"] != "manager":
        command += [CATALOG[app_id]["program"]]
    result = subprocess.run(command, env=env, check=False)
    if result.returncode != 0:
        raise ShortcutError("the PRoot GUI application did not complete successfully")
    return {"resource_id": f"proot.x11.app.{app_id}", "provider": "proot_debian",
            "status": "process_exited", "exit_status": result.returncode,
            "gui_visible": "unknown", "read_only": False}
