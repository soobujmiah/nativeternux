"""Human-readable presentation for bounded PRoot setup results."""
from __future__ import annotations

import json
import re
import sys


def summarize(result: object) -> list[str]:
    if not isinstance(result, dict):
        raise ValueError("setup result must be an object")
    status = result.get("status")
    if status not in {"preview", "adopted"}:
        raise ValueError("setup result status is unsupported")
    operation = result.get("operation", {})
    record = result.get("record", {})
    if not isinstance(operation, dict) or not isinstance(record, dict):
        raise ValueError("setup result details are malformed")
    details = operation if operation else record
    release = details.get("guest_release", {})
    if not isinstance(release, dict):
        raise ValueError("guest release details are malformed")
    version = release.get("VERSION_ID", "unknown")
    codename = release.get("VERSION_CODENAME", "unknown")
    user = details.get("guest_user", "unknown")
    rootfs = details.get("rootfs", "existing Debian rootfs")
    if not all(isinstance(value, str) and len(value) <= 1024
               and all(ord(char) >= 32 and ord(char) != 127 for char in value)
               for value in (version, codename, user, rootfs)):
        raise ValueError("setup result contains invalid presentation values")
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", user):
        raise ValueError("guest account name is invalid")
    lines = [
        "Existing Debian guest profile " + ("preview" if status == "preview" else "recorded"),
        f"Guest: Debian {version} ({codename}) · {user}",
        f"Target: {rootfs}",
    ]
    graphics = operation.get("observed_graphics_files", {})
    if graphics:
        if not isinstance(graphics, dict):
            raise ValueError("graphics inventory is malformed")
        driver_record = graphics.get("turnip_driver", {})
        icd_record = graphics.get("turnip_icd", {})
        if not isinstance(driver_record, dict) or not isinstance(icd_record, dict):
            raise ValueError("graphics file record is malformed")
        driver = driver_record.get("status", "unknown")
        icd = icd_record.get("status", "unknown")
        if driver not in {"present", "missing"} or icd not in {"present", "missing"}:
            raise ValueError("graphics file status is unsupported")
        lines.append(f"Turnip files: driver {driver}; ICD {icd} (file presence only)")
    changes = [
        operation.get("guest_mutations", []),
        operation.get("package_changes", []),
        operation.get("service_changes", []),
    ]
    if any(not isinstance(items, list) for items in changes):
        raise ValueError("setup change inventory is malformed")
    if not any(changes):
        lines.append("Guest files, packages, services: unchanged")
    plan_id = result.get("plan_id")
    if status == "preview":
        if not isinstance(plan_id, str) or not re.fullmatch(r"[0-9a-f]{64}", plan_id):
            raise ValueError("setup preview plan ID is invalid")
        lines.extend((f"Plan ID: {plan_id}", f"Apply after review: tx install debian apply {plan_id} --yes"))
    return lines


def main() -> int:
    try:
        raw = sys.stdin.read(65537)
        if len(raw) > 65536:
            raise ValueError("setup result exceeds the presentation limit")
        result = json.loads(raw)
        print("\n".join(summarize(result)))
        return 0
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"Could not format Debian setup result: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
