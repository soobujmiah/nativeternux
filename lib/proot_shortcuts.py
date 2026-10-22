"""Provider-scoped catalog and safe preview/apply for PRoot X11 launchers."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import shlex
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
    "blender": {
        "name": "Blender (PRoot)", "comment": "Open Blender from Debian PRoot",
        "icon": "blender", "program": "blender",
    },
    "pavucontrol": {
        "name": "Volume Control (PRoot)", "comment": "Open Debian PulseAudio controls",
        "icon": "multimedia-volume-control", "program": "pavucontrol",
    },
    "system-config-printer": {
        "name": "Print Settings (PRoot)", "comment": "Open Debian printer settings",
        "icon": "printer", "program": "system-config-printer",
    },
    "thunar-bulk-rename": {
        "name": "Bulk Rename (PRoot)", "comment": "Open Debian Thunar bulk rename",
        "icon": "system-file-manager", "program": "thunar",
    },
    "thunar-settings": {
        "name": "Thunar Preferences (PRoot)", "comment": "Open Debian Thunar preferences",
        "icon": "system-file-manager", "program": "thunar-settings",
    },
    "thunar-volman-settings": {
        "name": "Removable Drives and Media (PRoot)", "comment": "Open Debian removable media settings",
        "icon": "drive-removable-media", "program": "thunar-volman-settings",
    },
    "vlc": {
        "name": "VLC media player (PRoot)", "comment": "Open VLC from Debian PRoot",
        "icon": "vlc", "program": "/usr/bin/vlc",
    },
    "xarchiver": {
        "name": "Xarchiver (PRoot)", "comment": "Open Debian archive manager",
        "icon": "package-x-generic", "program": "xarchiver",
    },
    "xfce4-appfinder": {
        "name": "Application Finder (PRoot)", "comment": "Open Debian application finder",
        "icon": "system-search", "program": "xfce4-appfinder",
    },
    "xfce4-terminal-settings": {
        "name": "Xfce Terminal Settings (PRoot)", "comment": "Open Debian terminal preferences",
        "icon": "utilities-terminal", "program": "xfce4-terminal",
    },
    "shortcut-manager": {
        "name": "Manage PRoot Shortcuts", "comment": "Add, remove, and view PRoot app shortcuts",
        "icon": "preferences-desktop", "program": "manager",
    },
}

APP_ARGUMENTS: dict[str, tuple[str, ...]] = {
    "thunar-bulk-rename": ("--bulk-rename",),
    "vlc": ("--started-from-file",),
    "xfce4-terminal-settings": ("--preferences",),
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
    cli = Path(repo_root) / "tx"
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
        from proot_diagnostics import resolve_proot_guest_user
        user = resolve_proot_guest_user(distro="debian", prefix=prefix)
        probe_env = {key: value for key, value in os.environ.items()
                     if key not in {"ANDROID_ART_ROOT", "ANDROID_DATA", "ANDROID_I18N_ROOT",
                                    "ANDROID_ROOT", "ANDROID_RUNTIME_ROOT", "ANDROID_TZDATA_ROOT",
                                    "BOOTCLASSPATH", "DEX2OATBOOTCLASSPATH", "EXTERNAL_STORAGE"}}
        result = subprocess.run(
            [
                f"{prefix}/bin/proot-distro", "login", "debian", "--shared-tmp",
                "--user", user, "--", "sh", "-c",
                'command -v "$1" >/dev/null 2>&1', "sh", CATALOG[app_id]["program"],
            ],
            env=probe_env, check=False, capture_output=True, timeout=20,
        )
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0



# Keep generated guest launchers out of XFCE's generic Utility/Accessories
# menu. They belong only in the explicit PRoot Apps menu below.
DESKTOP_APP_CATEGORIES = "X-Ternuxx-PRoot;"
_DESKTOP_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,199}\.desktop\Z")


def _guest_app_dir(prefix: str) -> Path:
    root = Path(prefix) / "var/lib/proot-distro/containers/debian/rootfs"
    if root.is_symlink() or not root.is_dir():
        raise ShortcutError("installed Debian rootfs is unavailable or not a regular directory")
    app_dir = root / "usr/share/applications"
    if app_dir.is_symlink() or not app_dir.is_dir():
        raise ShortcutError("Debian application directory is unavailable")
    return app_dir


def _desktop_group(path: Path) -> dict[str, str]:
    import configparser
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    try:
        parser.read(path, encoding="utf-8")
        return dict(parser["Desktop Entry"])
    except (OSError, UnicodeError, KeyError, configparser.Error):
        return {}


def discover_desktop_apps(*, prefix: str) -> list[dict[str, str]]:
    """Read visible application entries from the selected Debian rootfs."""
    app_dir = _guest_app_dir(prefix)
    found: list[dict[str, str]] = []
    for path in sorted(app_dir.glob("*.desktop")):
        if path.is_symlink() or not path.is_file() or not _DESKTOP_ID.fullmatch(path.name):
            continue
        entry = _desktop_group(path)
        truth = lambda key: entry.get(key, "false").strip().lower() == "true"
        if (entry.get("Type") != "Application" or not entry.get("Name")
                or not entry.get("Exec") or truth("NoDisplay") or truth("Hidden")
                or truth("Terminal") or path.name == "xfce4-session-logout.desktop"):
            continue
        only = {item for item in entry.get("OnlyShowIn", "").split(";") if item}
        excluded = {item for item in entry.get("NotShowIn", "").split(";") if item}
        if (only and "XFCE" not in only) or "XFCE" in excluded:
            continue
        try:
            _desktop_app_argv(path.name, prefix=prefix)
        except ShortcutError:
            continue
        found.append({
            "desktop_id": path.name, "name": entry["Name"],
            "comment": entry.get("Comment", ""), "icon": entry.get("Icon", "applications-other"),
        })
    return found


def _desktop_app_argv(desktop_id: str, *, prefix: str) -> tuple[list[str], dict[str, str]]:
    if not _DESKTOP_ID.fullmatch(desktop_id):
        raise ShortcutError("invalid Debian desktop application ID")
    app_dir = _guest_app_dir(prefix)
    path = app_dir / desktop_id
    if path.is_symlink() or not path.is_file():
        raise ShortcutError("Debian desktop application is no longer installed")
    entry = _desktop_group(path)
    if (entry.get("Type") != "Application" or not entry.get("Exec")
            or entry.get("Hidden", "false").lower() == "true"
            or entry.get("NoDisplay", "false").lower() == "true"
            or entry.get("Terminal", "false").lower() == "true"
            or desktop_id == "xfce4-session-logout.desktop"):
        raise ShortcutError("Debian desktop entry is not an allowed visible GUI application")
    only = {item for item in entry.get("OnlyShowIn", "").split(";") if item}
    excluded = {item for item in entry.get("NotShowIn", "").split(";") if item}
    if (only and "XFCE" not in only) or "XFCE" in excluded:
        raise ShortcutError("Debian desktop entry is not available in XFCE")
    try:
        argv = shlex.split(entry["Exec"], posix=True)
    except ValueError as exc:
        raise ShortcutError("Debian desktop entry has invalid Exec quoting") from exc
    if not argv or not argv[0] or len(argv) > 128:
        raise ShortcutError("Debian desktop entry has an invalid launch command")
    expanded: list[str] = []
    field = re.compile(r"%(.)")
    for token in argv:
        if token in {"%f", "%F", "%u", "%U"}:
            continue
        if token == "%i":
            icon = entry.get("Icon", "")
            if icon:
                expanded.extend(["--icon", icon])
            continue
        def replace(match: re.Match[str]) -> str:
            code = match.group(1)
            if code == "%":
                return "%"
            if code == "c":
                return entry.get("Name", "")
            if code == "k":
                return f"/usr/share/applications/{desktop_id}"
            if code in {"f", "F", "u", "U", "d", "D", "n", "N", "v", "m"}:
                return ""
            raise ShortcutError("Debian desktop entry uses an unsupported field code")
        expanded.append(field.sub(replace, token))
    expanded = [part for part in expanded if part != ""]
    if not expanded:
        raise ShortcutError("Debian desktop entry has no launchable command")
    interpreters = {"sh", "bash", "dash", "zsh", "fish", "busybox", "python", "python2",
                    "python3", "perl", "ruby", "node"}
    for index, token in enumerate(expanded[:-1]):
        if Path(token).name.lower() in interpreters and "-c" in expanded[index + 1:index + 4]:
            raise ShortcutError("shell or interpreter command desktop entries are not launched from shortcuts")
    return expanded, entry


def _safe_desktop_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", " ").replace("\r", " ").replace("\t", " ").replace("\x00", "")


def _dynamic_entry(desktop_id: str, item: dict[str, str], *, cli: str) -> bytes:
    command = f"{_desktop_quote(cli)} mng app launch --desktop-id {_desktop_quote(desktop_id)}"
    lines = [
        "[Desktop Entry]", "Version=1.0", "Type=Application",
        f"Name={_safe_desktop_value(item['name'])} (PRoot)",
        f"Comment={_safe_desktop_value(item.get('comment', ''))}",
        f"Exec={command}", f"Icon={_safe_desktop_value(item.get('icon', 'applications-other'))}",
        "Terminal=false", "StartupNotify=true", f"Categories={DESKTOP_APP_CATEGORIES}",
        "X-Ternuxx-Generated=proot-app-v2", f"X-Ternuxx-Desktop-ID={desktop_id}",
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".ternuxx-proot-apps-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _sync_desktop_applications_mutate(*, home: str, prefix: str, repo_root: str,
                               xdg_data_home: str | None = None,
                               xdg_config_home: str | None = None) -> dict[str, Any]:
    home_path, app_dir = _paths(home, xdg_data_home)
    config_home = Path(xdg_config_home).expanduser() if xdg_config_home else home_path / ".config"
    if not config_home.is_absolute():
        config_home = home_path / config_home
    config_home = config_home.resolve()
    try:
        config_home.relative_to(home_path)
    except ValueError as exc:
        raise ShortcutError("XDG config directory must remain inside the native home directory") from exc
    items = discover_desktop_apps(prefix=prefix)
    installed_cli = Path(prefix) / "bin" / "tx"
    cli = str(installed_cli if installed_cli.is_file() and os.access(installed_cli, os.X_OK)
              else Path(repo_root) / "tx")
    desired: dict[str, bytes] = {}
    for item in items:
        desktop_id = item["desktop_id"]
        filename = "ternuxx-proot-app-" + desktop_id
        desired[filename] = _dynamic_entry(desktop_id, item, cli=cli)
    app_dir.mkdir(parents=True, exist_ok=True)
    written, conflicts, removed = [], [], []
    for filename, payload in desired.items():
        target = app_dir / filename
        existing = _file_bytes(target)
        if existing == payload:
            continue
        if existing is not None and b"X-Ternuxx-Generated=proot-app" not in existing and b"X-Ternuxx-Generated=proot-app-v2" not in existing:
            conflicts.append(filename)
            continue
        _atomic_write(target, payload)
        written.append(filename)
    for target in app_dir.glob("ternuxx-proot-app-*.desktop"):
        if target.name in desired:
            continue
        raw = _file_bytes(target)
        if raw is not None and (b"X-Ternuxx-Generated=proot-app" in raw or b"X-Ternuxx-Generated=proot-app-v2" in raw):
            target.unlink()
            removed.append(target.name)

    menus = config_home / "menus"
    menu_file = menus / "xfce-applications.menu"
    menu_payload = ('''<!DOCTYPE Menu PUBLIC "-//freedesktop//DTD Menu 1.0//EN"
  "http://www.freedesktop.org/standards/menu-spec/1.0/menu.dtd">
<Menu>
  <Name>Xfce</Name>
  <MergeFile type="parent">xfce-applications.menu</MergeFile>
  <Menu>
    <Name>Accessories</Name>
    <Exclude><Category>X-Ternuxx-PRoot</Category></Exclude>
  </Menu>
  <Menu>
    <Name>Accessibility</Name>
    <Exclude><Category>X-Ternuxx-PRoot</Category></Exclude>
  </Menu>
  <Menu>
    <Name>PRoot Apps</Name>
    <Directory>ternuxx-proot-apps.directory</Directory>
    <Include><Category>X-Ternuxx-PRoot</Category></Include>
  </Menu>
</Menu>
''').encode("utf-8")
    directory_file = app_dir.parent / "desktop-directories" / "ternuxx-proot-apps.directory"
    directory_payload = (b"[Desktop Entry]\nType=Directory\nName=PRoot Apps\n"
                         b"Icon=applications-system\nX-Ternuxx-Generated=true\n")
    legacy_directory_payload = (b"[Desktop Entry]\nType=Directory\nName=PRoot Apps\n"
                                b"Icon=applications-system\n")
    menu_status = "unchanged"
    for target, payload in ((menu_file, menu_payload), (directory_file, directory_payload)):
        old = _file_bytes(target)
        if old == payload:
            continue
        owned = (b"X-Ternuxx-PRoot" in old if target == menu_file and old is not None else
                 b"X-Ternuxx-Generated=true" in old if old is not None else False)
        if old is not None and not owned and not (target == directory_file and old == legacy_directory_payload):
            conflicts.append(str(target.relative_to(home_path)))
            continue
        _atomic_write(target, payload)
        menu_status = "updated"
    return {"status": "complete", "discovered": len(items), "written": written,
            "removed": removed, "conflicts": conflicts, "menu": menu_status,
            "desktop_ids": [item["desktop_id"] for item in items], "read_only": False}



def _sync_roots(home: str, xdg_data_home: str | None,
                xdg_config_home: str | None) -> tuple[Path, Path, Path]:
    home_path, app_dir = _paths(home, xdg_data_home)
    config_home = Path(xdg_config_home).expanduser() if xdg_config_home else home_path / ".config"
    if not config_home.is_absolute():
        config_home = home_path / config_home
    config_home = config_home.resolve()
    try:
        config_home.relative_to(home_path)
    except ValueError as exc:
        raise ShortcutError("XDG config directory must remain inside the native home directory") from exc
    return home_path, app_dir, config_home


def _sync_stage(*, home: str, prefix: str, repo_root: str,
                xdg_data_home: str | None, xdg_config_home: str | None
                ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run the existing sync against a private copy and return an exact file plan."""
    import shutil
    actual_home, actual_apps, actual_config = _sync_roots(home, xdg_data_home, xdg_config_home)
    actual_menu = actual_config / "menus" / "xfce-applications.menu"
    actual_directory = actual_apps.parent / "desktop-directories" / "ternuxx-proot-apps.directory"

    def mapped(stage_home: Path, actual: Path) -> Path:
        try:
            relative = actual.relative_to(actual_home)
        except ValueError as exc:
            raise ShortcutError("shortcut sync target escaped the native home directory") from exc
        return stage_home / relative

    with tempfile.TemporaryDirectory(prefix=".ternuxx-shortcut-preview-", dir=actual_home) as temp:
        stage_home = Path(temp) / "home"
        stage_home.mkdir(mode=0o700)
        stage_apps = mapped(stage_home, actual_apps)
        stage_config = mapped(stage_home, actual_config)
        stage_menu = mapped(stage_home, actual_menu)
        stage_directory = mapped(stage_home, actual_directory)

        def copy_target(source: Path, destination: Path) -> None:
            if source.is_symlink():
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.symlink(os.readlink(source), destination)
            elif source.exists():
                if not source.is_file():
                    raise ShortcutError("shortcut sync target is not a regular file")
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)

        if actual_apps.exists():
            if actual_apps.is_symlink() or not actual_apps.is_dir():
                raise ShortcutError("applications menu directory is not a regular directory")
            for source in actual_apps.glob("ternuxx-proot-app-*.desktop"):
                copy_target(source, stage_apps / source.name)
        copy_target(actual_menu, stage_menu)
        copy_target(actual_directory, stage_directory)

        stage_result = _sync_desktop_applications_mutate(
            home=str(stage_home), prefix=prefix, repo_root=repo_root,
            xdg_data_home=str(mapped(stage_home, actual_apps.parent)),
            xdg_config_home=str(mapped(stage_home, actual_config)),
        )

        staged_files: set[Path] = set()
        if stage_apps.exists():
            staged_files.update(stage_apps.glob("ternuxx-proot-app-*.desktop"))
        for candidate in (stage_menu, stage_directory):
            if candidate.exists() or candidate.is_symlink():
                staged_files.add(candidate)
        actual_files: set[Path] = set()
        if actual_apps.exists():
            actual_files.update(actual_apps.glob("ternuxx-proot-app-*.desktop"))
        for candidate in (actual_menu, actual_directory):
            if candidate.exists() or candidate.is_symlink():
                actual_files.add(candidate)

        pairs: list[dict[str, Any]] = []
        for staged in staged_files | {mapped(stage_home, path) for path in actual_files}:
            actual = actual_home / staged.relative_to(stage_home)
            before = _file_bytes(actual)
            after = _file_bytes(staged)
            if before == after:
                continue
            pairs.append({
                "path": str(actual.relative_to(actual_home)),
                "before_bytes": before,
                "after_bytes": after,
                "before_mode": (actual.stat().st_mode & 0o777) if before is not None else None,
            })
        pairs.sort(key=lambda item: item["path"])
        return stage_result, pairs


