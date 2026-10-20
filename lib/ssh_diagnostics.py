#!/usr/bin/env python3
"""Read-only native OpenSSH diagnostics; never reads credential files."""

from __future__ import annotations

import argparse
import errno
from datetime import datetime, timezone
import ipaddress
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import socket
import stat
import subprocess
import sys
import time
from typing import Callable


POLICY_KEYS = {
    "port", "listenaddress", "pubkeyauthentication", "passwordauthentication",
    "kbdinteractiveauthentication", "permitrootlogin", "authenticationmethods",
}


def _decode_proc_address(value: str, ipv6: bool) -> str | None:
    try:
        raw = bytes.fromhex(value)
        if ipv6:
            if len(raw) != 16:
                return None
            # Linux procfs prints each 32-bit word in host byte order.
            raw = b"".join(raw[i:i + 4][::-1] for i in range(0, 16, 4))
        else:
            if len(raw) != 4:
                return None
            raw = raw[::-1]
        return ipaddress.ip_address(raw).compressed
    except (ValueError, TypeError):
        return None


def _read_tcp_listener_sockets(proc_root: Path) -> tuple[list[dict[str, int | str]], str]:
    listeners: set[tuple[str, int, str]] = set()
    readable = 0
    permission_denied = False
    for filename, ipv6 in (("net/tcp", False), ("net/tcp6", True)):
        try:
            rows = (proc_root / filename).read_text(encoding="ascii").splitlines()[1:]
        except OSError as exc:
            permission_denied = permission_denied or exc.errno in {errno.EACCES, errno.EPERM}
            continue
        readable += 1
        for row in rows:
            fields = row.split()
            if len(fields) < 10 or fields[3] != "0A":
                continue
            try:
                address_hex, port_hex = fields[1].split(":", 1)
                address = _decode_proc_address(address_hex, ipv6)
                port = int(port_hex, 16)
                inode = fields[9]
            except (ValueError, IndexError):
                continue
            if address is not None and 1 <= port <= 65535 and inode.isdecimal():
                listeners.add((address, port, inode))
    status = ("complete" if readable == 2 else "partial" if readable == 1
              else "permission_denied" if permission_denied else "unavailable")
    return [{"address": address, "port": port, "inode": inode}
            for address, port, inode in sorted(listeners)], status


def read_tcp_listeners(proc_root: Path) -> tuple[list[dict[str, int | str]], str]:
    sockets, status = _read_tcp_listener_sockets(proc_root)
    return [{"address": row["address"], "port": row["port"]} for row in sockets], status


def _proc_identity(proc_root: Path, pid: int) -> tuple[int, int, str] | None:
    """Read only PID, parent PID, and start ticks; never command arguments."""
    try:
        stat_line = (proc_root / str(pid) / "stat").read_text(encoding="ascii")
        comm = (proc_root / str(pid) / "comm").read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return None
    closing = stat_line.rfind(")")
    if closing < 0:
        return None
    fields = stat_line[closing + 2:].split()
    # The remainder starts at stat field 3 (state); ppid is field 4 and
    # starttime is field 22, so starttime is offset 19 in this remainder.
    if len(fields) <= 19 or not fields[1].isdecimal() or not fields[19].isdecimal():
        return None
    return pid, int(fields[1]), fields[19]


def listener_bind_scope(policy: dict[str, list[str]]) -> str:
    """Classify configured ListenAddress values without asserting network reachability."""
    values = policy.get("listenaddress", [])
    if not values:
        return "unknown"
    scopes: set[str] = set()
    for value in values:
        host, separator, _port = value.rpartition(":")
        if not separator:
            continue
        if host.startswith("[") and host.endswith("]"):
            host = host[1:-1]
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            continue
        scopes.add("wildcard" if address.is_unspecified else
                   "loopback_only" if address.is_loopback else "non_loopback")
    if not scopes:
        return "unknown"
    if "wildcard" in scopes:
        return "wildcard"
    if "non_loopback" in scopes:
        return "non_loopback"
    return "loopback_only"


