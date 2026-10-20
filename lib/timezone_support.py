"""Timezone resolution and persistent preference for Native Termux.

Supports ordinary TZif files through zoneinfo and Android's packed tzdata
format through a bounded, read-only parser. No network access or package install
is performed here.
"""
from __future__ import annotations

import datetime as dt
import fcntl
import io
import json
import os
from pathlib import Path
import re
import stat
import struct
from functools import lru_cache
from zoneinfo import TZPATH, ZoneInfo, ZoneInfoNotFoundError, available_timezones as _zoneinfo_available_timezones

DEFAULT_TIMEZONE = "Asia/Dhaka"
SCHEMA_VERSION = 1
MAX_DATABASE_BYTES = 8 * 1024 * 1024
_ZONE_RE = re.compile(r"^[A-Za-z0-9_+.-]+(?:/[A-Za-z0-9_+.-]+)*$")
_ANDROID_DATABASES = (
    "/system/usr/share/zoneinfo/tzdata",
    "/apex/com.android.tzdata/etc/tz/tzdata",
)
_PREFIX_DATABASE = "share/zoneinfo"


class TimezoneError(ValueError):
    pass


def _valid_name(name: object) -> str:
    if (not isinstance(name, str) or not name or len(name) > 64
            or not _ZONE_RE.fullmatch(name)
            or any(part in {"", ".", ".."} for part in name.split("/"))):
        raise TimezoneError("timezone must be a valid IANA timezone name")
    return name


def _safe_database(path: str) -> tuple[bytes, str]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise TimezoneError("timezone database is unavailable") from exc
    try:
        st = os.fstat(fd)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid not in {0, 1000, os.getuid()}
                or st.st_size < 24 or st.st_size > MAX_DATABASE_BYTES
                or (st.st_mode & 0o022)):
            raise TimezoneError("timezone database identity or size is unsafe")
        chunks: list[bytes] = []
        remaining = st.st_size
        while remaining:
            part = os.read(fd, min(65536, remaining))
            if not part:
                raise TimezoneError("timezone database was truncated while reading")
            chunks.append(part)
            remaining -= len(part)
        return b"".join(chunks), path
    finally:
        os.close(fd)


def _parse_android_database(data: bytes) -> tuple[str, dict[str, tuple[int, int]]]:
    if len(data) < 24 or not data.startswith(b"tzdata") or data[11:12] != b"\0":
        raise TimezoneError("Android timezone database header is invalid")
    version_bytes = data[6:11]
    try:
        version = version_bytes.decode("ascii")
    except UnicodeDecodeError as exc:
        raise TimezoneError("Android timezone database version is invalid") from exc
    index_offset, data_offset, zonetab_offset = struct.unpack(">III", data[12:24])
    if (index_offset < 24 or index_offset > data_offset
            or data_offset > zonetab_offset or zonetab_offset > len(data)
            or (data_offset - index_offset) % 52):
        raise TimezoneError("Android timezone database offsets are invalid")
    index: dict[str, tuple[int, int]] = {}
    previous = ""
    for offset in range(index_offset, data_offset, 52):
        entry = data[offset:offset + 52]
        raw_name = entry[:40].split(b"\0", 1)[0]
        try:
            name = raw_name.decode("ascii")
        except UnicodeDecodeError as exc:
            raise TimezoneError("Android timezone database contains an invalid zone name") from exc
        _valid_name(name)
        start, length, _raw_offset = struct.unpack(">III", entry[40:52])
        if (name <= previous or length == 0 or start > zonetab_offset - data_offset
                or length > zonetab_offset - data_offset - start):
            raise TimezoneError("Android timezone database index is malformed")
        previous = name
        index[name] = (data_offset + start, length)
    return version, index


@lru_cache(maxsize=4)
def _android_index(path: str, mtime_ns: int, size: int) -> tuple[bytes, str, dict[str, tuple[int, int]]]:
    del mtime_ns, size
    data, resolved_path = _safe_database(path)
    version, index = _parse_android_database(data)
    return data, version, index


