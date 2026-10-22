"""Preview-first enrollment and revocation for the shared Native Termux SSH account.

Only public authorized_keys records are handled. Private keys are never accepted.
The fixed file is shared by the owner-managed 8022 channel and Ternuxx 8023.
"""
from __future__ import annotations

import fcntl
import hashlib
import os
import re
from pathlib import Path
import stat
import subprocess
import tempfile
import shutil

import ssh_key_inventory


_MAX_FILE_BYTES = 256 * 1024
_MAX_LINES = 1000
_FINGERPRINT_RE = re.compile(r"^SHA256:[A-Za-z0-9+/]{43}$")


class SshKeyMutationError(RuntimeError):
    pass


def _read_fixed(home: str | os.PathLike[str], uid: int) -> tuple[Path, bytes, int]:
    root = Path(home)
    if not root.is_absolute() or ".." in root.parts:
        raise SshKeyMutationError("Native home path is invalid")
    try:
        root_stat = root.lstat()
        ssh_dir = root / ".ssh"
        dir_stat = ssh_dir.lstat()
    except OSError as exc:
        raise SshKeyMutationError("the existing Native .ssh directory is unavailable") from exc
    if (stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode)
            or root_stat.st_uid != uid):
        raise SshKeyMutationError("Native home ownership or path is unverified")
    if (stat.S_ISLNK(dir_stat.st_mode) or not stat.S_ISDIR(dir_stat.st_mode)
            or dir_stat.st_uid != uid or stat.S_IMODE(dir_stat.st_mode) & 0o077):
        raise SshKeyMutationError("Native .ssh directory must be owned by this account and private")
    path = ssh_dir / "authorized_keys"
    try:
        before = path.lstat()
    except FileNotFoundError:
        return path, b"", 0o600
    except OSError as exc:
        raise SshKeyMutationError("authorized_keys cannot be inspected safely") from exc
    if (stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode)
            or before.st_uid != uid or before.st_size > _MAX_FILE_BYTES):
        raise SshKeyMutationError("authorized_keys type, owner, or size is unsafe")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(path, flags)
        try:
            opened = os.fstat(fd)
            if (not stat.S_ISREG(opened.st_mode) or opened.st_ino != before.st_ino
                    or opened.st_dev != before.st_dev or opened.st_uid != uid
                    or opened.st_size > _MAX_FILE_BYTES):
                raise SshKeyMutationError("authorized_keys changed during inspection")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                raw = stream.read(_MAX_FILE_BYTES + 1)
        finally:
            os.close(fd)
    except OSError as exc:
        raise SshKeyMutationError("authorized_keys cannot be read safely") from exc
    if len(raw) > _MAX_FILE_BYTES:
        raise SshKeyMutationError("authorized_keys exceeds the supported size")
    try:
        raw.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise SshKeyMutationError("authorized_keys is not valid UTF-8; no changes made") from exc
    if len(raw.splitlines()) > _MAX_LINES:
        raise SshKeyMutationError("authorized_keys exceeds the supported entry count")
    return path, raw, stat.S_IMODE(before.st_mode)


def _records(raw: bytes) -> list[bytes]:
    return raw.splitlines(keepends=True)


def _read_wire_string(blob: bytes, offset: int) -> tuple[bytes, int]:
    if offset + 4 > len(blob):
        raise ValueError("truncated SSH key")
    length = int.from_bytes(blob[offset:offset + 4], "big")
    start = offset + 4
    end = start + length
    if length == 0 or end > len(blob):
        raise ValueError("invalid SSH key field")
    return blob[start:end], end


