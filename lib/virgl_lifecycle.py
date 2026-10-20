#!/usr/bin/env python3
"""Identity-checked Native Termux VirGL vtest server for Ternuxx PRoot clients."""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time

OWNER = "ternuxx-native-virgl-v1"
SCHEMA = 1
START_TIMEOUT = 8.0
_DISPLAY = re.compile(r"^:([0-9]{1,2})$")


class VirglError(RuntimeError):
    pass


def _paths(display: str) -> dict[str, Path | str | int]:
    match = _DISPLAY.fullmatch(display)
    if not match:
        raise VirglError("VirGL display must be a local X11 display such as :1")
    number = int(match.group(1))
    prefix = Path(os.environ.get("PREFIX", "/data/data/com.termux/files/usr"))
    home = Path(os.environ.get("HOME", str(Path.home())))
    state = Path(os.environ.get("TERNUXX_STATE_DIR", str(home / ".local/share/ternuxx")))
    gpu = state / "gpu"
    runtime = prefix / "tmp" / ".ternuxx-virgl"
    sock = runtime / f"virgl-{number}.sock"
    return {"prefix": prefix, "home": home, "state": state, "gpu": gpu,
            "record": gpu / f"virgl-{number}.json", "lock": gpu / f".virgl-{number}.lock",
            "log": gpu / f"virgl-{number}.log", "runtime": runtime, "socket": sock,
            "guest_socket": f"/tmp/.ternuxx-virgl/virgl-{number}.sock",
            "server": prefix / "bin/virgl_test_server_android", "display": display,
            "number": number}


def _require_native() -> None:
    if (not os.environ.get("TERMUX_VERSION")
            or os.environ.get("PREFIX") != "/data/data/com.termux/files/usr"):
        raise VirglError("VirGL service requires the Native Termux shell")


def _private_dir(path: Path, *, create: bool) -> None:
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        info = path.lstat()
    except OSError as exc:
        raise VirglError(f"cannot inspect private VirGL directory {path.name}") from exc
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077 or path.resolve() != path):
        raise VirglError(f"unsafe private VirGL directory: {path.name}")


def _ensure_dirs(paths: dict[str, Path | str | int]) -> None:
    state, gpu, runtime = paths["state"], paths["gpu"], paths["runtime"]
    assert isinstance(state, Path) and isinstance(gpu, Path) and isinstance(runtime, Path)
    if state.absolute() != state.resolve(strict=False):
        raise VirglError("Ternuxx state path contains a symbolic link")
    if not state.exists():
        state.mkdir(mode=0o700, parents=True)
    _private_dir(state, create=False)
    gpu.mkdir(mode=0o700, exist_ok=True)
    _private_dir(gpu, create=False)
    runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
    _private_dir(runtime, create=False)


class _Lock:
    def __init__(self, path: Path):
        self.path, self.fd = path, None

    def __enter__(self):
        flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
        self.fd = os.open(self.path, flags, 0o600)
        info = os.fstat(self.fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) & 0o077):
            os.close(self.fd)
            self.fd = None
            raise VirglError("VirGL lifecycle lock is unsafe")
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(self.fd)
            self.fd = None
            raise VirglError("another VirGL lifecycle operation is in progress") from exc
        return self

    def __exit__(self, *_args):
        if self.fd is not None:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)


def _proc(pid: int) -> dict[str, object] | None:
    root = Path("/proc") / str(pid)
    try:
        raw = (root / "stat").read_text(encoding="ascii")
        fields = raw[raw.rfind(")") + 2:].split()
        uid = (root / "status").read_text(encoding="ascii").split("Uid:", 1)[1].splitlines()[0].split()[0]
        argv = [item.decode("utf-8", "replace") for item in (root / "cmdline").read_bytes().split(b"\0") if item]
        env = (root / "environ").read_bytes().split(b"\0")
        marker = any(item == f"TERNUXX_VIRGL_OWNER={OWNER}".encode() for item in env)
        return {"pid": pid, "state": fields[0], "pgid": int(fields[2]), "sid": int(fields[3]),
                "ticks": fields[19], "uid": int(uid), "argv": argv, "marker": marker,
                "exe": os.readlink(root / "exe")}
    except (OSError, ValueError, IndexError):
        return None


