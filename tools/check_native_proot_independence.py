#!/usr/bin/env python3
"""Exercise read-only Native core commands with a failing proot-distro on PATH."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
PREFIX = Path(os.environ.get("PREFIX", ""))
PROBES = {
    "cli_help": ["./tx", "--help"],
    "management_catalog": ["./tx", "mng", "catalog", "list", "--json"],
    "boot_helper_status": ["./tx", "mng", "boot", "helpers", "status", "--json"],
    "native_graphics_status": ["./tx", "graphics", "native", "status", "--json"],
    "ssh_diagnostics": ["./tx", "ssh", "inspect", "--json"],
    "recovery_status": ["./tx", "recovery", "status", "--json"],
    "doctor": ["./tx", "doctor", "--json"],
}


def main() -> int:
    if "com.termux/files/usr" not in str(PREFIX) or not (ROOT / "tx").is_file():
        raise SystemExit("Run this check from the Native Termux Ternuxx checkout.")
    shell = PREFIX / "bin/sh"
    if not shell.is_file():
        raise SystemExit("Native Termux shell was not found under PREFIX.")

    results: dict[str, dict[str, object]] = {}
    with tempfile.TemporaryDirectory(prefix="ternuxx-broken-proot-") as temporary:
        marker = Path(temporary) / "proot-distro.called"
        shim = Path(temporary) / "proot-distro"
        shim.write_text(
            f"#!{shell}\ntouch {shlex.quote(str(marker))}\n"
            "echo injected-proot-distro-failure >&2\nexit 127\n",
            encoding="utf-8",
        )
        shim.chmod(0o700)
        env = dict(os.environ)
        env["PATH"] = f"{temporary}{os.pathsep}{env.get('PATH', '')}"

        for name, command in PROBES.items():
            run = subprocess.run(
                command, cwd=ROOT, env=env, text=True, capture_output=True, timeout=30
            )
            entry: dict[str, object] = {"exit_code": run.returncode}
            if name == "cli_help":
                entry["passed"] = run.returncode == 0 and "Ternuxx" in run.stdout
            else:
                try:
                    payload = json.loads(run.stdout)
                except json.JSONDecodeError as exc:
                    entry.update(passed=False, error=f"invalid JSON: {exc}")
                else:
                    entry["passed"] = run.returncode in (0, 1)
                    entry["ok"] = payload.get("ok")
                    if name == "doctor":
                        findings = [
                            item for item in payload.get("findings", [])
                            if item.get("id") == "NTX-PROOT-001"
                        ]
                        entry["overall"] = payload.get("overall")
                        entry["read_only"] = payload.get("read_only")
                        entry["proot_finding"] = (
                            {
                                "severity": findings[0].get("severity"),
                                "observed": findings[0].get("observed"),
                            }
                            if findings else None
                        )
                        entry["passed"] = bool(
                            entry["passed"]
                            and payload.get("read_only") is True
                            and (
                                not findings
                                or findings[0].get("severity") == "info"
                            )
                        )
                    else:
                        entry["passed"] = bool(
                            entry["passed"] and payload.get("ok") is True
                        )
            results[name] = entry

        shim_invoked = marker.is_file()

    print(json.dumps({
        "scenario": "proot-distro command fails with exit 127",
        "shim_invoked": shim_invoked,
        "guest_mutation_command_run": False,
        "results": results,
    }, indent=2, sort_keys=True))
    passed = shim_invoked and all(item.get("passed") for item in results.values())
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