def preview_desktop_application_sync(*, home: str, prefix: str, repo_root: str,
                                     xdg_data_home: str | None = None,
                                     xdg_config_home: str | None = None) -> dict[str, Any]:
    stage, pairs = _sync_stage(
        home=home, prefix=prefix, repo_root=repo_root,
        xdg_data_home=xdg_data_home, xdg_config_home=xdg_config_home,
    )
    changes = []
    for item in pairs:
        before, after = item["before_bytes"], item["after_bytes"]
        changes.append({
            "path": item["path"],
            "action": "remove" if after is None else ("create" if before is None else "update"),
            "before": hashlib.sha256(before).hexdigest() if before is not None else "absent",
            "after": hashlib.sha256(after).hexdigest() if after is not None else "absent",
        })
    plan = {"provider": "native_termux", "guest_provider": "proot_debian", "changes": changes}
    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
    plan_id = hashlib.sha256(canonical).hexdigest()[:24]
    return {
        "resource_id": "proot.x11.shortcut-sync",
        "provider": "proot_debian",
        "storage_provider": "native_termux",
        "status": "preview",
        "discovered": stage.get("discovered", 0),
        "desktop_ids": stage.get("desktop_ids", []),
        "conflicts": stage.get("conflicts", []),
        "changes": changes,
        "changed": bool(changes),
        "requires_confirmation": bool(changes),
        "plan_id": plan_id,
        "read_only": True,
    }


