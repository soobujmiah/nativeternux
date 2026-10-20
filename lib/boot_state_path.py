"""Containment checks for the optional Termux:Boot state tree."""
from __future__ import annotations
import os
from pathlib import Path
import stat

class StatePathError(ValueError):
    pass

def resolve_private_state(home_value: str, configured: str, allowed_home_root: str | None = None):
    if not isinstance(home_value, str) or not home_value or "\0" in home_value:
        raise StatePathError("HOME is empty or malformed")
    home_input = Path(home_value)
    if not home_input.is_absolute():
        raise StatePathError("HOME must be absolute")
    home = Path(os.path.abspath(home_input))
    try:
        if home.resolve(strict=True) != home:
            raise StatePathError("HOME contains a symbolic link")
    except OSError as exc:
        raise StatePathError("HOME is unavailable") from exc
    info = home.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise StatePathError("HOME ownership or permissions are unsafe")
    if allowed_home_root is not None:
        root = Path(os.path.abspath(allowed_home_root))
        try:
            home.relative_to(root)
        except ValueError as exc:
            raise StatePathError("HOME is outside the Native Termux home tree") from exc
    if not isinstance(configured, str) or not configured or "\0" in configured:
        raise StatePathError("state directory is empty or malformed")
    raw = Path(configured)
    if ".." in raw.parts:
        raise StatePathError("state directory may not contain parent traversal")
    target = Path(os.path.abspath(raw if raw.is_absolute() else home / raw))
    try:
        parts = target.relative_to(home).parts
    except ValueError as exc:
        raise StatePathError("state directory must be beneath HOME") from exc
    if not parts:
        raise StatePathError("state directory must be a strict child of HOME")
    current = home
    for index, part in enumerate(parts):
        current = current / part
        try:
            item = current.lstat()
        except FileNotFoundError:
            break
        except OSError as exc:
            raise StatePathError("state path cannot be inspected") from exc
        if stat.S_ISLNK(item.st_mode) or not stat.S_ISDIR(item.st_mode) or item.st_uid != os.getuid():
            raise StatePathError("state path component ownership or type is unsafe")
        if item.st_mode & 0o022 or (index == len(parts) - 1 and item.st_mode & 0o077):
            raise StatePathError("state path component permissions are unsafe")
    return home, target

def _open_absolute_directory(path: Path) -> int:
    flags = (os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
             | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0))
    return os.open(str(path), flags)


def _check_directory(fd: int, *, private: bool, label: str) -> None:
    info = os.fstat(fd)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise StatePathError(f"{label} ownership or type is unsafe")
    mode = stat.S_IMODE(info.st_mode)
    if (private and mode & 0o077) or (not private and mode & 0o022):
        raise StatePathError(f"{label} permissions are unsafe")


def ensure_private_tree(home: Path, target: Path) -> int:
    """Create and return an open descriptor for HOME/state/cron/boot."""
    try:
        parts = target.relative_to(home).parts
    except ValueError as exc:
        raise StatePathError("state directory must be beneath HOME") from exc
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise StatePathError("state directory components are invalid")
    fd = _open_absolute_directory(home)
    try:
        _check_directory(fd, private=False, label="HOME")
        names = [*parts, "cron", "boot"]
        for index, name in enumerate(names):
            flags = (os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
                     | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0))
            try:
                child = os.open(name, flags, dir_fd=fd)
            except FileNotFoundError:
                os.mkdir(name, mode=0o700, dir_fd=fd)
                child = os.open(name, flags, dir_fd=fd)
            except OSError as exc:
                raise StatePathError("state path changed or became unsafe") from exc
            os.close(fd)
            fd = child
            is_private = index >= len(parts) - 1
            _check_directory(fd, private=is_private, label="private state directory")
        return fd
    except BaseException:
        os.close(fd)
        raise
