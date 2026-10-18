#!/usr/bin/env python3
"""Preview-first reconciliation for interrupted native boot-profile file changes."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat

import boot_profiles
import operation_journal


class BootProfileRecoveryError(RuntimeError):
    """A boot-profile journal or managed file cannot be safely reconciled."""


def _owned_bytes(path: Path, expected_mode: int) -> bytes | None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise BootProfileRecoveryError("Managed boot-profile file cannot be inspected") from exc
    if (stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != expected_mode):
        raise BootProfileRecoveryError("Managed boot-profile file ownership or mode is unsafe")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise BootProfileRecoveryError("Managed boot-profile file cannot be read") from exc


def _snapshot(
    operation_id: str,
    *,
    home: str | os.PathLike[str],
    state_dir: str | os.PathLike[str],
) -> dict[str, object]:
    if not isinstance(operation_id, str) or len(operation_id) != 32 or any(c not in "0123456789abcdef" for c in operation_id):
        raise BootProfileRecoveryError("Operation ID is invalid")
    try:
        record = operation_journal.inspect_record(str(state_dir), operation_id, home_dir=home)
    except (OSError, ValueError, RuntimeError) as exc:
        raise BootProfileRecoveryError("Operation record is unavailable or unsafe") from exc
    kind = record.get("kind")
    status = record.get("status")
    initial_status = "starting" if kind == "boot.enable" else "stopping"
    if (kind not in {"boot.enable", "boot.disable"}
            or status not in {"needs_recovery", initial_status}):
        raise BootProfileRecoveryError("Only an interrupted boot-profile operation can be resolved")
    if kind == "boot.enable":
        detail = record.get("detail")
        requested_profile = detail.removeprefix("profile ").split(";", 1)[0] if isinstance(detail, str) else ""
        if requested_profile not in {"cli-only", "native"}:
            raise BootProfileRecoveryError("The interrupted enable operation has an unsupported profile")
    else:
        requested_profile = "absent"

    try:
        home_path = Path(home).expanduser().resolve()
        profile_path = boot_profiles._state_file(home_path, state_dir)
        script_path = boot_profiles._boot_script_path(home_path)
        profile_bytes = _owned_bytes(profile_path, 0o600)
        script_bytes = _owned_bytes(script_path, 0o700)
        observed_profile, source = boot_profiles.selected_profile(home=home_path, state_dir=state_dir)
    except (OSError, ValueError, RuntimeError) as exc:
        raise BootProfileRecoveryError("Boot-profile paths or contents are unsafe or invalid") from exc

    if script_bytes is None:
        script_state = "absent"
    elif script_bytes == boot_profiles._managed_script("cli-only"):
        script_state = "cli-only"
    elif script_bytes == boot_profiles._managed_script("native"):
        script_state = "native"
    else:
        raise BootProfileRecoveryError("Startup file is not a recognized Ternuxx-managed script")

    if kind == "boot.enable":
        state_matches = source == "configured" and observed_profile == requested_profile and script_state == requested_profile
        observed = observed_profile if source == "configured" else "absent"
    else:
        state_matches = source != "configured" and profile_bytes is None and script_bytes is None
        observed = "absent" if state_matches else observed_profile if source == "configured" else "cli-only"
    resolution = "complete" if state_matches else "failed"
    core = {
        "operation_id": operation_id,
        "record_kind": kind,
        "record_updated_at": record["updated_at"],
        "affected_paths": [str(operation_journal.record_path(str(state_dir), operation_id, home_dir=home))],
        "requested_profile": requested_profile,
        "observed_profile": observed,
        "profile_file_sha256": hashlib.sha256(profile_bytes).hexdigest() if profile_bytes is not None else None,
        "boot_script_sha256": hashlib.sha256(script_bytes).hexdigest() if script_bytes is not None else None,
        "boot_script_state": script_state,
        "state_matches_target": state_matches,
        "resolution": resolution,
    }
    plan_id = hashlib.sha256(json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        **core,
        "plan_id": plan_id,
        "requires_confirmation": True,
        "changed": False,
        "read_only": True,
        "impact": "Updates only the listed journal path; startup files and Android settings are not changed.",
    }


def preview(operation_id: str, *, home: str | os.PathLike[str], state_dir: str | os.PathLike[str]) -> dict[str, object]:
    return _snapshot(operation_id, home=home, state_dir=state_dir)


def resolve(
    operation_id: str,
    *,
    home: str | os.PathLike[str],
    state_dir: str | os.PathLike[str],
    confirmed: bool,
    plan_id: str | None,
) -> dict[str, object]:
    if type(confirmed) is not bool:
        raise BootProfileRecoveryError("Explicit confirmation is required")
    current = preview(operation_id, home=home, state_dir=state_dir)
    if not confirmed:
        return current
    if not isinstance(plan_id, str) or plan_id != current["plan_id"]:
        raise BootProfileRecoveryError("Recovery state changed or the exact preview plan ID is missing")
    verified = preview(operation_id, home=home, state_dir=state_dir)
    if verified["plan_id"] != plan_id:
        raise BootProfileRecoveryError("Boot-profile files or journal changed after preview")
    operation_journal.resolve_boot_profile_record(
        str(state_dir), operation_id, expected_kind=str(current["record_kind"]),
        expected_updated_at=str(current["record_updated_at"]), result=str(current["resolution"]),
        requested_profile=str(current["requested_profile"]), observed_profile=str(current["observed_profile"]),
        state_matches_target=bool(current["state_matches_target"]), home_dir=home,
    )
    return {
        "operation_id": operation_id,
        "resolution": current["resolution"],
        "requested_profile": current["requested_profile"],
        "observed_profile": current["observed_profile"],
        "changed": True,
        "read_only": False,
        "affected_paths": current["affected_paths"],
        "boot_files_changed": False,
    }
