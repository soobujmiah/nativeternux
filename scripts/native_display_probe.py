#!/usr/bin/env python3
"""Read-only readiness probe for a local Native Termux X11 Unix socket."""
from __future__ import annotations

import os
from pathlib import Path
import re
import socket
import stat
import sys

DISPLAY_RE = re.compile(r"^:([0-9]{1,2})(?:\.[0-9]{1,2})?$")


def probe(display: str, tmp_root: str) -> tuple[bool, str]:
    match = DISPLAY_RE.fullmatch(display)
    if not match:
        return False, "DISPLAY must be a local :N display"
    root = Path(tmp_root)
    try:
        root_info = root.lstat()
    except OSError:
        return False, "local X11 temporary directory is unavailable"
    uid = os.getuid()
    if (stat.S_ISLNK(root_info.st_mode) or not stat.S_ISDIR(root_info.st_mode)
            or root_info.st_uid != uid):
        return False, "local X11 temporary directory is unsafe"
    socket_dir = root / ".X11-unix"
    try:
        dir_info = socket_dir.lstat()
    except OSError:
        return False, "local X11 socket directory is unavailable"
    if (stat.S_ISLNK(dir_info.st_mode) or not stat.S_ISDIR(dir_info.st_mode)
            or dir_info.st_uid != uid):
        return False, "local X11 socket directory is unsafe"
    socket_path = socket_dir / f"X{match.group(1)}"
    try:
        socket_info = socket_path.lstat()
    except OSError:
        return False, "local X11 socket is unavailable"
    if stat.S_ISLNK(socket_info.st_mode) or not stat.S_ISSOCK(socket_info.st_mode) or socket_info.st_uid != uid:
        return False, "local X11 socket is unsafe"
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(0.5)
    try:
        client.connect(str(socket_path))
    except OSError:
        return False, "local X11 server is not accepting connections"
    finally:
        client.close()
    return True, "ready"


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: native_display_probe.py DISPLAY TMP_ROOT", file=sys.stderr)
        raise SystemExit(2)
    ok, message = probe(sys.argv[1], sys.argv[2])
    if ok:
        print(message)
        raise SystemExit(0)
    print(message, file=sys.stderr)
    raise SystemExit(1)