def _android_database_paths(prefix: str | None = None) -> list[str]:
    paths = list(_ANDROID_DATABASES)
    if prefix:
        paths.append(os.path.join(prefix, _PREFIX_DATABASE, "tzdata"))
    return paths


def _find_android_database(prefix: str | None = None) -> tuple[str, bytes, str, dict[str, tuple[int, int]]] | None:
    for path in _android_database_paths(prefix):
        try:
            st = os.stat(path, follow_symlinks=False)
            if not stat.S_ISREG(st.st_mode):
                continue
            data, version, index = _android_index(path, st.st_mtime_ns, st.st_size)
            return path, data, version, index
        except (OSError, TimezoneError):
            continue
    return None


def database_status(*, prefix: str | None = None) -> dict[str, object]:
    try:
        ZoneInfo("UTC")
    except (ZoneInfoNotFoundError, ValueError):
        pass
    else:
        for directory in TZPATH:
            if os.path.isdir(directory):
                return {"available": True, "provider": "tzif-zoneinfo", "version": "system-unknown",
                        "path": directory}
    packed = _find_android_database(prefix)
    if packed:
        path, _data, version, _index = packed
        return {"available": True, "provider": "android-packed-tzdata",
                "version": version, "path": path}
    return {"available": False, "provider": "unavailable", "version": None, "path": None}


def available_timezones(*, prefix: str | None = None) -> list[str]:
    names: set[str] = set()
    try:
        names.update(_zoneinfo_available_timezones())
    except (OSError, ValueError):
        pass
    for path in _android_database_paths(prefix):
        try:
            st = os.stat(path, follow_symlinks=False)
            if not stat.S_ISREG(st.st_mode):
                continue
            _data, _version, index = _android_index(path, st.st_mtime_ns, st.st_size)
            names.update(index)
        except (OSError, TimezoneError):
            continue
    names.add("UTC")
    return sorted(names)


def get_timezone(name: object, *, prefix: str | None = None) -> dt.tzinfo:
    zone_name = _valid_name(name)
    if zone_name in {"UTC", "Etc/UTC", "Etc/GMT"}:
        return dt.timezone.utc
    try:
        return ZoneInfo(zone_name)
    except (ZoneInfoNotFoundError, ValueError):
        pass
    for path in _android_database_paths(prefix):
        try:
            st = os.stat(path, follow_symlinks=False)
            if not stat.S_ISREG(st.st_mode):
                continue
            data, _version, index = _android_index(path, st.st_mtime_ns, st.st_size)
        except (OSError, TimezoneError):
            continue
        item = index.get(zone_name)
        if item:
            start, length = item
            try:
                return ZoneInfo.from_file(io.BytesIO(data[start:start + length]), key=zone_name)
            except (ValueError, OSError) as exc:
                raise TimezoneError("timezone data for this IANA name is malformed") from exc
    raise TimezoneError("timezone is unknown or unavailable; install supported timezone data")


def _state_root(state_dir: str | os.PathLike[str]) -> Path:
    root = Path(state_dir)
    if not root.is_absolute():
        raise TimezoneError("Ternuxx state directory must be absolute")
    try:
        st = root.lstat()
    except FileNotFoundError as exc:
        raise TimezoneError("Ternuxx state directory must already exist") from exc
    if root.is_symlink() or not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid():
        raise TimezoneError("Ternuxx state directory identity is unsafe")
    return root


