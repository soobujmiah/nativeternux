#!/usr/bin/env python3
"""Inspect displays and reclaim only artifacts tied to an exact stale session."""
import errno
import os
import socket
import stat
import sys


def snapshot(path, expected):
    try:
        item = os.lstat(path)
    except FileNotFoundError:
        return None
    if item.st_uid != os.getuid() or stat.S_ISLNK(item.st_mode):
        raise RuntimeError("foreign artifact")
    if expected == "socket" and not stat.S_ISSOCK(item.st_mode):
        raise RuntimeError("not a socket")
    if expected == "lock" and not stat.S_ISREG(item.st_mode):
        raise RuntimeError("not a lock file")
    return item.st_dev, item.st_ino


def prepare(root, number):
    if not number.isdigit() or not 0 <= int(number) <= 10:
        return "busy"
    root = os.path.abspath(root)
    try:
        rstat = os.lstat(root)
        sockdir = os.path.join(root, ".X11-unix")
        dstat = os.lstat(sockdir)
        if (stat.S_ISLNK(rstat.st_mode) or not stat.S_ISDIR(rstat.st_mode)
                or rstat.st_uid != os.getuid()):
            return "busy"
        if (stat.S_ISLNK(dstat.st_mode) or not stat.S_ISDIR(dstat.st_mode)
                or dstat.st_uid != os.getuid()):
            return "busy"
    except OSError:
        return "busy"

    lock = os.path.join(root, ".X{}-lock".format(number))
    sockpath = os.path.join(sockdir, "X{}".format(number))
    try:
        lock_id = snapshot(lock, "lock")
        socket_id = snapshot(sockpath, "socket")
    except (OSError, RuntimeError):
        return "busy"
    if lock_id is None and socket_id is None:
        return "available"
    if lock_id is None:
        return "busy"

    try:
        with open(lock, "r", encoding="ascii") as stream:
            raw_pid = stream.read(64).strip()
        if not raw_pid.isdigit():
            return "busy"
        pid = int(raw_pid)
    except OSError:
        return "busy"
    if os.path.exists("/proc/{}".format(pid)):
        return "busy"

    if socket_id is not None:
        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        probe.settimeout(0.5)
        try:
            probe.connect(sockpath)
            return "busy"
        except OSError as error:
            if error.errno != errno.ECONNREFUSED:
                return "busy"
        finally:
            probe.close()

    # This is inspection only. Cleanup requires a separately authorized
    # lifecycle operation tied to a verified Ternuxx session identity.
    return "stale"


def recover(root, number, expected_pid):
    """Remove an unresponsive socket/lock pair only for its recorded dead PID."""
    if not number.isdigit() or not 0 <= int(number) <= 10 or not expected_pid.isdigit():
        return "busy"
    root = os.path.abspath(root)
    try:
        rstat = os.lstat(root)
        sockdir = os.path.join(root, ".X11-unix")
        dstat = os.lstat(sockdir)
        if (stat.S_ISLNK(rstat.st_mode) or not stat.S_ISDIR(rstat.st_mode)
                or rstat.st_uid != os.getuid()):
            return "busy"
        if (stat.S_ISLNK(dstat.st_mode) or not stat.S_ISDIR(dstat.st_mode)
                or dstat.st_uid != os.getuid()):
            return "busy"
    except OSError:
        return "busy"

    lock = os.path.join(root, ".X{}-lock".format(number))
    sockpath = os.path.join(sockdir, "X{}".format(number))
    try:
        lock_id = snapshot(lock, "lock")
        socket_id = snapshot(sockpath, "socket")
    except (OSError, RuntimeError):
        return "busy"
    if lock_id is None and socket_id is None:
        return "available"
    if lock_id is None or int(expected_pid) <= 1 or os.path.exists("/proc/{}".format(expected_pid)):
        return "busy"
    try:
        with open(lock, "r", encoding="ascii") as stream:
            if stream.read(64).strip() != expected_pid:
                return "busy"
    except OSError:
        return "busy"
    if socket_id is not None:
        probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        probe.settimeout(0.5)
        try:
            probe.connect(sockpath)
            return "busy"
        except OSError as error:
            if error.errno != errno.ECONNREFUSED:
                return "busy"
        finally:
            probe.close()

    try:
        if snapshot(lock, "lock") != lock_id or snapshot(sockpath, "socket") != socket_id:
            return "busy"
        with open(lock, "r", encoding="ascii") as stream:
            if stream.read(64).strip() != expected_pid:
                return "busy"
        if socket_id is not None:
            os.unlink(sockpath)
        if snapshot(lock, "lock") != lock_id:
            return "busy"
        os.unlink(lock)
    except OSError:
        return "busy"
    return "recovered"


if __name__ == "__main__":
    if len(sys.argv) == 3:
        result = prepare(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 5 and sys.argv[1] == "recover":
        result = recover(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        raise SystemExit(2)
    print(result)
    raise SystemExit(0 if result in ("available", "recovered") else 1)
