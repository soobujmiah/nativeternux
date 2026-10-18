"""Read-only discovery of installed Termux PRoot distributions."""
from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path
import shutil
import subprocess
from typing import Callable


_ANSI = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
_DISTRO = re.compile(r"^\s*\*\s+([A-Za-z0-9][A-Za-z0-9_-]{0,31})\s*$")
_GUEST_USER = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")


class GuestProfileError(ValueError):
    """A Ternux profile cannot be safely used for bounded guest discovery."""


def resolve_ternux_guest_user(*, home: str | os.PathLike[str],
                              path: str | None = None,
                              which: Callable[..., str | None] = shutil.which,
                              runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run
                              ) -> str:
    """Read only the guest username from Ternux's private state file.

    The username is returned for in-process use and must never be included in a
    response, log, or evidence record. No directory or file is created.
    """
    command = which("ternux", path=path) if path is not None else which("ternux")
    if not command:
        raise GuestProfileError("installed Ternux CLI is unavailable")
    try:
        result = runner([command, "--json", "state"], capture_output=True,
                        text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GuestProfileError("Ternux state query failed") from exc
    try:
        report = json.loads(result.stdout)
    except (TypeError, json.JSONDecodeError) as exc:
        raise GuestProfileError("Ternux state response is invalid") from exc
    if (result.returncode != 0 or not isinstance(report, dict)
            or report.get("command") != "state" or report.get("status") != "ok"
            or not isinstance(report.get("state_dir"), str)
            or not isinstance(report.get("version"), str)
            or not _HOST_VERSION.fullmatch(report["version"])):
        raise GuestProfileError("Ternux state response is unsupported")

    home_path = Path(home).absolute()
    state_dir = Path(report["state_dir"])
    if not state_dir.is_absolute():
        raise GuestProfileError("Ternux state path is not absolute")
    try:
        relative = state_dir.relative_to(home_path)
    except ValueError as exc:
        raise GuestProfileError("Ternux state path is outside Termux HOME") from exc
    parts = relative.parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise GuestProfileError("Ternux state path is unsafe")

    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    file_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptors: list[int] = []
    try:
        current_fd = os.open(home_path, directory_flags)
        descriptors.append(current_fd)
        home_stat = os.fstat(current_fd)
        if (not stat.S_ISDIR(home_stat.st_mode) or home_stat.st_uid != os.getuid()
                or stat.S_IMODE(home_stat.st_mode) & 0o077):
            raise GuestProfileError("Termux HOME permissions are unsafe")
        for part in parts:
            current_fd = os.open(part, directory_flags, dir_fd=current_fd)
            descriptors.append(current_fd)
            metadata = os.fstat(current_fd)
            if (not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid()
                    or stat.S_IMODE(metadata.st_mode) & 0o077):
                raise GuestProfileError("Ternux state directory permissions are unsafe")
        state_fd = os.open("state", file_flags, dir_fd=current_fd)
        descriptors.append(state_fd)
        state_stat = os.fstat(state_fd)
        if (not stat.S_ISREG(state_stat.st_mode) or state_stat.st_uid != os.getuid()
                or stat.S_IMODE(state_stat.st_mode) != 0o600):
            raise GuestProfileError("Ternux state file permissions are unsafe")
        chunks: list[bytes] = []
        total_bytes = 0
        while True:
            chunk = os.read(state_fd, 65536)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > 1024 * 1024:
                raise GuestProfileError("Ternux state file is too large")
            chunks.append(chunk)
        text = b"".join(chunks).decode("utf-8")
    except GuestProfileError:
        raise
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise GuestProfileError("Ternux state path or file is unavailable or unsafe") from exc
    finally:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass

    users = [line.partition("=")[2].strip() for line in text.splitlines()
             if line.partition("=")[0].strip() == "user"]
    if len(users) != 1 or not _GUEST_USER.fullmatch(users[0]) or users[0] == "root":
        raise GuestProfileError("Ternux state has no unique supported non-root guest user")
    return users[0]
_DISPLAY = re.compile(r"^:(?:[0-9]|10)$")
_GUEST_VERSION = re.compile(r"^ternux guest v([0-9][A-Za-z0-9.+~-]{0,31})$")
_GUEST_SOURCE = "https://github.com/soobujmiah/ternux"
_HOST_VERSION = re.compile(r"^[0-9][A-Za-z0-9.+~-]{0,31}$")
_PULSE_SERVER = "tcp:127.0.0.1:4713"
_PULSE_INFO_VALUE = re.compile(r"^[A-Za-z0-9_.:+-]{1,128}$")
_X11_DISPLAY_TOKEN = re.compile(r"^:(?:[0-9]|10)$")


def inspect_native_pulseaudio_endpoint(
        *, which: Callable[[str], str | None] = shutil.which,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        ) -> dict[str, str | None]:
    """Read native pactl endpoint state without starting a stream or service."""
    unknown = {"status": "unknown", "server_name": None, "default_sink": None}
    command = which("pactl")
    if not command:
        return {**unknown, "status": "unavailable"}
    try:
        result = runner([command, "info"], capture_output=True, text=True,
                        timeout=5, check=False)
    except subprocess.TimeoutExpired:
        return unknown
    except OSError:
        return {**unknown, "status": "unavailable"}
    if result.returncode != 0:
        return {**unknown, "status": "unavailable"}
    if not isinstance(result.stdout, str):
        return unknown
    values: dict[str, str] = {}
    for line in result.stdout.splitlines():
        key, separator, value = line.partition(":")
        if separator and key in {"Server Name", "Default Sink"}:
            value = value.strip()
            if _PULSE_INFO_VALUE.fullmatch(value):
                values[key] = value
    server_name = values.get("Server Name")
    if not server_name:
        return unknown
    return {"status": "available", "server_name": server_name,
            "default_sink": values.get("Default Sink")}


def inspect_termux_x11_process_displays(
        *, which: Callable[[str], str | None] = shutil.which,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        ) -> dict[str, object]:
    """Summarize visible Termux:X11 display arguments without returning PIDs/argv."""
    command = which("ps")
    if not command:
        return {"status": "unavailable", "observed_displays": []}
    try:
        result = runner([command, "-A", "-o", "pid=,comm="],
                        capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "unknown", "observed_displays": []}
    if result.returncode != 0 or not isinstance(getattr(result, "stdout", None), str):
        return {"status": "unknown", "observed_displays": []}

    candidate_pids: list[str] = []
    for line in result.stdout.splitlines():
        fields = line.strip().split(None, 1)
        if (len(fields) != 2 or not fields[0].isdigit()
                or fields[1].rsplit("/", 1)[-1] != "termux-x11"):
            continue
        candidate_pids.append(fields[0])
    if len(candidate_pids) > 8:
        return {"status": "unknown", "observed_displays": []}

    displays: set[str] = set()
    for pid in candidate_pids:
        try:
            args_result = runner([command, "-p", pid, "-o", "args="],
                                 capture_output=True, text=True, timeout=5, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return {"status": "unknown", "observed_displays": []}
        if args_result.returncode != 0 or not isinstance(getattr(args_result, "stdout", None), str):
            return {"status": "unknown", "observed_displays": []}
        arguments = args_result.stdout.split()
        displays.update(token for token in arguments if _X11_DISPLAY_TOKEN.fullmatch(token))
    return {"status": "available", "observed_displays": sorted(displays)}


def _installed_names(output: str) -> list[str] | None:
    clean = _ANSI.sub("", output).replace("\r", "")
    in_installed = False
    names: list[str] = []
    for line in clean.splitlines():
        value = line.strip()
        if value.lower() == "installed containers:":
            in_installed = True
            continue
        if not in_installed:
            continue
        if value.lower().startswith("log in with:"):
            break
        match = _DISTRO.fullmatch(line)
        if match:
            names.append(match.group(1).lower())
    if not in_installed:
        return None
    return sorted(set(names))


def inspect_installed(*, which: Callable[[str], str | None] = shutil.which,
                      runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> dict[str, object]:
    manager = which("proot-distro")
    if not manager:
        return {
            "component": "proot_distribution_inventory",
            "status": "unavailable",
            "manager_available": False,
            "installed_distributions": [],
            "ownership": "unverified",
            "guest_entered": False,
            "read_only": True,
        }
    try:
        result = runner([manager, "list"], stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        result = None
    names = (_installed_names(result.stdout) if isinstance(getattr(result, "stdout", None), str)
             else None) if result is not None and result.returncode == 0 else None
    status = "unknown" if names is None else "installed" if names else "none"
    return {
        "component": "proot_distribution_inventory",
        "status": status,
        "manager_available": True,
        "installed_distributions": names or [],
        "ownership": "unverified",
        "guest_entered": False,
        "read_only": True,
    }



def inspect_native_ternux(*, which: Callable[[str], str | None] = shutil.which,
                         runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run
                         ) -> dict[str, str | None]:
    """Read Ternux's typed host status without treating it as ownership proof."""
    unknown = {
        "availability": "unavailable", "identity": "unverified", "version": None,
        "status": "unknown", "x11_running": "unknown", "pulseaudio": "unknown",
        "virgl": "unknown", "launcher": "unknown", "backend_availability": "unavailable",
        "backend": "unknown", "renderer": None, "vulkan": "unknown",
    }
    command = which("ternux")
    if not command:
        return unknown
    try:
        result = runner([command, "--json", "status"], capture_output=True, text=True,
                        timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {**unknown, "availability": "unknown"}
    try:
        data = json.loads(result.stdout) if isinstance(result.stdout, str) else None
    except (json.JSONDecodeError, TypeError):
        data = None
    if not isinstance(data, dict):
        return {**unknown, "availability": "unknown"}
    fields = (data.get("command"), data.get("status"), data.get("version"),
              data.get("x11_running"), data.get("pulseaudio"), data.get("virgl"),
              data.get("launcher"))
    command_name, status, version, x11, pulse, virgl, launcher = fields
    if (result.returncode != 0 or command_name != "status"
            or status not in {"running", "stopped"}
            or not isinstance(version, str) or not _HOST_VERSION.fullmatch(version)
            or x11 not in {"yes", "no"} or pulse not in {"running", "stopped"}
            or virgl not in {"running", "stopped"} or launcher not in {"present", "missing"}):
        return {**unknown, "availability": "unknown"}
    try:
        backend_result = runner([command, "--json", "backend", "show"], capture_output=True,
                                text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        backend_result = None
    backend_report = {"backend_availability": "unknown", "backend": "unknown",
                      "renderer": None, "vulkan": "unknown"}
    if backend_result is not None:
        try:
            backend_data = json.loads(backend_result.stdout) if isinstance(backend_result.stdout, str) else None
        except (json.JSONDecodeError, TypeError):
            backend_data = None
        if (backend_result.returncode == 0 and isinstance(backend_data, dict)
                and backend_data.get("command") == "backend" and backend_data.get("status") == "ok"
                and isinstance(backend_data.get("version"), str)
                and _HOST_VERSION.fullmatch(backend_data["version"])
                and backend_data.get("backend") in {"auto", "zink", "virgl"}
                and isinstance(backend_data.get("renderer"), str)
                and len(backend_data["renderer"]) <= 1024
                and backend_data.get("vulkan") in {"yes", "no"}):
            backend_report = {
                "backend_availability": "available", "backend": backend_data["backend"],
                "renderer": backend_data["renderer"], "vulkan": backend_data["vulkan"],
            }
    return {
        "availability": "available", "identity": "unverified", "version": version,
        "status": status, "x11_running": x11, "pulseaudio": pulse,
        "virgl": virgl, "launcher": launcher, **backend_report,
    }


def _verification_result(*, status: str, display: str, backend: str,
                         guest_entered: bool = False, version: str | None = None,
                         observed_display: str | None = None, x11: str = "unknown", audio: str = "unknown",
                         renderer: str | None = None, renderer_class: str = "unavailable",
                         blockers: list[str] | None = None,
                         native_ternux_status: dict[str, str | None] | None = None,
                         native_pulseaudio_endpoint: dict[str, str | None] | None = None
                         ) -> dict[str, object]:
    return {
        "component": "ternux_guest_diagnostics",
        "status": status,
        "distro": "debian",
        "display": display,
        "requested_backend": backend,
        "pulse_server": _PULSE_SERVER,
        "companion_version": version,
        "guest_entered": guest_entered,
        "profile_owner": "unverified",
        "native_ternux_status": native_ternux_status or inspect_native_ternux(which=lambda _name: None),
        "native_pulseaudio_endpoint": native_pulseaudio_endpoint or {
            "status": "unknown", "server_name": None, "default_sink": None},
        "checks": {"observed_display": observed_display, "x11": x11, "audio": audio,
                   "renderer_class": renderer_class, "renderer": renderer},
        "blockers": blockers or [],
        "read_only": True,
        "safety": {"packages_changed": False, "guest_write_command_invoked": False,
                    "host_lifecycle_started": False, "host_lifecycle_stopped": False,
                    "services_started": False, "services_stopped": False,
                    "host_home_and_shared_storage_unbound": True},
    }


def _guest_command(manager: str, user: str, display: str, backend: str,
                   command: str, *, prefix: str = "/data/data/com.termux/files/usr") -> list[str]:
    args = [manager, "login", "--isolated"]
    if backend == "zink":
        x11_host_dir = str(Path(prefix) / "tmp" / ".X11-unix")
        args.extend(["--bind", f"{x11_host_dir}:/tmp/.X11-unix",
                     "--bind", "/dev/kgsl-3d0:/dev/kgsl", "--bind", "/dev/dri"])
    else:
        # The VirGL server uses a socket under Termux TMPDIR; keep the guest
        # isolated from HOME/shared storage while preserving that documented route.
        args.append("--shared-tmp")
    args.append("debian")
    args.extend(["--user", user, "--env", f"DISPLAY={display}",
                 "--env", f"PULSE_SERVER={_PULSE_SERVER}"])
    if backend == "zink":
        args.extend(["--env", "MESA_LOADER_DRIVER_OVERRIDE=zink",
                     "--env", "GALLIUM_DRIVER=zink", "--env", "TU_DEBUG=sysmem,noconform",
                     "--env", "MESA_VK_WSI_DEBUG=sw", "--env", "MESA_SHADER_CACHE_DISABLE=true"])
    else:
        args.extend(["--env", "GALLIUM_DRIVER=virpipe",
                     "--env", "MESA_GL_VERSION_OVERRIDE=4.3COMPAT",
                     "--env", "MESA_SHADER_CACHE_DISABLE=true"])
    args.extend(["--", "ternux", command])
    return args


def verify_ternux_guest(*, distro: str, user: str, display: str, backend: str,
                        prefix: str = "/data/data/com.termux/files/usr",
                        which: Callable[[str], str | None] = shutil.which,
                        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> dict[str, object]:
    """Run only the version and read-only status commands of Ternux's guest CLI."""
    if distro != "debian":
        raise ValueError("the Ternux guest companion is supported only in Debian")
    if not isinstance(user, str) or not _GUEST_USER.fullmatch(user) or user == "root":
        raise ValueError("guest user must be an explicit non-root Debian username")
    if not isinstance(display, str) or not _DISPLAY.fullmatch(display):
        raise ValueError("display must be an explicit Termux:X11 display from :0 through :10")
    if backend not in {"zink", "virgl"}:
        raise ValueError("backend must be explicitly selected as zink or virgl")

    native_pulseaudio_endpoint = inspect_native_pulseaudio_endpoint(which=which, runner=runner)

    def verification_result(**values: object) -> dict[str, object]:
        values["native_pulseaudio_endpoint"] = native_pulseaudio_endpoint
        return _verification_result(**values)

    manager = which("proot-distro")
    if not manager:
        return verification_result(status="unavailable", display=display, backend=backend,
                                    blockers=["proot-distro command is unavailable"])
    try:
        inventory = runner([manager, "list"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return verification_result(status="unknown", display=display, backend=backend,
                                    blockers=["installed Debian inventory could not be read"])
    installed = (_installed_names(inventory.stdout) if isinstance(getattr(inventory, "stdout", None), str)
                 else None) if inventory.returncode == 0 else None
    if installed is None:
        return verification_result(status="unknown", display=display, backend=backend,
                                    blockers=["installed Debian inventory is unavailable or unrecognized"])
    if distro not in installed:
        return verification_result(status="not_installed", display=display, backend=backend,
                                    blockers=["Debian is not listed as an installed PRoot distribution"])

    native_ternux_status = inspect_native_ternux(which=which, runner=runner)

    try:
        version_result = runner(_guest_command(manager, user, display, backend, "--version", prefix=prefix),
                                capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return verification_result(status="unknown", display=display, backend=backend,
                                    guest_entered=True, blockers=["guest companion version check failed"],
                                    native_ternux_status=native_ternux_status)
    lines = version_result.stdout.splitlines()
    version_match = _GUEST_VERSION.fullmatch(lines[0].strip()) if lines else None
    if (version_result.returncode != 0 or not version_match or len(lines) < 2
            or lines[1].strip() != _GUEST_SOURCE):
        return verification_result(status="unsupported_companion", display=display, backend=backend,
                                    guest_entered=True,
                                    blockers=["guest command did not identify the expected Ternux companion"],
                                    native_ternux_status=native_ternux_status)
    version = version_match.group(1)

    try:
        result = runner(_guest_command(manager, user, display, backend, "status", prefix=prefix),
                        capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return verification_result(status="unknown", display=display, backend=backend,
                                    guest_entered=True, version=version,
                                    blockers=["read-only guest status command timed out or failed to start"],
                                    native_ternux_status=native_ternux_status)

    values: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key, value = key.strip().lower(), value.strip()
        if key in {"display", "x11", "audio", "renderer"}:
            values[key] = value
    observed_display = values.get("display")
    x11 = "reachable" if values.get("x11") == "reachable" else "unavailable" if "x11" in values else "unknown"
    audio = "reachable" if values.get("audio") == "PulseAudio reachable" else "unavailable" if "audio" in values else "unknown"
    renderer = values.get("renderer")
    if not renderer or renderer == "unavailable (glxinfo missing)":
        renderer, renderer_class = None, "unavailable"
    elif "llvmpipe" in renderer.lower() or "softpipe" in renderer.lower():
        renderer_class = "software"
    elif "zink" in renderer.lower() and ("turnip" in renderer.lower() or "adreno" in renderer.lower()):
        renderer_class = "zink_turnip"
    elif "virpipe" in renderer.lower() or "virgl" in renderer.lower():
        renderer_class = "virgl"
    else:
        renderer_class = "other"
    expected_renderer = "zink_turnip" if backend == "zink" else "virgl"
    blockers = []
    if observed_display is not None and observed_display != display:
        blockers.append("guest reported display does not match the requested display")
    if x11 != "reachable":
        blockers.append("guest X11 connection is not verified")
    if audio != "reachable":
        blockers.append("guest PulseAudio connection is not verified")
    if renderer_class != expected_renderer:
        blockers.append("observed renderer does not match the explicitly requested backend")
    if result.returncode != 0 and not blockers:
        blockers.append("guest status reported one or more failed checks")
    if not result.stdout.strip() and len(blockers) < 4:
        blockers.append("guest status returned no recognized output")
    if x11 == "unavailable" and observed_display == display and len(blockers) < 4:
        process_displays = inspect_termux_x11_process_displays(which=which, runner=runner)
        if (process_displays["status"] == "available"
                and display not in process_displays["observed_displays"]):
            blockers.append(
                f"requested display {display} not observed in the Termux-visible X11 process list")
    status = "complete" if not blockers and result.returncode == 0 else "partial" if values else "unknown"
    return verification_result(status=status, display=display, backend=backend,
                                guest_entered=True, version=version, observed_display=observed_display,
                                x11=x11, audio=audio,
                                renderer=renderer, renderer_class=renderer_class, blockers=blockers,
                                native_ternux_status=native_ternux_status)
