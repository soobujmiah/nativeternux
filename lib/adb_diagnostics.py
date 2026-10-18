"""Read-only, loopback-only ADB server protocol diagnostics."""
from __future__ import annotations

import re
import socket
from typing import Callable


_HOST = "127.0.0.1"
_PORT = 5037
_REQUEST = b"host:version"
_MAX_VERSION_LENGTH = 8


def _recv_exact(connection: socket.socket, size: int) -> bytes | None:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = connection.recv(remaining)
        if not chunk:
            return None
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def inspect_local_server(
        *, connector: Callable[..., socket.socket] = socket.create_connection,
        ) -> dict[str, object]:
    """Query only ADB host:version on 127.0.0.1:5037.

    This direct bounded socket probe never invokes an adb executable (which
    could auto-start a server), requests no device list, and sends no device
    command. A reachable server is not proof of its process owner or bind scope.
    """
    base: dict[str, object] = {
        "component": "adb_server_diagnostics",
        "host": _HOST,
        "port": _PORT,
        "server_protocol_version_hex": None,
        "safety": {
            "read_only": True,
            "adb_executable_invoked": False,
            "server_started_or_stopped": False,
            "device_list_requested": False,
            "device_command_sent": False,
        },
    }
    try:
        connection = connector((_HOST, _PORT), timeout=1.5)
    except ConnectionRefusedError:
        return {**base, "status": "not_observed"}
    except (OSError, TimeoutError):
        return {**base, "status": "unknown"}

    try:
        connection.settimeout(1.5)
        connection.sendall(f"{len(_REQUEST):04x}".encode("ascii") + _REQUEST)
        status = _recv_exact(connection, 4)
        if status != b"OKAY":
            return {**base, "status": "protocol_error"}
        raw_length = _recv_exact(connection, 4)
        if raw_length is None or not re.fullmatch(rb"[0-9a-fA-F]{4}", raw_length):
            return {**base, "status": "protocol_error"}
        length = int(raw_length, 16)
        if not 1 <= length <= _MAX_VERSION_LENGTH:
            return {**base, "status": "protocol_error"}
        version = _recv_exact(connection, length)
        if version is None or not re.fullmatch(rb"[0-9a-fA-F]{1,8}", version):
            return {**base, "status": "protocol_error"}
        return {
            **base,
            "status": "available",
            "server_protocol_version_hex": version.decode("ascii").lower(),
        }
    except (OSError, TimeoutError):
        return {**base, "status": "unknown"}
    finally:
        try:
            connection.close()
        except OSError:
            pass
