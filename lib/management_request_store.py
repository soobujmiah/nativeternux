"""Private durable idempotency markers and sanitized management audit events."""
from __future__ import annotations

import datetime as dt
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import stat
import tempfile
import threading
import time
from collections.abc import Callable

import management_authorization
import management_sessions


MAX_AUDIT_BYTES = 4 * 1024 * 1024
MAX_IDEMPOTENCY_RECORDS = 2048
IDEMPOTENCY_RETENTION_SECONDS = 24 * 60 * 60
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
SESSION_REF_RE = re.compile(r"^[A-Za-z0-9_-]{16,96}$")
IDEMPOTENCY_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{16,96}$")
FINGERPRINT_RE = re.compile(r"^[a-f0-9]{64}$")


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _safe_directory(path: Path, *, create: bool) -> None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        if not create:
            raise ValueError("management state directory is missing")
        path.mkdir(mode=0o700)
        metadata = path.lstat()
    if (stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) != 0o700
            or metadata.st_uid != os.getuid()):
        raise ValueError("management state directory is not private and owned")


def _private_state_root(home: str | os.PathLike[str], state_dir: str | os.PathLike[str], *, create: bool) -> Path:
    home_path = Path(home).expanduser().resolve()
    state_lexical = Path(state_dir).expanduser()
    if not state_lexical.is_absolute():
        raise ValueError("management state path must be absolute")
    absolute = state_lexical.absolute()
    try:
        relative = absolute.relative_to(home_path)
    except ValueError as exc:
        raise ValueError("management state path must remain inside HOME") from exc
    current = home_path
    for part in relative.parts:
        current = current / part
        try:
            if current.is_symlink():
                raise ValueError("management state path contains a symbolic link")
        except OSError as exc:
            raise ValueError("management state path cannot be inspected") from exc
    state_path = state_lexical.resolve(strict=False)
    if state_path == home_path or home_path not in state_path.parents:
        raise ValueError("management state path must remain below HOME")
    _safe_directory(state_path, create=create)
    root = state_path / "management-api"
    _safe_directory(root, create=create)
    records = root / "idempotency"
    _safe_directory(records, create=create)
    return root


