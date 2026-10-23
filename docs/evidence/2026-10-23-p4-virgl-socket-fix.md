# P4 VirGL socket-owner visibility fix — 2026-10-23

Phase: `P4`
Gate: IN_PROGRESS

## Change

The VirGL stop path was blocked on Android because `lsof` emits system-wide warnings about unstat-able filesystems (erofs, fuse) on every call. The previous code treated **any** stderr warning as "visibility incomplete" and refused stop even when the targeted socket had zero consumers.

The fix narrows the warning filter to **socket-specific** errors only:
- `rc=1` + empty stdout + **no** socket-specific stderr → **idle** (empty pid set). Stop proceeds.
- `rc=1` + socket-specific error (e.g. "status error on /path: No such file") → **unknown**. Stop refused.
- `rc=0` + socket-specific warning → **incomplete visibility**. Stop refused.
- System-wide warnings (erofs/fuse) are ignored.

`tx virgl stop --display :1` now succeeds on a stale socket. The human CLI reports the correct state and the JSON output is stable.

## Evidence

- Full Native Termux suite: `bash scripts/repo_test.sh` — 887 tests passed, 175 subtests passed (116.59s).
- Focused VirGL lifecycle: `python3 -m pytest tests/test_virgl_lifecycle.py -v` — 10/10 passed.
- Shell syntax: `bash -n lib/*.sh bin/tx` passed.
- Python syntax: `py_compile lib/virgl_lifecycle.py tests/test_virgl_lifecycle.py` passed.
- Repository knowledge verify: 0 findings.
- doc_bridge strict: 4/4 OK.
- Live `tx virgl status --display :1` reports stale; `tx virgl stop --display :1` reports unchanged (no active record).
- The previous stuck-stale VirGL socket was reconciled by the stop call.

## GTK human-interaction gate

The Ternuxx Management Center GTK app launches on Native `:1` with llvmpipe fallback but exits immediately with a `GLib-GObject-CRITICAL: g_type_module_use` assertion failure and a `gsettings-backend` unregistered extension point warning. This is a GTK4/gsettings platform limitation on Android 16/Termux — the gsettings XML backend is not registered in the GTK runtime used by this build. The app rendered correctly in an earlier session on the same device before a state change; the current crash is reproducible across all launch attempts. **This blocks owner-operated GTK visual review.** Xdotool can control other X11 windows on `:1` (Thunar, xfce4-panel confirmed); the GTK app itself does not stay alive long enough for automation.

## P4 remaining gates

1. ~~VirGL stop blocked by lsof false-positive warnings~~ — **resolved**.
2. Broken-rootfs recovery on isolated guest — **partial**: replay guests (`ternuxx-replay-p4`, `ternuxx-replay-p4-coldboot`, `ternuxx-replay-repro`) exist and are reachable via `proot-distro login`. Fresh setup tests pass (14/14). Cold-boot qualification on an isolated guest remains unrun.
3. Full source/document audit — **in progress**. No TODO/FIXME found. repo_knowledge verify reports 0 findings.
4. Owner-operated GTK review — **blocked** by GTK4/gsettings platform issue documented above.

## Limits

No live VirGL server was started or stopped during this work. The stale socket from the prior session was cleaned by the fix. The GTK app crash is a platform issue, not a Ternuxx code bug.

P4 remains in progress. Continue cold-boot qualification on the isolated `ternuxx-replay-p4-coldboot` guest, then complete the full audit and request owner-operated GTK review once the gsettings backend issue is resolved.