def _record_read(path: Path) -> dict[str, object] | None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077 or info.st_size > 8192):
        raise VirglError("VirGL owner record is unsafe; existing state was preserved")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise VirglError("VirGL owner record is malformed; existing state was preserved") from exc
    expected = {"schema", "owner", "display", "pid", "start_ticks", "process_group",
                "server", "socket", "socket_device", "socket_inode", "status"}
    if (not isinstance(data, dict) or set(data) != expected or data.get("schema") != SCHEMA
            or data.get("owner") != OWNER or not isinstance(data.get("display"), str)
            or not _DISPLAY.fullmatch(data["display"])
            or not isinstance(data.get("pid"), int) or data["pid"] <= 0
            or not isinstance(data.get("start_ticks"), str) or not data["start_ticks"].isdigit()
            or data.get("process_group") != data.get("pid")
            or not isinstance(data.get("server"), str) or not isinstance(data.get("socket"), str)
            or type(data.get("socket_device")) is not int or type(data.get("socket_inode")) is not int
            or data.get("status") not in {"starting", "running", "stopping", "stopped", "failed"}):
        raise VirglError("VirGL owner record has an unsupported identity; existing state was preserved")
    return data


def _record_write(path: Path, data: dict[str, object]) -> None:
    fd, temporary = tempfile.mkstemp(prefix=".virgl.", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _matches(record: dict[str, object], paths: dict[str, Path | str | int]) -> dict[str, object] | None:
    process = _proc(record["pid"])
    server, sock = paths["server"], paths["socket"]
    if not process or not isinstance(server, Path) or not isinstance(sock, Path):
        return None
    if (record.get("display") != paths["display"] or record.get("server") != str(server)
            or record.get("socket") != str(sock)):
        return None
    argv = process["argv"]
    if (process["uid"] != os.getuid() or process["ticks"] != record["start_ticks"]
            or process["pgid"] != record["process_group"] or process["sid"] != record["process_group"]
            or not process["marker"] or process["state"] in {"Z", "X"}
            or str(server) not in argv or "--no-fork" not in argv
            or "--socket-path" not in argv or str(sock) not in argv):
        return None
    return process


def _socket_info(path: Path) -> os.stat_result | None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if (not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid()
            or path.is_symlink()):
        raise VirglError("VirGL socket path is not an owner-owned Unix socket; it was preserved")
    return info


def _socket_ready(path: Path, timeout: float = 0.25) -> os.stat_result | None:
    info = _socket_info(path)
    if info is None:
        return None
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(timeout)
    try:
        if client.connect_ex(str(path)) != 0:
            return None
    except OSError:
        return None
    finally:
        client.close()
    return info


def _remove_recorded_socket(record: dict[str, object], path: Path) -> None:
    info = _socket_info(path)
    if info is None:
        return
    if (record.get("socket") != str(path) or record.get("socket_device") != info.st_dev
            or record.get("socket_inode") != info.st_ino):
        raise VirglError("VirGL socket identity changed; refusing to remove it")
    path.unlink()


def _matches_lsof(paths: dict[str, Path | str | int], pid: int) -> bool:
    sock = paths["socket"]
    assert isinstance(sock, Path)
    command = shutil.which("lsof")
    if command is None:
        raise VirglError("lsof is unavailable; cannot prove VirGL has no active clients, so stop was refused")
    try:
        result = subprocess.run([command, "-nP", "-t", "-U", str(sock)], capture_output=True,
                                text=True, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise VirglError("could not inspect VirGL socket users; stop was refused") from exc
    pids: set[int] = set()
    for line in result.stdout.splitlines():
        if not line.strip().isdigit():
            raise VirglError("lsof returned ambiguous VirGL socket ownership; stop was refused")
        pids.add(int(line.strip()))
    if result.returncode not in {0, 1} or pids != {pid}:
        raise VirglError("VirGL has active or unverified socket users; stop was refused")
    return True


def status(display: str = ":1") -> dict[str, object]:
    _require_native()
    paths = _paths(display)
    record = _record_read(paths["record"])
    if record is not None:
        process = _matches(record, paths)
        if process is None:
            recorded = _proc(record["pid"])
            if recorded is None or recorded["state"] in {"Z", "X"}:
                return {"owner": "ternuxx", "state": "stale", "display": display,
                        "socket": str(paths["socket"]), "identity": "recorded-process-absent", "read_only": True}
            return {"owner": "unknown", "state": "unsafe", "display": display,
                    "identity": "record-does-not-match-live-process", "read_only": True}
        info = _socket_ready(paths["socket"])
        return {"owner": "ternuxx", "state": "running" if info else "degraded",
                "display": display, "socket": str(paths["guest_socket"]),
                "identity": "matched", "read_only": True}
    info = _socket_ready(paths["socket"])
    if info:
        return {"owner": "external", "state": "running", "display": display,
                "socket": str(paths["guest_socket"]), "identity": "no-ternuxx-owner-record", "read_only": True}
    return {"owner": "ternuxx", "state": "stopped", "display": display,
            "socket": str(paths["guest_socket"]), "identity": "no-responsive-owner-server", "read_only": True}


def _stale_cleanup(paths: dict[str, Path | str | int], record: dict[str, object]) -> None:
    pid = int(record["pid"])
    current = _proc(pid)
    if current is not None and current["state"] not in {"Z", "X"}:
        if _matches(record, paths) is None:
            raise VirglError("recorded VirGL PID is live with a different identity; nothing was changed")
        raise VirglError("recorded VirGL server is live but unhealthy; inspect status/log before retrying")
    sock = paths["socket"]
    assert isinstance(sock, Path)
    _remove_recorded_socket(record, sock)
    record["status"] = "stopped"
    _record_write(paths["record"], record)


def _abort_owned_start(child: subprocess.Popen, record: dict[str, object],
                       paths: dict[str, Path | str | int]) -> None:
    process = _matches(record, paths)
    if process is None:
        raise VirglError("VirGL startup timed out and process identity is no longer exact; no process was signaled")
    sock = paths["socket"]
    assert isinstance(sock, Path)
    info = _socket_info(sock)
    if info is not None:
        record.update({"socket_device": info.st_dev, "socket_inode": info.st_ino})
    record["status"] = "stopping"
    _record_write(paths["record"], record)
    process = _matches(record, paths)
    if process is None:
        raise VirglError("VirGL startup identity changed during recovery; no process was signaled")
    os.kill(int(record["pid"]), signal.SIGTERM)
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired as exc:
        raise VirglError("timed-out VirGL process did not stop; state and socket were retained") from exc
    if _proc(int(record["pid"])) is not None:
        raise VirglError("timed-out VirGL process remains present; state was retained")
    if record["socket_inode"]:
        _remove_recorded_socket(record, sock)
    record["status"] = "failed"
    _record_write(paths["record"], record)


def start(display: str = ":1") -> dict[str, object]:
    _require_native()
    paths = _paths(display)
    _ensure_dirs(paths)
    with _Lock(paths["lock"]):
        record = _record_read(paths["record"])
        if record:
            if record["status"] == "stopped":
                record = None
            else:
                process = _matches(record, paths)
                if process:
                    if _socket_ready(paths["socket"]) is None:
                        raise VirglError("Ternuxx VirGL process is live but its socket is not ready; refusing a duplicate")
                    return {"owner": "ternuxx", "state": "running", "display": display,
                            "socket": str(paths["guest_socket"]), "changed": False}
                old_process = _proc(int(record["pid"]))
                if old_process is not None and old_process["state"] not in {"Z", "X"}:
                    raise VirglError("VirGL owner record conflicts with a live PID; process and files were preserved")
                _stale_cleanup(paths, record)
                record = None
        sock = paths["socket"]
        assert isinstance(sock, Path)
        if sock.exists() or sock.is_symlink():
            raise VirglError("VirGL socket path exists without a matching Ternuxx owner record; it was preserved")
        server = paths["server"]
        assert isinstance(server, Path)
        if not server.is_file() or not os.access(server, os.X_OK):
            raise VirglError("virgl_test_server_android is unavailable; install the optional Native virglrenderer-android provider explicitly")
        existing = []
        try:
            entries = list(Path("/proc").iterdir())
        except OSError as exc:
            raise VirglError("cannot inspect Native process identities; refusing VirGL startup") from exc
        for entry in entries:
            if not entry.name.isdigit():
                continue
            process = _proc(int(entry.name))
            if (process and process["uid"] == os.getuid() and process["argv"]
                    and str(server) in process["argv"] and "--socket-path" in process["argv"]
                    and str(sock) in process["argv"]):
                existing.append(process["pid"])
        if existing:
            raise VirglError("a VirGL server already targets this socket without a Ternuxx owner record; refusing adoption")
        log = paths["log"]
        assert isinstance(log, Path)
        if log.exists() or log.is_symlink():
            info = log.lstat()
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or stat.S_IMODE(info.st_mode) & 0o077):
                raise VirglError("VirGL log path is unsafe; it was preserved")
        fd = os.open(log, os.O_CREAT | os.O_APPEND | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
        os.fchmod(fd, 0o600)
        env = {key: value for key, value in os.environ.items() if not key.startswith("LD_")}
        env.update({"TERNUXX_VIRGL_OWNER": OWNER, "DISPLAY": display,
                    "PREFIX": str(paths["prefix"]), "HOME": str(paths["home"])})
        try:
            with os.fdopen(fd, "ab") as stream:
                child = subprocess.Popen([str(server), "--no-fork", "--socket-path", str(sock)],
                                         stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT,
                                         env=env, close_fds=True, start_new_session=True)
        except OSError as exc:
            raise VirglError(f"could not start Native VirGL server: {exc}") from exc
        process = None
        for _ in range(30):
            process = _proc(child.pid)
            if (process and process["marker"] and process["uid"] == os.getuid()
                    and process["pgid"] == child.pid and process["sid"] == child.pid
                    and process["argv"] and str(server) in process["argv"]):
                break
            if child.poll() is not None:
                raise VirglError(f"Native VirGL server exited during startup (exit {child.returncode}); inspect private GPU log")
            time.sleep(0.05)
        if not process or not process["marker"] or process["pgid"] != child.pid or process["sid"] != child.pid:
            raise VirglError("Native VirGL process identity could not be verified; process was not signaled")
        record = {"schema": SCHEMA, "owner": OWNER, "display": display, "pid": child.pid,
                  "start_ticks": str(process["ticks"]), "process_group": child.pid,
                  "server": str(server), "socket": str(sock), "socket_device": 0,
                  "socket_inode": 0, "status": "starting"}
        _record_write(paths["record"], record)
        deadline = time.monotonic() + START_TIMEOUT
        while time.monotonic() < deadline:
            if child.poll() is not None:
                record["status"] = "failed"
                _record_write(paths["record"], record)
                raise VirglError(f"Native VirGL server exited before socket readiness (exit {child.returncode}); inspect private GPU log")
            info = _socket_ready(sock)
            if info is not None:
                os.chmod(sock, 0o600)
                info = _socket_info(sock)
                assert info is not None
                record.update({"socket_device": info.st_dev, "socket_inode": info.st_ino,
                               "status": "running"})
                _record_write(paths["record"], record)
                return {"owner": "ternuxx", "state": "running", "display": display,
                        "socket": str(paths["guest_socket"]), "changed": True}
            time.sleep(0.1)
        _abort_owned_start(child, record, paths)
        raise VirglError(f"Native VirGL socket did not become ready within {START_TIMEOUT:g} seconds; owned process was stopped")


def stop(display: str = ":1") -> dict[str, object]:
    _require_native()
    paths = _paths(display)
    _ensure_dirs(paths)
    with _Lock(paths["lock"]):
        record = _record_read(paths["record"])
        if not record or record.get("status") == "stopped":
            return {"owner": "unknown", "state": "unchanged", "display": display,
                    "changed": False, "reason": "no active Ternuxx VirGL record; no process was signaled"}
        process = _matches(record, paths)
        if process is None:
            stale_process = _proc(int(record["pid"]))
            if stale_process is not None and stale_process["state"] not in {"Z", "X"}:
                raise VirglError("VirGL process identity is ambiguous; process was not signaled")
            _stale_cleanup(paths, record)
            return {"owner": "ternuxx", "state": "stopped", "display": display,
                    "changed": False, "reason": "recorded process was absent; exact stale socket reconciled"}
        _matches_lsof(paths, int(record["pid"]))
        # Recheck after lsof: never signal a PID whose identity changed during
        # the client inspection window.
        process = _matches(record, paths)
        if process is None:
            raise VirglError("VirGL process identity changed during stop validation; nothing was signaled")
        info = _socket_info(paths["socket"])
        if info is None or info.st_dev != record["socket_device"] or info.st_ino != record["socket_inode"]:
            raise VirglError("VirGL socket identity changed; process and socket were preserved")
        record["status"] = "stopping"
        _record_write(paths["record"], record)
        os.kill(int(record["pid"]), signal.SIGTERM)
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if _matches(record, paths) is None:
                _remove_recorded_socket(record, paths["socket"])
                record["status"] = "stopped"
                _record_write(paths["record"], record)
                return {"owner": "ternuxx", "state": "stopped", "display": display,
                        "changed": True}
            time.sleep(0.1)
        raise VirglError("verified VirGL process did not stop; its state and socket were retained")


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in {"status", "start", "ensure", "stop"}:
        print("usage: virgl_lifecycle.py status|start|ensure|stop [--display :N]", file=sys.stderr)
        return 2
    action, rest = argv[0], argv[1:]
    display = ":1"
    if rest:
        if len(rest) != 2 or rest[0] != "--display":
            print("usage: virgl_lifecycle.py status|start|ensure|stop [--display :N]", file=sys.stderr)
            return 2
        display = rest[1]
    try:
        result = status(display) if action == "status" else stop(display) if action == "stop" else start(display)
        print(json.dumps({"command": "virgl", **result}, sort_keys=True))
        return 0
    except (VirglError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