def _validate_key_blob(public_key: str, key_type: str) -> bool:
    import base64
    import shlex
    try:
        fields = shlex.split(public_key, comments=False, posix=True)
        if len(fields) < 2 or fields[0] != key_type:
            return False
        blob = base64.b64decode(fields[1].encode("ascii"), validate=True)
        embedded_type, offset = _read_wire_string(blob, 0)
        if embedded_type.decode("ascii") != key_type:
            return False
        if key_type == "ssh-ed25519":
            key, offset = _read_wire_string(blob, offset)
            return len(key) == 32 and offset == len(blob)
        if key_type == "ssh-rsa":
            exponent, offset = _read_wire_string(blob, offset)
            modulus, offset = _read_wire_string(blob, offset)
            return bool(exponent and modulus) and offset == len(blob)
        if key_type.startswith("ecdsa-sha2-"):
            curve, offset = _read_wire_string(blob, offset)
            point, offset = _read_wire_string(blob, offset)
            curve_name = key_type.removeprefix("ecdsa-sha2-")
            expected = {"nistp256": 65, "nistp384": 97, "nistp521": 133}.get(curve_name)
            return (expected is not None and curve == curve_name.encode("ascii")
                    and len(point) == expected and point[:1] == b"\x04" and offset == len(blob))
        if key_type == "sk-ssh-ed25519@openssh.com":
            key, offset = _read_wire_string(blob, offset)
            application, offset = _read_wire_string(blob, offset)
            return len(key) == 32 and application.startswith(b"ssh:") and offset == len(blob)
    except (ValueError, UnicodeError, IndexError):
        return False
    return False


def _validate_openssh_public_key(public_key: str, expected_fingerprint: str) -> bool:
    ssh_keygen = shutil.which("ssh-keygen")
    if not ssh_keygen:
        raise SshKeyMutationError("ssh-keygen is unavailable; public-key validation failed closed")
    try:
        result = subprocess.run(
            [ssh_keygen, "-lf", "-"], input=public_key + "\n",
            capture_output=True, text=True, timeout=3, check=False,
            env={"HOME": os.environ.get("HOME", ""), "LANG": "C", "LC_ALL": "C",
                 "PATH": os.environ.get("PATH", "")},
        )
    except (OSError, subprocess.TimeoutExpired):
        raise SshKeyMutationError("ssh-keygen could not validate the public key")
    fields = result.stdout.split()
    return result.returncode == 0 and len(fields) >= 2 and fields[1] == expected_fingerprint


def _fingerprint_line(line: bytes) -> tuple[str, str] | None:
    try:
        value = line.decode("utf-8").rstrip("\r\n")
    except UnicodeError:
        return None
    parsed = ssh_key_inventory._parse_line(value)
    if not parsed or parsed.get("status") != "valid":
        return None
    return parsed["fingerprint"], parsed["key_type"]


def _payload(action: str, raw: bytes, replacement: bytes) -> bytes:
    if action == "add":
        if not raw:
            return replacement + b"\n"
        return raw + (b"" if raw.endswith(b"\n") else b"\n") + replacement + b"\n"
    return replacement


