"""Read-only, explicit boot-profile planner for native Ternuxx."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import tempfile

import operation_journal


PROFILES = ("cli-only", "native", "proot", "hybrid")
BOOT_SCRIPT_NAME = "10-ternuxx-profile"
SCRIPT_MARKER = "# Ternuxx-managed boot profile v2"


def _state_file(home: str | os.PathLike[str], state_dir: str | os.PathLike[str]) -> Path:
    home_path = Path(home).expanduser().resolve()
    lexical_state = Path(state_dir).expanduser()
    state_path = lexical_state.resolve()
    if state_path == home_path or home_path not in state_path.parents:
        raise ValueError("state path must resolve inside Termux HOME")
    lexical_profile = lexical_state / "boot" / "profile.json"
    profile_path = lexical_profile.resolve()
    if profile_path == home_path or home_path not in profile_path.parents:
        raise ValueError("boot profile path resolves outside Termux HOME")
    for candidate in (lexical_state, lexical_state / "boot", lexical_profile):
        if candidate.is_symlink():
            raise ValueError("boot profile state path contains a symbolic link")
    return profile_path


def selected_profile(*, home: str | os.PathLike[str], state_dir: str | os.PathLike[str]) -> tuple[str, str]:
    path = _state_file(home, state_dir)
    if not path.exists():
        return "cli-only", "default"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("boot profile configuration is unreadable") from exc
    if (not isinstance(data, dict) or data.get("schema_version") != 1
            or data.get("owner") != "ternuxx" or data.get("provider") != "native"
            or data.get("profile") not in PROFILES):
        raise ValueError("boot profile configuration is invalid")
    return str(data["profile"]), "configured"


def status(*, home: str | os.PathLike[str], state_dir: str | os.PathLike[str],
           prefix: str, which=shutil.which) -> dict[str, object]:
    profile, _source = selected_profile(home=home, state_dir=state_dir)
    return preview(profile, home=home, state_dir=state_dir, prefix=prefix, which=which)


def preview(
    profile: str,
    *,
    home: str | os.PathLike[str],
    state_dir: str | os.PathLike[str],
    prefix: str,
    which=shutil.which,
) -> dict[str, object]:
    if profile not in PROFILES:
        raise ValueError("unsupported boot profile")
    if prefix != "/data/data/com.termux/files/usr":
        raise ValueError("native Termux prefix is invalid")
    configured, source = selected_profile(home=home, state_dir=state_dir)
    cli = which("ternuxx")
    x11 = which("termux-x11")
    xfce = which("xfce4-session")
    if profile == "cli-only":
        ready = True
        blockers: list[str] = []
        command = f"#!/data/data/com.termux/files/usr/bin/bash\n{SCRIPT_MARKER}\nset -eu\n# CLI-only: no desktop process is started."
    elif profile == "native":
        blockers = []
        if not cli:
            blockers.append("installed ternuxx command is unavailable")
        if not x11:
            blockers.append("termux-x11 command is unavailable")
        if not xfce:
            blockers.append("xfce4-session command is unavailable")
        ready = not blockers
        command = (
            f"#!/data/data/com.termux/files/usr/bin/bash\n"
            f"{SCRIPT_MARKER}\n"
            "set -eu\n"
            f'export PREFIX="{prefix}"\n'
            f'exec "{prefix}/bin/ternuxx" start'
        )
    else:
        ready = False
        provider = "Ternux Debian ownership-aware adapter" if profile == "proot" else "native XFCE plus Ternux workload-routing adapter"
        blockers = [f"{provider} is not implemented; no provider fallback will run"]
        command = ""
    return {
        "component": "boot_profile_preview",
        "schema_version": 1,
        "requested_profile": profile,
        "configured_profile": configured,
        "configuration_source": source,
        "ready": ready,
        "readiness_scope": "startup command prerequisites only; Termux:Boot delivery and Android background policy are not verified",
        "blockers": blockers,
        "actions": (
            ["start no graphical session; keep separately configured CLI services"]
            if profile == "cli-only" else
            ["start Ternuxx-owned native X11/XFCE", "desktop manager requests Termux:X11 Android activity; visibility remains unverified"]
            if profile == "native" and ready else
            ["no startup action; resolve the listed provider prerequisites first"]
        ),
        "generated_script": command,
        "managed_script_path": str(_boot_script_path(home)),
        "safety": {
            "read_only": True,
            "script_installed": False,
            "boot_config_changed": False,
            "existing_proot_touched": False,
            "silent_provider_fallback": False,
        },
    }


def _boot_script_path(home: str | os.PathLike[str]) -> Path:
    home_path = Path(home).expanduser().resolve()
    termux_dir = home_path / ".termux"
    boot_dir = termux_dir / "boot"
    for directory in (termux_dir, boot_dir):
        if directory.is_symlink():
            raise ValueError("Termux:Boot path contains a symbolic link")
        resolved = directory.resolve()
        if resolved == home_path or home_path not in resolved.parents:
            raise ValueError("Termux:Boot path resolves outside HOME")
        if directory.exists() and not directory.is_dir():
            raise ValueError("Termux:Boot path component is not a directory")
    return boot_dir / BOOT_SCRIPT_NAME


def _managed_script(profile: str) -> bytes:
    if profile == "cli-only":
        body = f"#!/data/data/com.termux/files/usr/bin/bash\n{SCRIPT_MARKER}\nset -eu\n# CLI-only: no desktop process is started.\n"
    elif profile == "native":
        body = (
            f"#!/data/data/com.termux/files/usr/bin/bash\n"
            f"{SCRIPT_MARKER}\n"
            "set -eu\n"
            'export PREFIX="/data/data/com.termux/files/usr"\n'
            'exec "/data/data/com.termux/files/usr/bin/ternuxx" start\n'
        )
    else:
        raise ValueError("this profile does not have a supported boot adapter")
    return body.encode("utf-8")


def _legacy_managed_script(profile: str) -> bytes:
    if profile == "cli-only":
        body = "#!/data/data/com.termux/files/usr/bin/bash\n# Ternuxx-managed boot profile v1\nset -eu\n# CLI-only: no desktop process is started.\n"
    elif profile == "native":
        body = (
            "#!/data/data/com.termux/files/usr/bin/bash\n"
            "# Ternuxx-managed boot profile v1\n"
            'export PREFIX="/data/data/com.termux/files/usr"\n'
            'exec "/data/data/com.termux/files/usr/bin/ternuxx" start\n'
        )
    else:
        raise ValueError("unsupported legacy boot profile")
    return body.encode("utf-8")


def _atomic_write(path: Path, data: bytes, mode: int) -> None:
    fd, temporary = tempfile.mkstemp(prefix=".ternuxx-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _ensure_dirs(home_path: Path, state_path: Path) -> list[Path]:
    created: list[Path] = []
    state_root = state_path.parent.parent
    state_parts = state_root.relative_to(home_path).parts
    state_chain = []
    current = home_path
    for part in state_parts:
        current = current / part
        state_chain.append(current)
    paths = list(dict.fromkeys([
        home_path / ".termux",
        home_path / ".termux" / "boot",
        *state_chain,
        state_root / "boot",
    ]))
    for path in paths:
        if path.is_symlink():
            raise ValueError("managed boot or state directory is a symbolic link")
        if path.exists():
            if not path.is_dir():
                raise ValueError("managed boot or state path is not a directory")
            continue
        path.mkdir(mode=0o700)
        os.chmod(path, 0o700)
        created.append(path)
    return created


def _restore_file(path: Path, previous: bytes | None, mode: int) -> None:
    if previous is None:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    else:
        _atomic_write(path, previous, mode)


def enable(*, profile: str, home: str | os.PathLike[str], state_dir: str | os.PathLike[str],
           prefix: str, confirmed: bool, boot_app_status: str,
           which=shutil.which) -> dict[str, object]:
    plan = preview(profile, home=home, state_dir=state_dir, prefix=prefix, which=which)
    blockers = list(plan["blockers"])
    if boot_app_status != "installed":
        blockers.append("Termux:Boot app is not positively confirmed installed")
    plan = {**plan, "blockers": blockers, "ready": not blockers,
            "boot_app_status": boot_app_status}
    if not confirmed:
        return {**plan, "requires_confirmation": True, "changed": False}
    if not plan["ready"]:
        raise ValueError("profile prerequisites are not satisfied: " + "; ".join(plan["blockers"]))
    home_path = Path(home).expanduser().resolve()
    script_path = _boot_script_path(home_path)
    state_path = _state_file(home_path, state_dir)
    desired_script = _managed_script(profile)
    config_data = (json.dumps({
        "schema_version": 1, "owner": "ternuxx", "provider": "native", "profile": profile,
    }, sort_keys=True, indent=2) + "\n").encode("utf-8")

    old_profile, old_source = selected_profile(home=home_path, state_dir=state_path.parent.parent)
    old_config = state_path.read_bytes() if old_source == "configured" else None
    if script_path.is_symlink():
        raise ValueError("refusing to replace a symbolic-link startup file")
    old_script = script_path.read_bytes() if script_path.exists() else None
    recognized_scripts = {
        _managed_script("cli-only"), _managed_script("native"),
        _legacy_managed_script("cli-only"), _legacy_managed_script("native"),
    }
    if old_script is not None and old_script not in recognized_scripts:
        raise ValueError("refusing to replace an unrecognized startup file")
    if old_profile == profile and old_script == desired_script:
        return {**plan, "requires_confirmation": False, "changed": False}

    operation_id = operation_journal.begin(
        str(state_path.parent.parent), "boot.enable", f"profile {profile}", home_dir=home_path,
    )
    created_dirs: list[Path] = []
    try:
        created_dirs = _ensure_dirs(home_path, state_path)
        _atomic_write(state_path, config_data, 0o600)
        _atomic_write(script_path, desired_script, 0o700)
        operation_journal.update(
            str(state_path.parent.parent), operation_id, "complete",
            "boot profile enabled", home_dir=home_path,
        )
    except Exception:
        rollback_ok = True
        for path, previous, mode in (
            (script_path, old_script, 0o700), (state_path, old_config, 0o600),
        ):
            try:
                _restore_file(path, previous, mode)
            except OSError:
                rollback_ok = False
        for directory in reversed(created_dirs):
            try:
                directory.rmdir()
            except OSError:
                pass
        try:
            operation_journal.update(
                str(state_path.parent.parent), operation_id,
                "failed" if rollback_ok else "needs_recovery",
                f"profile {profile}; enable failed; rollback " + ("completed" if rollback_ok else "incomplete"),
                home_dir=home_path,
            )
        except Exception:
            pass
        raise
    return {
        **plan, "requires_confirmation": False, "changed": True,
        "operation_id": operation_id,
        "safety": {
            "read_only": False, "script_installed": True, "boot_config_changed": True,
            "existing_proot_touched": False, "silent_provider_fallback": False,
        },
    }


def disable(*, home: str | os.PathLike[str], state_dir: str | os.PathLike[str],
            confirmed: bool) -> dict[str, object]:
    home_path = Path(home).expanduser().resolve()
    script_path = _boot_script_path(home_path)
    state_path = _state_file(home_path, state_dir)
    profile, source = selected_profile(home=home_path, state_dir=state_dir)
    if script_path.is_symlink():
        raise ValueError("refusing to remove a symbolic-link startup file")
    old_script = script_path.read_bytes() if script_path.exists() else None
    known_scripts = {
        _managed_script("cli-only"), _managed_script("native"),
        _legacy_managed_script("cli-only"), _legacy_managed_script("native"),
    }
    if old_script is not None and old_script not in known_scripts:
        raise ValueError("refusing to remove an unrecognized startup file")
    old_config = state_path.read_bytes() if source == "configured" else None
    preview_data = {
        "component": "boot_profile_disable",
        "schema_version": 1,
        "configured_profile": profile,
        "configuration_source": source,
        "script_path": str(script_path),
        "script_present": old_script is not None,
        "requires_confirmation": not confirmed and (old_script is not None or old_config is not None),
        "changed": False,
        "safety": {
            "read_only": not confirmed,
            "script_removed": False,
            "only_owned_paths": True,
            "existing_proot_touched": False,
        },
    }
    if not confirmed or (old_script is None and old_config is None):
        return preview_data

    operation_id = operation_journal.begin(
        str(state_path.parent.parent), "boot.disable", "disable managed boot profile",
        home_dir=home_path,
    )
    try:
        if old_script is not None:
            script_path.unlink()
        if old_config is not None:
            state_path.unlink()
        operation_journal.update(
            str(state_path.parent.parent), operation_id, "complete",
            "managed boot profile disabled", home_dir=home_path,
        )
    except Exception:
        rollback_ok = True
        for path, previous, mode in ((script_path, old_script, 0o700), (state_path, old_config, 0o600)):
            try:
                _restore_file(path, previous, mode)
            except OSError:
                rollback_ok = False
        try:
            operation_journal.update(
                str(state_path.parent.parent), operation_id,
                "failed" if rollback_ok else "needs_recovery",
                "disable failed; rollback " + ("completed" if rollback_ok else "incomplete"),
                home_dir=home_path,
            )
        except Exception:
            pass
        raise
    preview_data.update(
        requires_confirmation=False, changed=True, operation_id=operation_id,
        safety={**preview_data["safety"], "read_only": False, "script_removed": old_script is not None},
    )
    return preview_data