class ManagementRequestStore:
    """Durable at-most-once mutation markers with a secret-free audit trail.

    Records intentionally omit request bodies, arguments, token values, and
    operation responses. A completed duplicate is identified but never
    re-dispatched; the caller must query fresh state for its current outcome.
    """

    durable = True

    def __init__(
        self,
        *,
        home: str | os.PathLike[str],
        state_dir: str | os.PathLike[str],
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.root = _private_state_root(home, state_dir, create=True)
        self.records = self.root / "idempotency"
        self.audit_path = self.root / "audit.jsonl"
        self.lock_path = self.root / ".request-store.lock"
        self._clock = clock
        self._thread_lock = threading.RLock()
        self._ensure_regular_file(self.lock_path, create=True)
        if self.audit_path.exists() or self.audit_path.is_symlink():
            self._ensure_regular_file(self.audit_path, create=False)

    @staticmethod
    def _ensure_regular_file(path: Path, *, create: bool) -> None:
        flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
        if create:
            flags |= os.O_CREAT
        try:
            fd = os.open(path, flags, 0o600)
        except OSError as exc:
            raise ValueError("management request store file is unsafe") from exc
        try:
            metadata = os.fstat(fd)
            if (not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600
                    or metadata.st_uid != os.getuid()):
                raise ValueError("management request store file is not private and owned")
        finally:
            os.close(fd)

    def begin(
        self,
        *,
        session_ref: str,
        idempotency_key: str,
        fingerprint: str,
        request_id: str,
        operation: str,
    ) -> str:
        self._validate_identifiers(session_ref, idempotency_key, fingerprint, request_id, operation)
        key_hash = hashlib.sha256(f"{session_ref}\0{idempotency_key}".encode()).hexdigest()
        record_path = self.records / f"{key_hash}.json"
        with self._locked():
            self._prune_records()
            if record_path.exists() or record_path.is_symlink():
                record = self._read_record(record_path)
                if record["fingerprint"] != fingerprint:
                    return "conflict"
                return "completed" if record["state"] == "completed" else "in_progress"
            if len(list(self.records.glob("*.json"))) >= MAX_IDEMPOTENCY_RECORDS:
                raise RuntimeError("durable idempotency capacity reached")
            now = self._clock()
            record = {
                "schema_version": 1,
                "session_ref": session_ref,
                "idempotency_key_sha256": hashlib.sha256(idempotency_key.encode()).hexdigest(),
                "fingerprint": fingerprint,
                "request_id": request_id,
                "operation": operation,
                "capability": management_authorization.required_capability(operation),
                "state": "in_progress",
                "created_at_epoch": now,
                "created_at_utc": _utc_now(),
                "updated_at_utc": _utc_now(),
            }
            self._atomic_write(record_path, record)
            self._audit(record, "started", None, 0)
            return "new"

    def complete(
        self,
        *,
        session_ref: str,
        idempotency_key: str,
        fingerprint: str,
        http_status: int,
        outcome: str,
        duration_ms: int,
    ) -> None:
        if outcome not in {"succeeded", "failed", "unknown"}:
            raise ValueError("invalid management operation outcome")
        if type(http_status) is not int or not 100 <= http_status <= 599:
            raise ValueError("invalid management HTTP status")
        if type(duration_ms) is not int or not 0 <= duration_ms <= 24 * 60 * 60 * 1000:
            raise ValueError("invalid management operation duration")
        key_hash = hashlib.sha256(f"{session_ref}\0{idempotency_key}".encode()).hexdigest()
        record_path = self.records / f"{key_hash}.json"
        with self._locked():
            record = self._read_record(record_path)
            if record["fingerprint"] != fingerprint or record["state"] != "in_progress":
                raise RuntimeError("idempotency record changed before completion")
            record["state"] = "completed"
            record["outcome"] = outcome
            record["http_status"] = http_status
            record["duration_ms"] = duration_ms
            record["updated_at_utc"] = _utc_now()
            self._atomic_write(record_path, record)
            self._audit(record, outcome, http_status, duration_ms)

    def _validate_identifiers(self, session_ref: str, key: str, fingerprint: str,
                              request_id: str, operation: str) -> None:
        if not isinstance(session_ref, str) or not SESSION_REF_RE.fullmatch(session_ref):
            raise ValueError("invalid management session reference")
        if not isinstance(key, str) or not IDEMPOTENCY_KEY_RE.fullmatch(key):
            raise ValueError("invalid idempotency key")
        if not isinstance(fingerprint, str) or not FINGERPRINT_RE.fullmatch(fingerprint):
            raise ValueError("invalid request fingerprint")
        if not isinstance(request_id, str) or not REQUEST_ID_RE.fullmatch(request_id):
            raise ValueError("invalid request ID")
        if operation not in management_authorization.OPERATION_CAPABILITIES:
            raise ValueError("unsupported management operation")
        if operation not in management_sessions.MUTATING_OPERATIONS:
            raise ValueError("durable request store accepts mutation operations only")

    def _read_record(self, path: Path) -> dict[str, object]:
        fd = -1
        try:
            fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            metadata = os.fstat(fd)
            if (stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode)
                    or stat.S_IMODE(metadata.st_mode) != 0o600 or metadata.st_uid != os.getuid()
                    or metadata.st_size > 16 * 1024):
                raise RuntimeError("unsafe durable idempotency record")
            chunks = bytearray()
            while len(chunks) <= 16 * 1024:
                chunk = os.read(fd, min(4096, 16 * 1024 + 1 - len(chunks)))
                if not chunk:
                    break
                chunks.extend(chunk)
            if len(chunks) > 16 * 1024:
                raise RuntimeError("durable idempotency record is oversized")
            record = json.loads(chunks.decode("utf-8"), parse_constant=self._reject_json_constant)
        except (OSError, ValueError, TypeError) as exc:
            raise RuntimeError("durable idempotency record is unreadable") from exc
        finally:
            if fd >= 0:
                os.close(fd)
        base = {"schema_version", "session_ref", "idempotency_key_sha256", "fingerprint",
                "request_id", "operation", "capability", "state", "created_at_epoch",
                "created_at_utc", "updated_at_utc"}
        state = record.get("state") if isinstance(record, dict) else None
        expected = base if state == "in_progress" else base | {"outcome", "http_status", "duration_ms"}
        if (not isinstance(record, dict) or set(record) != expected or record.get("schema_version") != 1
                or state not in {"in_progress", "completed"}
                or not isinstance(record.get("session_ref"), str)
                or not SESSION_REF_RE.fullmatch(record["session_ref"])
                or not isinstance(record.get("idempotency_key_sha256"), str)
                or not re.fullmatch(r"[a-f0-9]{64}", record["idempotency_key_sha256"])
                or not isinstance(record.get("fingerprint"), str)
                or not FINGERPRINT_RE.fullmatch(record["fingerprint"])
                or not isinstance(record.get("request_id"), str)
                or not REQUEST_ID_RE.fullmatch(record["request_id"])
                or not isinstance(record.get("operation"), str)
                or record.get("operation") not in management_sessions.MUTATING_OPERATIONS
                or record.get("capability") != management_authorization.required_capability(record.get("operation"))
                or type(record.get("created_at_epoch")) not in {int, float}
                or record.get("created_at_epoch", 0) < 0
                or record.get("created_at_epoch", 0) > 1_000_000_000_000
                or not math.isfinite(record.get("created_at_epoch", float("nan")))
                or not isinstance(record.get("created_at_utc"), str)
                or not isinstance(record.get("updated_at_utc"), str)
                or (state == "completed" and (record.get("outcome") not in {"succeeded", "failed", "unknown"}
                    or type(record.get("http_status")) is not int
                    or type(record.get("duration_ms")) is not int))):
            raise RuntimeError("durable idempotency record is malformed")
        return record

    @staticmethod
    def _reject_json_constant(value: str) -> object:
        raise ValueError(f"invalid durable idempotency constant: {value}")

    def _prune_records(self) -> None:
        now = self._clock()
        for path in self.records.glob("*.json"):
            record = self._read_record(path)
            if (record["state"] == "completed"
                    and now - float(record.get("created_at_epoch", now)) >= IDEMPOTENCY_RETENTION_SECONDS):
                path.unlink()
        self._fsync_directory(self.records)

    def _audit(self, record: dict[str, object], event: str, http_status: int | None,
               duration_ms: int) -> None:
        entry = {
            "schema_version": 1,
            "event_id": secrets.token_hex(16),
            "occurred_at_utc": _utc_now(),
            "session_ref": record["session_ref"],
            "request_id": record["request_id"],
            "operation": record["operation"],
            "capability": record["capability"],
            "event": event,
            "http_status": http_status,
            "duration_ms": duration_ms,
        }
        raw = json.dumps(entry, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"
        try:
            existing = self.audit_path.stat().st_size if self.audit_path.exists() else 0
            if existing + len(raw) > MAX_AUDIT_BYTES:
                raise RuntimeError("management audit capacity reached")
            fd = os.open(self.audit_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT |
                         getattr(os, "O_NOFOLLOW", 0), 0o600)
            try:
                metadata = os.fstat(fd)
                if (not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600
                        or metadata.st_uid != os.getuid()):
                    raise RuntimeError("management audit file is unsafe")
                written = 0
                while written < len(raw):
                    amount = os.write(fd, raw[written:])
                    if amount <= 0:
                        raise OSError("short management audit write")
                    written += amount
                os.fsync(fd)
                self._fsync_directory(self.root)
            finally:
                os.close(fd)
        except OSError as exc:
            raise RuntimeError("management audit write failed") from exc

    def _atomic_write(self, path: Path, record: dict[str, object]) -> None:
        fd, temporary = tempfile.mkstemp(prefix=".request.", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(record, stream, sort_keys=True, separators=(",", ":"), allow_nan=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, path)
            self._fsync_directory(path.parent)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    class _Guard:
        def __init__(self, store: "ManagementRequestStore") -> None:
            self.store = store
            self.fd = -1

        def __enter__(self):
            self.store._thread_lock.acquire()
            try:
                self.fd = os.open(self.store.lock_path, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
                metadata = os.fstat(self.fd)
                if (not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600
                        or metadata.st_uid != os.getuid()):
                    raise RuntimeError("management request lock is unsafe")
                fcntl.flock(self.fd, fcntl.LOCK_EX)
            except Exception:
                self.store._thread_lock.release()
                raise
            return self

        def __exit__(self, *_exc):
            try:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
                os.close(self.fd)
            finally:
                self.store._thread_lock.release()

    def _locked(self) -> "ManagementRequestStore._Guard":
        return self._Guard(self)
