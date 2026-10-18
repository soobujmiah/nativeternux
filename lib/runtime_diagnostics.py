"""Read-only, bounded Native Termux boot and Wake Lock capability checks."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
from typing import Callable


def _read_command(runner: Callable[..., subprocess.CompletedProcess[str]], args: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return runner(args, capture_output=True, text=True, timeout=4, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None


def inspect_boot(*, home: str | os.PathLike[str], which: Callable[[str], str | None] = shutil.which,
                 runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> dict[str, object]:
    boot_dir = Path(home) / ".termux/boot"
    # Android's `cmd package` service can be available from Termux even when the
    # `pm` wrapper cannot transact with PackageManager. Prefer the direct command,
    # but keep the wrapper as a compatibility fallback.
    cmd = which("cmd")
    pm = which("pm")
    queries: list[list[str]] = []
    if cmd:
        queries.append([cmd, "package", "path", "com.termux.boot"])
    if pm:
        queries.append([pm, "path", "com.termux.boot"])
    app = "unknown"
    for query in queries:
        result = _read_command(runner, query)
        if result is None or result.returncode != 0:
            continue
        output = result.stdout.strip()
        if any(line.strip().startswith("package:") for line in output.splitlines()):
            app = "installed"
            break
        normalized = output.lower()
        if any(message in normalized for message in (
            "unable to find package", "unknown package", "package not found",
            "was not found", "is not installed",
        )):
            app = "not_installed"
            break
        # Empty or unfamiliar successful output is ambiguous, not proof of absence.
    android_user = str(os.getuid() // 100000)
    package_enabled = "unknown"
    receiver_state = "unknown"
    package_managers = [item for item in (cmd, pm) if item]
    if package_managers:
        def package_query(*arguments: str) -> subprocess.CompletedProcess[str] | None:
            last_result = None
            for manager in package_managers:
                prefix = [manager, "package"] if manager == cmd else [manager]
                last_result = _read_command(runner, [*prefix, *arguments])
                if last_result is not None and last_result.returncode == 0:
                    return last_result
            return last_result

        enabled_result = package_query("list", "packages", "-e", "--user", android_user, "com.termux.boot")
        disabled_result = package_query("list", "packages", "-d", "--user", android_user, "com.termux.boot")
        def lists_package(result: subprocess.CompletedProcess[str] | None) -> bool:
            return result is not None and result.returncode == 0 and any(
                line.strip() == "package:com.termux.boot" for line in result.stdout.splitlines()
            )
        if lists_package(enabled_result):
            package_enabled = "enabled"
        elif lists_package(disabled_result):
            package_enabled = "disabled"

        action = "android.intent.action.BOOT_COMPLETED"
        receiver_args = ("query-receivers", "--components", "--user", android_user,
                         "-a", action, "-p", "com.termux.boot")
        active_receivers = package_query(*receiver_args)
        all_receivers = package_query("query-receivers", "--components", "--user", android_user,
                                      "--query-flags", "0x200", "-a", action, "-p", "com.termux.boot")
        def lists_receiver(result: subprocess.CompletedProcess[str] | None) -> bool:
            return result is not None and result.returncode == 0 and any(
                line.strip().startswith("com.termux.boot/") for line in result.stdout.splitlines()
            )
        active_ok = active_receivers is not None and active_receivers.returncode == 0
        all_ok = all_receivers is not None and all_receivers.returncode == 0
        if lists_receiver(active_receivers):
            receiver_state = "enabled"
        elif lists_receiver(all_receivers):
            receiver_state = "disabled"
        elif package_enabled == "enabled" and active_ok and all_ok:
            receiver_state = "absent"
    directory_status = "unknown" if boot_dir.is_symlink() else "present" if boot_dir.is_dir() else "absent"
    if directory_status == "present":
        try:
            entries = [item for item in boot_dir.iterdir() if item.is_file() and not item.is_symlink()]
        except OSError:
            entries = None
    else:
        entries = []
    return {
        "component": "termux_boot_diagnostics",
        "app": app,
        "package_enabled": package_enabled,
        "boot_completed_receiver": receiver_state,
        "system_delivery_policy": "unknown",
        "package_manager_available": bool(cmd or pm),
        "script_directory": directory_status,
        "regular_script_count": len(entries) if entries is not None else None,
        "non_executable_script_count": sum(not os.access(item, os.X_OK) for item in entries) if entries is not None else None,
        "startup_policy": "unknown" if entries is None or entries else "not_configured",
        "termux_boot_command_available": which("termux-boot") is not None,
        "safety": {"read_only": True, "package_changed": False, "script_contents_read": False},
    }


def inspect_wakelock(*, which: Callable[[str], str | None] = shutil.which) -> dict[str, object]:
    acquire = which("termux-wake-lock")
    release = which("termux-wake-unlock")
    return {
        "component": "wakelock_diagnostics",
        "acquire_command_available": acquire is not None,
        "release_command_available": release is not None,
        "active_lock_state": "unknown",
        "ownership_scope": "global_unscoped",
        "safety": {"read_only": True, "acquire_or_release_invoked": False},
    }