def preview(action: str, *, home: str | os.PathLike[str], uid: int,
            fingerprint: str | None = None, public_key: str | None = None) -> dict[str, object]:
    if action not in {"add", "remove"}:
        raise SshKeyMutationError("action must be add or remove")
    if action == "add":
        if (not isinstance(public_key, str) or len(public_key) > 16_384
                or any(ord(character) < 32 or ord(character) == 127 for character in public_key)):
            raise SshKeyMutationError("provide one bounded public-key line without control characters")
        parsed = ssh_key_inventory._parse_line(public_key)
        if (not parsed or parsed.get("status") != "valid"
                or (fingerprint is not None and parsed.get("fingerprint") != fingerprint)
                or not _validate_key_blob(public_key, parsed.get("key_type", ""))
                or not _validate_openssh_public_key(public_key, parsed.get("fingerprint", ""))):
            raise SshKeyMutationError("public key is malformed or its fingerprint does not match")
        fingerprint = parsed["fingerprint"]
        import shlex
        try:
            fields = shlex.split(public_key, comments=False, posix=True)
        except ValueError as exc:
            raise SshKeyMutationError("public key line is malformed") from exc
        if not fields or fields[0] != parsed.get("key_type"):
            raise SshKeyMutationError("authorized_keys options require an explicit advanced policy workflow")
        replacement = public_key.strip().encode("utf-8")
    else:
        replacement = b""
        if not isinstance(fingerprint, str) or not _FINGERPRINT_RE.fullmatch(fingerprint):
            raise SshKeyMutationError("a valid SHA256 key fingerprint is required")

    assert fingerprint is not None
    path, raw, _mode = _read_fixed(home, uid)
    records = _records(raw)
    found = []
    kept = []
    for record in records:
        item = _fingerprint_line(record)
        if item and item[0] == fingerprint:
            found.append(record)
        else:
            kept.append(record)
    if action == "add":
        exists = bool(found)
        desired = raw if exists else _payload("add", raw, replacement)
        changed = not exists
    else:
        exists = bool(found)
        if exists and not any(_fingerprint_line(record) and _fingerprint_line(record)[0] != fingerprint
                              for record in records):
            raise SshKeyMutationError(
                "cannot remove the last authorized key; enroll and verify a replacement key first")
        desired = b"".join(kept)
        changed = exists
    before_hash = hashlib.sha256(raw).hexdigest()
    after_hash = hashlib.sha256(desired).hexdigest()
    plan_material = "\0".join((action, fingerprint, before_hash, after_hash, str(uid), path.name)).encode()
    plan_id = hashlib.sha256(plan_material).hexdigest()[:24]
    sample = ssh_key_inventory._parse_line(public_key) if action == "add" and public_key else None
    if not sample and found:
        try:
            sample = ssh_key_inventory._parse_line(found[0].decode("utf-8").rstrip("\r\n"))
        except UnicodeError:
            sample = None
    return {
        "status": "ready" if changed else "already_in_requested_state",
        "action": action,
        "fingerprint": fingerprint,
        "key_type": sample.get("key_type", "unknown") if sample else "unknown",
        "target": ".ssh/authorized_keys",
        "affects_services": ["owner-managed SSH 8022", "Ternuxx managed SSH 8023"],
        "changed": changed,
        "requires_confirmation": changed,
        "plan_id": plan_id,
        "before_sha256": before_hash,
        "after_sha256": after_hash,
        "matching_entries": len(found),
        "recovery": "re-enrollment of this public key restores its access",
        "secret_values_returned": False,
    }


def apply(action: str, *, home: str | os.PathLike[str], uid: int, fingerprint: str | None = None,
          confirmed: bool, plan_id: str, public_key: str | None = None) -> dict[str, object]:
    path, _raw, _mode = _read_fixed(home, uid)
    lock_path = path.parent / ".ternuxx-authorized-keys.lock"
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        lock_fd = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise SshKeyMutationError("could not acquire the private SSH credential lock") from exc
    try:
        lock_stat = os.fstat(lock_fd)
        if not stat.S_ISREG(lock_stat.st_mode) or lock_stat.st_uid != uid:
            raise SshKeyMutationError("SSH credential lock ownership is unverified")
        os.fchmod(lock_fd, 0o600)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        plan = preview(action, home=home, uid=uid, fingerprint=fingerprint, public_key=public_key)
        if not plan["changed"]:
            return plan
        if not confirmed:
            return {**plan, "status": "confirmation_required"}
        if plan_id != plan["plan_id"]:
            return {**plan, "status": "stale_plan", "changed": False}
        fingerprint = str(plan["fingerprint"])
        _path, current, _mode = _read_fixed(home, uid)
        if action == "add":
            assert public_key is not None
            desired = _payload("add", current, public_key.strip().encode("utf-8"))
        else:
            desired = b"".join(
                record for record in _records(current)
                if not ((_fingerprint_line(record) or ("", ""))[0] == fingerprint)
            )
        if hashlib.sha256(current).hexdigest() != plan["before_sha256"] or hashlib.sha256(desired).hexdigest() != plan["after_sha256"]:
            raise SshKeyMutationError("authorized_keys changed after preview; create a new preview")
        temp_fd, temp_name = tempfile.mkstemp(prefix=".ternuxx-authorized-keys-", dir=path.parent)
        try:
            os.fchmod(temp_fd, 0o600)
            os.fchown(temp_fd, uid, -1)
            with os.fdopen(temp_fd, "wb") as stream:
                stream.write(desired)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, path)
            dir_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
        return {**plan, "status": "complete", "changed": True}
    finally:
        os.close(lock_fd)