def apply_desktop_application_sync(*, home: str, prefix: str, repo_root: str,
                                   confirmed: bool, plan_id: str | None,
                                   xdg_data_home: str | None = None,
                                   xdg_config_home: str | None = None) -> dict[str, Any]:
    preview = preview_desktop_application_sync(
        home=home, prefix=prefix, repo_root=repo_root,
        xdg_data_home=xdg_data_home, xdg_config_home=xdg_config_home,
    )
    if not preview["changed"]:
        return {**preview, "status": "already_in_requested_state"}
    if not confirmed or not isinstance(plan_id, str):
        return {**preview, "status": "confirmation_required"}
    if plan_id != preview["plan_id"]:
        raise ShortcutError("shortcut sync state changed or plan ID does not match the current preview")

    home_path = Path(home).expanduser().resolve()
    snapshots = []
    for change in preview["changes"]:
        target = home_path / change["path"]
        snapshots.append((target, _file_bytes(target), target.stat().st_mode & 0o777
                          if target.exists() and not target.is_symlink() else None))
    try:
        result = _sync_desktop_applications_mutate(
            home=home, prefix=prefix, repo_root=repo_root,
            xdg_data_home=xdg_data_home, xdg_config_home=xdg_config_home,
        )
    except Exception:
        rollback_errors = []
        for target, before, mode in reversed(snapshots):
            try:
                if before is None:
                    target.unlink(missing_ok=True)
                else:
                    _atomic_write(target, before)
                    if mode is not None:
                        os.chmod(target, mode)
            except OSError as exc:
                rollback_errors.append(str(target))
        if rollback_errors:
            raise ShortcutError("shortcut sync failed and rollback needs recovery for: "
                                + ", ".join(rollback_errors))
        raise
    return {**preview, "status": "complete", "changed": True,
            "written": result.get("written", []), "removed": result.get("removed", []),
            "conflicts": result.get("conflicts", []), "menu": result.get("menu"),
            "read_only": False}

