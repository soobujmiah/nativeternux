#!/usr/bin/env python3
"""Preview-first removal of the obsolete Ternuxx bare-gui Bash shortcut."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

BEGIN = "# >>> Ternuxx managed Termux shortcuts >>>"
END = "# <<< Ternuxx managed Termux shortcuts <<<"
MAX_BYTES = 1024 * 1024


class ShortcutError(Exception):
    pass


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _owned_rc(home: str | os.PathLike[str]) -> tuple[Path, bytes | None, int]:
    root = Path(home)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise ShortcutError("HOME must be an existing absolute, non-symlink directory")
    path = root / ".bashrc"
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return path, None, 0o600
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid():
        raise ShortcutError(".bashrc must be a regular file owned by the current user")
    if metadata.st_size > MAX_BYTES:
        raise ShortcutError(".bashrc exceeds the safe preview size limit")
    data = path.read_bytes()
    if b"\x00" in data:
        raise ShortcutError(".bashrc contains NUL bytes")
    return path, data, stat.S_IMODE(metadata.st_mode)


def _remove_managed_block(text: str) -> str:
    begins = [m.start() for m in re.finditer(re.escape(BEGIN), text)]
    ends = [m.start() for m in re.finditer(re.escape(END), text)]
    if not begins and not ends:
        return text
    if len(begins) != 1 or len(ends) != 1 or begins[0] >= ends[0]:
        raise ShortcutError("managed shortcut markers are incomplete or duplicated")
    line_start = text.rfind("\n", 0, begins[0]) + 1
    end_newline = text.find("\n", ends[0])
    line_end = len(text) if end_newline < 0 else end_newline + 1
    return text[:line_start] + text[line_end:]


def preview(*, home: str | os.PathLike[str]) -> dict[str, object]:
    path, original, mode = _owned_rc(home)
    old = original or b""
    try:
        text = old.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ShortcutError(".bashrc is not valid UTF-8; leaving it unchanged") from exc
    new = _remove_managed_block(text).encode("utf-8")
    record = {
        "target": str(path),
        "action": "remove_obsolete_managed_gui_function",
        "original_sha256": _sha(old),
        "desired_sha256": _sha(new),
        "mode": mode,
        "changed": old != new,
        "requires_confirmation": old != new,
        "read_only": True,
    }
    record["plan_id"] = _sha(_canonical(record))
    return record

def _atomic_write(path: Path, data: bytes, mode: int) -> None:
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as stream:
            fd = -1
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        tmp = ""
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if fd >= 0:
            os.close(fd)
        if tmp:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass


def apply(*, home: str | os.PathLike[str], confirmed: bool, plan_id: str | None) -> dict[str, object]:
    if confirmed is not True:
        raise ShortcutError("explicit --yes confirmation is required")
    plan = preview(home=home)
    if not plan["changed"] or plan["plan_id"] != plan_id:
        raise ShortcutError("shell config changed after preview or exact plan ID is missing")
    path = Path(str(plan["target"]))
    _, original, mode = _owned_rc(home)
    if _sha(original or b"") != plan["original_sha256"]:
        raise ShortcutError(".bashrc changed after preview")
    try:
        text = (original or b"").decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ShortcutError(".bashrc is not valid UTF-8; leaving it unchanged") from exc
    new = _remove_managed_block(text).encode("utf-8")
    if _sha(new) != plan["desired_sha256"]:
        raise ShortcutError("shell config changed after preview")
    _atomic_write(path, new, mode)
    return {"status": "removed" if new != (original or b"") else "unchanged",
            "target": str(path), "plan_id": plan["plan_id"], "sha256": _sha(new)}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    p_preview = sub.add_parser("preview", help="preview removal of the obsolete managed gui function")
    p_preview.add_argument("--home", default=os.environ.get("HOME", ""))
    p_apply = sub.add_parser("apply", help="remove only the exact managed Ternuxx gui block from ~/.bashrc")
    p_apply.add_argument("--home", default=os.environ.get("HOME", ""))
    p_apply.add_argument("--yes", action="store_true")
    p_apply.add_argument("--plan-id")
    args = parser.parse_args()
    try:
        if args.action == "preview":
            result = preview(home=args.home)
        else:
            result = apply(home=args.home, confirmed=args.yes, plan_id=args.plan_id)
    except (ShortcutError, OSError) as exc:
        print(f"shell shortcuts: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