def _service_policy_endpoints(policy: dict[str, list[str]]) -> set[tuple[str, int]]:
    ports: set[int] = set()
    for value in policy.get("port", []):
        try:
            port = int(value)
        except (TypeError, ValueError):
            continue
        if 1 <= port <= 65535:
            ports.add(port)
    endpoints: set[tuple[str, int]] = set()
    for value in policy.get("listenaddress", []):
        host, separator, port_text = value.rpartition(":")
        if not separator:
            continue
        if host.startswith("[") and host.endswith("]"):
            host = host[1:-1]
        try:
            address = ipaddress.ip_address(host).compressed
            port = int(port_text)
        except ValueError:
            continue
        if address and 1 <= port <= 65535 and (not ports or port in ports):
            endpoints.add((address, port))
    return endpoints


def _correlate_runit_listener(
    proc_root: Path,
    service_pid: int | None,
    policy: dict[str, list[str]],
    listeners: list[dict[str, int | str]],
    listener_status: str,
) -> str:
    """Correlate a fixed runit process tree to an SSH listener using procfs inode ownership."""
    if service_pid is None or listener_status != "complete":
        return "unknown"
    endpoints = _service_policy_endpoints(policy)
    if not endpoints:
        return "unknown"
    root_identity = _proc_identity(proc_root, service_pid)
    if root_identity is None:
        return "unknown"
    try:
        entries = list(proc_root.iterdir())
    except OSError:
        return "unknown"
    identities: dict[int, tuple[int, int, str]] = {}
    incomplete = False
    for entry in entries:
        if not entry.name.isdecimal():
            continue
        pid = int(entry.name)
        identity = _proc_identity(proc_root, pid)
        if identity is None:
            # Processes can exit during the snapshot. Treat inaccessible live
            # entries conservatively; an affirmative socket match can still prove ownership.
            try:
                (proc_root / entry.name / "stat").stat()
            except OSError:
                continue
            incomplete = True
            continue
        identities[pid] = identity
    if identities.get(service_pid) != root_identity:
        return "unknown"
    parents = {pid: identity[1] for pid, identity in identities.items()}
    tree = {service_pid}
    changed = True
    while changed:
        changed = False
        for pid, parent in parents.items():
            if parent in tree and pid not in tree:
                tree.add(pid)
                changed = True
    socket_inodes = {str(row["inode"]) for row in listeners}
    observed: set[tuple[str, int]] = set()
    for pid in tree:
        try:
            comm = (proc_root / str(pid) / "comm").read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            incomplete = True
            continue
        if comm not in {"sshd", "sshd-session"}:
            continue
        fd_dir = proc_root / str(pid) / "fd"
        try:
            fds = list(fd_dir.iterdir())
        except OSError:
            incomplete = True
            continue
        for fd in fds:
            try:
                target = os.readlink(fd)
            except OSError as exc:
                if exc.errno != 2:  # ENOENT is a normal close-during-snapshot race.
                    incomplete = True
                continue
            match = re.fullmatch(r"socket:\[(\d+)\]", target)
            if match and match.group(1) in socket_inodes:
                for row in listeners:
                    if str(row["inode"]) == match.group(1):
                        observed.add((str(row["address"]), int(row["port"])))
    if observed & endpoints:
        return "verified"
    return "unknown" if incomplete else "not_verified"


def service_definition_source(source: str | os.PathLike[str] | None = None) -> Path:
    """Locate the canonical service source for checkout and installed runtimes."""
    relative = Path("scripts/termux-services/ternuxx-sshd/run")
    if source is not None:
        return Path(source)
    configured_root = os.environ.get("TERNUXX_REPO_ROOT")
    if configured_root:
        return Path(configured_root) / relative
    checkout_source = Path(__file__).resolve().parents[1] / relative
    if checkout_source.is_file():
        return checkout_source
    return Path.home() / "ternuxx" / relative