def _read_preference(root: Path) -> dict[str, object] | None:
    path = root / "timezone.json"
    try:
        st = path.lstat()
    except FileNotFoundError:
        return None
    if path.is_symlink() or not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or (st.st_mode & 0o077):
        raise TimezoneError("timezone preference identity or permissions are unsafe")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TimezoneError("timezone preference is unreadable or corrupt") from exc
    if (not isinstance(value, dict) or set(value) != {"schema_version", "timezone", "source", "updated_at"}
            or type(value["schema_version"]) is not int or value["schema_version"] != SCHEMA_VERSION
            or not isinstance(value["source"], str) or value["source"] not in {"user", "installation"}):
        raise TimezoneError("timezone preference schema is unsupported or malformed")
    _valid_name(value["timezone"])
    try:
        timestamp = dt.datetime.fromisoformat(str(value["updated_at"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise TimezoneError("timezone preference timestamp is invalid") from exc
    if timestamp.tzinfo is None:
        raise TimezoneError("timezone preference timestamp has no timezone")
    return value


def _optional_state_root(state_dir: str | os.PathLike[str]) -> Path | None:
    root = Path(state_dir)
    try:
        root.lstat()
    except FileNotFoundError:
        return None
    return _state_root(root)


def current_timezone(state_dir: str | os.PathLike[str], *,
                     installation_timezone: str | None = None) -> str:
    root = _optional_state_root(state_dir)
    saved = _read_preference(root) if root is not None else None
    if saved:
        return str(saved["timezone"])
    candidate = installation_timezone or os.environ.get("TERNUXX_INSTALL_TIMEZONE")
    if candidate:
        _valid_name(candidate)
        return candidate
    return DEFAULT_TIMEZONE


def status(state_dir: str | os.PathLike[str], *, prefix: str | None = None,
           now: dt.datetime | None = None) -> dict[str, object]:
    root = _optional_state_root(state_dir)
    saved = _read_preference(root) if root is not None else None
    configured = str(saved["timezone"]) if saved else (
        os.environ.get("TERNUXX_INSTALL_TIMEZONE") or DEFAULT_TIMEZONE)
    source = str(saved["source"]) if saved else (
        "installation" if os.environ.get("TERNUXX_INSTALL_TIMEZONE") else "default")
    db = database_status(prefix=prefix)
    try:
        zone = get_timezone(configured, prefix=prefix)
        instant = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
        local = instant.astimezone(zone)
        available = True
        local_iso = local.isoformat()
        offset = local.strftime("%z")
        abbreviation = local.tzname()
    except TimezoneError:
        available, local_iso, offset, abbreviation = False, None, None, None
    return {
        "schema_version": SCHEMA_VERSION,
        "timezone": configured,
        "source": source,
        "configured": bool(saved) or source == "installation",
        "available": available,
        "local_time": local_iso,
        "utc_offset": offset,
        "abbreviation": abbreviation,
        "database": db,
        "ip_suggestion": "not_implemented",
    }


def set_timezone(state_dir: str | os.PathLike[str], name: object, *,
                 source: str = "user", prefix: str | None = None,
                 now: dt.datetime | None = None) -> dict[str, object]:
    zone_name = _valid_name(name)
    if not isinstance(source, str) or source not in {"user", "installation"}:
        raise TimezoneError("timezone source must be user or installation")
    get_timezone(zone_name, prefix=prefix)
    root = _state_root(state_dir)
    lock_path = root / ".timezone.lock"
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(lock_path, flags, 0o600)
    try:
        lock_stat = os.fstat(fd)
        if not stat.S_ISREG(lock_stat.st_mode) or lock_stat.st_uid != os.getuid() or (lock_stat.st_mode & 0o077):
            raise TimezoneError("timezone lock identity or permissions are unsafe")
        fcntl.flock(fd, fcntl.LOCK_EX)
        _read_preference(root)  # Refuse to overwrite corrupt or untrusted prior state.
        stamp = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "timezone": zone_name,
            "source": source,
            "updated_at": stamp.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        }
        temp = root / (".timezone." + os.urandom(8).hex() + ".tmp")
        temp_fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            with os.fdopen(temp_fd, "w", encoding="utf-8") as stream:
                json.dump(payload, stream, sort_keys=True, separators=(",", ":"), allow_nan=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, root / "timezone.json")
            os.chmod(root / "timezone.json", 0o600)
            dir_fd = os.open(root, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        finally:
            try:
                temp.unlink()
            except FileNotFoundError:
                pass
    finally:
        os.close(fd)
    return status(root, prefix=prefix, now=now)