def launch_desktop_application(desktop_id: str, *, prefix: str, repo_root: str,
                               env: dict[str, str], display: str | None = None) -> dict[str, Any]:
    argv, _entry_data = _desktop_app_argv(desktop_id, prefix=prefix)
    if display is not None and not re.fullmatch(r":[0-9]{1,2}", display):
        raise ShortcutError("unsupported X11 display")
    script = Path(repo_root) / "scripts" / "proot-x11-app.sh"
    command = [f"{prefix}/bin/bash", str(script)]
    if display is not None:
        command += ["--display", display]
    command += ["--", *argv]
    result = subprocess.run(command, env=env, check=False)
    if result.returncode != 0:
        raise ShortcutError("the PRoot GUI application did not complete successfully")
    return {"resource_id": f"proot.x11.app.{desktop_id}", "provider": "proot_debian",
            "status": "process_exited", "exit_status": result.returncode,
            "gui_visible": "unknown", "read_only": False}

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
           display: str | None = None) -> dict[str, Any]:
    if app_id not in CATALOG:
        raise ShortcutError("unknown PRoot application ID")
    if display is not None and not re.fullmatch(r":[0-9]{1,2}", display):
        raise ShortcutError("unsupported X11 display")
    if CATALOG[app_id]["program"] == "manager":
        script = Path(repo_root) / "scripts" / "proot-x11-shortcut-manager.sh"
        command = [f"{prefix}/bin/bash", str(script)]
    else:
        script = Path(repo_root) / "scripts" / "proot-x11-app.sh"
        command = [f"{prefix}/bin/bash", str(script)]
        if display is not None:
            command += ["--display", display]
        command += [CATALOG[app_id]["program"], *APP_ARGUMENTS.get(app_id, ())]
    result = subprocess.run(command, env=env, check=False)
    if result.returncode != 0:
        raise ShortcutError("the PRoot GUI application did not complete successfully")
    return {"resource_id": f"proot.x11.app.{app_id}", "provider": "proot_debian",
            "status": "process_exited", "exit_status": result.returncode,
            "gui_visible": "unknown", "read_only": False}