def _managed_service_definition_identity(
    prefix: Path,
    source: str | os.PathLike[str] | None = None,
) -> dict[str, object]:
    """Compare the fixed installed runit definition with its canonical source."""
    source_path = service_definition_source(source)
    service_root = prefix / "var/service"
    service_dir = service_root / "ternuxx-sshd"
    run_path = service_dir / "run"
    try:
        root_stat = service_root.lstat()
        directory_stat = service_dir.lstat()
        run_stat = run_path.lstat()
        source_stat = source_path.stat()
        if (stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode)
                or stat.S_ISLNK(directory_stat.st_mode) or not stat.S_ISDIR(directory_stat.st_mode)
                or stat.S_ISLNK(run_stat.st_mode) or not stat.S_ISREG(run_stat.st_mode)
                or not stat.S_ISREG(source_stat.st_mode)):
            return {"status": "unsafe", "source_sha256": None, "installed_sha256": None}
        if (root_stat.st_uid != os.getuid() or directory_stat.st_uid != os.getuid()
                or run_stat.st_uid != os.getuid() or root_stat.st_mode & 0o022
                or directory_stat.st_mode & 0o022 or run_stat.st_mode & 0o022
                or not run_stat.st_mode & 0o100):
            return {"status": "unsafe", "source_sha256": None, "installed_sha256": None}
        source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        installed_hash = hashlib.sha256(run_path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return {"status": "unavailable", "source_sha256": None, "installed_sha256": None}
    except OSError:
        return {"status": "unavailable", "source_sha256": None, "installed_sha256": None}
    return {
        "status": "verified" if source_hash == installed_hash else "mismatch",
        "source_sha256": source_hash,
        "installed_sha256": installed_hash,
    }


def _proc_has_sshd(proc_root: Path) -> bool | None:
    proc = proc_root
    try:
        candidates = list(proc.iterdir())
    except OSError:
        return None
    for candidate in candidates:
        if not candidate.name.isdecimal():
            continue
        try:
            comm = (candidate / "comm").read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if comm in {"sshd", "sshd-session"}:
            return True
    # Absence from the visible procfs view is not proof that no daemon exists.
    return None


def _run_readonly(runner: Callable[..., subprocess.CompletedProcess[str]], args: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return runner(args, capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None


def _effective_policy(output: str) -> dict[str, list[str]]:
    policy: dict[str, list[str]] = {}
    for line in output.splitlines():
        fields = line.strip().split()
        if fields and fields[0].lower() in POLICY_KEYS:
            policy.setdefault(fields[0].lower(), []).append(" ".join(fields[1:]))
    return policy


def _managed_loopback_ssh_probe(
    policy: dict[str, list[str]],
    connector: Callable[..., socket.socket] = socket.create_connection,
) -> dict[str, object]:
    """Read an SSH protocol banner from one explicitly configured loopback endpoint."""
    configured_ports: set[int] = set()
    for value in policy.get("port", []):
        try:
            port = int(value)
        except (TypeError, ValueError):
            continue
        if 1 <= port <= 65535:
            configured_ports.add(port)

    endpoint: tuple[str, int] | None = None
    for value in policy.get("listenaddress", []):
        host: str
        port_text: str
        if value.startswith("[") and "]:" in value:
            host, port_text = value[1:].split("]:", 1)
        else:
            host, separator, port_text = value.rpartition(":")
            if not separator:
                continue
        try:
            address = ipaddress.ip_address(host)
            port = int(port_text)
        except ValueError:
            continue
        if address.is_loopback and port in configured_ports:
            endpoint = (address.compressed, port)
            break

    if endpoint is None:
        return {"status": "not_applicable", "address": None, "port": None}

    address, port = endpoint
    try:
        connection = connector((address, port), timeout=1.0)
    except socket.timeout:
        status = "timeout"
    except OSError:
        status = "unreachable"
    else:
        try:
            banner = connection.recv(256)
        except socket.timeout:
            status = "timeout"
        except OSError:
            status = "unreachable"
        else:
            status = "ssh_banner" if banner.startswith(b"SSH-") else "no_banner" if not banner else "unexpected_protocol"
        finally:
            try:
                connection.close()
            except OSError:
                pass
    return {"status": status, "address": address, "port": port}


def _clock_boottime_seconds() -> float | None:
    """Return kernel boot elapsed time when the platform exposes CLOCK_BOOTTIME."""
    clock_id = getattr(time, "CLOCK_BOOTTIME", None)
    if clock_id is None:
        return None
    try:
        value = time.clock_gettime(clock_id)
    except (OSError, OverflowError, ValueError):
        return None
    return value if value >= 0 else None


def _runit_service_age_seconds(status_line: str) -> int | None:
    """Parse only the fixed service's runit uptime; never retain its PID."""
    match = re.match(
        r"^run: ternuxx-sshd: \(pid [1-9][0-9]*\) (.+?)(?:, normally (?:up|down))?$",
        status_line,
    )
    if not match:
        return None
    text = match.group(1)
    parts = re.findall(r"(\d+)([dhms])", text)
    if not parts or "".join(number + unit for number, unit in parts) != re.sub(r"\s+", "", text):
        return None
    return sum(int(number) * {"d": 86400, "h": 3600, "m": 60, "s": 1}[unit]
               for number, unit in parts)


def _runit_startup_timing(
    service_state: str,
    status_line: str,
    boottime_clock: Callable[[], float | None] | None = None,
) -> dict[str, int | str | None]:
    """Compare runit service age with kernel uptime without attributing boot delivery."""
    result: dict[str, int | str | None] = {
        "status": "unavailable",
        "kernel_uptime_seconds": None,
        "runit_service_age_seconds": None,
        "seconds_after_kernel_boot": None,
    }
    if service_state == "stopped":
        result["status"] = "not_running"
        return result
    if service_state != "running":
        return result
    age = _runit_service_age_seconds(status_line)
    if age is None:
        return result
    result["runit_service_age_seconds"] = age
    clock = boottime_clock or _clock_boottime_seconds
    try:
        uptime = clock()
    except (OSError, OverflowError, ValueError):
        return result
    if uptime is None or uptime < 0:
        return result
    uptime_seconds = round(uptime)
    result["kernel_uptime_seconds"] = uptime_seconds
    delta = uptime - age
    if delta < -1:
        result["status"] = "inconsistent"
        return result
    result["status"] = "observed"
    result["seconds_after_kernel_boot"] = max(0, round(delta))
    return result


def inspect_native(
    *,
    prefix: str | os.PathLike[str],
    home: str | os.PathLike[str],
    proc_root: str | os.PathLike[str] = "/proc",
    which: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    socket_connector: Callable[..., socket.socket] = socket.create_connection,
    service_source: str | os.PathLike[str] | None = None,
    boottime_clock: Callable[[], float | None] | None = None,
) -> dict[str, object]:
    prefix_path = Path(prefix)
    home_path = Path(home)
    proc_path = Path(proc_root)
    sshd = which("sshd")
    config = prefix_path / "etc/ssh/sshd_config"
    listener_sockets, listener_status = _read_tcp_listener_sockets(proc_path)
    listener_rows = [{"address": row["address"], "port": row["port"]} for row in listener_sockets]
    report: dict[str, object] = {
        "schema_version": 1,
        "component": "native_ssh_diagnostics",
        "environment": "native_termux",
        "observed_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "checks": {
            "sshd_available": sshd is not None,
            "config_present": config.is_file(),
            "config_syntax": "unknown",
            "policy_context": "default_without_connection_context",
            "daemon_process_present": _proc_has_sshd(proc_path),
            "configured_policy": {},
            "configured_listener_bind_scope": "unknown",
            "managed_service": {
                "service_id": "ternuxx-sshd",
                "manager": "runit" if which("sv") else "not_detected",
                "status": "unknown",
                "config_present": False,
                "config_syntax": "unknown",
                "effective_policy": {},
                "listener_bind_scope": "unknown",
                "loopback_ssh_probe": {"status": "not_attempted", "address": None, "port": None},
                "definition_identity": _managed_service_definition_identity(prefix_path, service_source),
                "startup_timing": {
                    "status": "unavailable",
                    "kernel_uptime_seconds": None,
                    "runit_service_age_seconds": None,
                    "seconds_after_kernel_boot": None,
                },
            },
            "observed_tcp_listeners_all_processes": listener_rows,
            "tcp_listener_observation": listener_status,
            "listener_daemon_correlation": "not_performed",
            "service_supervisor": "runit_available" if which("sv") else "not_detected",
            "termux_boot_directory": "present" if (home_path / ".termux/boot").is_dir() else "absent",
            "configuration_owner": "unknown",
            "authenticated_connection_test": "not_run",
        },
        "safety": {"read_only": True, "credential_files_read": False, "raw_config_output_included": False},
    }
    checks = report["checks"]
    assert isinstance(checks, dict)
    managed = checks["managed_service"]
    assert isinstance(managed, dict)
    managed_config = home_path / ".config/ternuxx/sshd_recovery.conf"
    managed["config_present"] = managed_config.is_file()
    sv = which("sv")
    service_dir = prefix_path / "var/service/ternuxx-sshd"
    service_status_line = ""
    service_pid: int | None = None
    if sv:
        service_result = _run_readonly(runner, [sv, "status", str(service_dir)])
        if service_result is not None:
            service_status_line = service_result.stdout.strip().splitlines()[0] if service_result.stdout.strip() else ""
            run_prefixes = (f"run: {service_dir}: ", "run: ternuxx-sshd: ")
            down_prefixes = (f"down: {service_dir}: ", "down: ternuxx-sshd: ")
            run_prefix = next((prefix for prefix in run_prefixes if service_status_line.startswith(prefix)), None)
            down_prefix = next((prefix for prefix in down_prefixes if service_status_line.startswith(prefix)), None)
            if run_prefix is not None:
                managed["status"] = "running"
                pid_match = re.match(r"\(pid ([1-9][0-9]*)\)(?:\s|$)", service_status_line[len(run_prefix):])
                service_pid = int(pid_match.group(1)) if pid_match else None
                service_status_line = "run: ternuxx-sshd: " + service_status_line[len(run_prefix):]
            elif down_prefix is not None:
                managed["status"] = "stopped"
            else:
                managed["status"] = "unknown"
    managed["startup_timing"] = _runit_startup_timing(
        str(managed["status"]), service_status_line, boottime_clock)
    if sshd and managed_config.is_file():
        managed_syntax = _run_readonly(runner, [sshd, "-t", "-f", str(managed_config)])
        managed["config_syntax"] = "valid" if managed_syntax is not None and managed_syntax.returncode == 0 else "invalid_or_unavailable"
        if managed["config_syntax"] == "valid":
            managed_effective = _run_readonly(runner, [sshd, "-T", "-f", str(managed_config)])
            if managed_effective is not None and managed_effective.returncode == 0:
                managed["effective_policy"] = _effective_policy(managed_effective.stdout)
                managed["listener_bind_scope"] = listener_bind_scope(managed["effective_policy"])
                managed["loopback_ssh_probe"] = _managed_loopback_ssh_probe(
                    managed["effective_policy"], connector=socket_connector)
            else:
                managed["config_syntax"] = "invalid_or_unavailable"
    if managed["status"] == "running":
        if managed.get("definition_identity", {}).get("status") != "verified":
            checks["listener_daemon_correlation"] = "unknown"
        else:
            checks["listener_daemon_correlation"] = _correlate_runit_listener(
                proc_path, service_pid, managed.get("effective_policy", {}),
                listener_sockets, listener_status)
    elif managed["status"] == "stopped":
        checks["listener_daemon_correlation"] = "not_performed"
    else:
        checks["listener_daemon_correlation"] = "unknown"

    if not sshd or not config.is_file():
        return report

    syntax = _run_readonly(runner, [sshd, "-t", "-f", str(config)])
    checks["config_syntax"] = "valid" if syntax is not None and syntax.returncode == 0 else "invalid_or_unavailable"
    effective_args = [sshd, "-T", "-f", str(config)]
    try:
        native_user = pwd.getpwuid(os.getuid()).pw_name
    except (KeyError, OSError):
        native_user = ""
    if native_user:
        effective_args.extend(["-C", f"user={native_user},host=localhost,addr=127.0.0.1"])
        checks["policy_context"] = "native_user_loopback"
    effective = _run_readonly(runner, effective_args)
    if effective is not None and effective.returncode == 0:
        checks["configured_policy"] = _effective_policy(effective.stdout)
        checks["configured_listener_bind_scope"] = listener_bind_scope(checks["configured_policy"])
    else:
        checks["config_syntax"] = "invalid_or_unavailable"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tx ssh inspect")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if os.environ.get("TERMUX_VERSION") is None or os.environ.get("PREFIX") != "/data/data/com.termux/files/usr":
        result = {"error": {"code": "native_termux_required", "message": "SSH inspection must run in the native Termux shell"}}
        print(json.dumps(result) if args.json else result["error"]["message"], file=sys.stderr if not args.json else sys.stdout)
        return 2
    report = inspect_native(prefix=os.environ["PREFIX"], home=os.environ.get("HOME", ""))
    if args.json:
        print(json.dumps(report, sort_keys=True))
    else:
        checks = report["checks"]
        assert isinstance(checks, dict)
        print("Native SSH diagnostic (read-only)")
        for key in ("sshd_available", "config_present", "config_syntax", "daemon_process_present", "observed_tcp_listeners_all_processes", "listener_daemon_correlation", "service_supervisor", "termux_boot_directory", "configuration_owner", "authenticated_connection_test"):
            print(f"  {key}: {checks[key]}")
        print(f"  managed_service: {checks['managed_service']}")
        print("  Credentials and raw configuration: not read or displayed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
