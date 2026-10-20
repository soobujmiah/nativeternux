# P3 interactive PRoot TTY fixture audit — 2026-10-20

Phase: `P3`

## Scope
Native Termux checkout was used over SSH 8022. Only repository tests and phase evidence changed; no live PRoot login, desktop stop/restart, guest write, or rootfs operation was performed.

## Findings and changes
- `tests/test_proot_sessions.py` had a repeated block of registry test method names. Later definitions silently replaced the earlier definitions when Python loaded the class, so the duplicate block was removed.
- Added a fixture proving a changed numeric guest UID/GID in translated PRoot argv fails ownership verification.
- Added a fixture proving a confirmed stop targets only the recorded process group with SIGTERM.
- Existing fixture coverage verifies process start identity, private process/session group, host UID, marker, translated argv, rootfs/launcher inode, cwd directory identity, missing/unreadable process evidence, environment filtering, and explicit no-reattach health reporting.
- Source review confirms the foreground PTY loop relays input/output and terminal-size changes and restores the caller terminal on exit. There is not yet a dedicated fixture exercising byte relay, resize propagation, terminal restoration, or job-control behavior.

## Evidence
- `python3 -m unittest tests.test_proot_sessions -q`: 31 tests passed on Native Termux.
- `bash scripts/repo_test.sh`: 619 tests passed on Native Termux.
- Current Native XFCE and existing Debian GUI sessions were left untouched.
- Read-only observation of existing GUI PRoot processes showed `--change-id=1000:1000`, `--cwd=/home/sbj`, and host cwd at the rootfs directory. These are GUI sessions, not the failed interactive profile, so they do not resolve the prior interactive TTY mismatch.
- No live interactive PRoot acceptance is claimed. General attach/reconnect remains unsupported; terminal output and resize are source-reviewed, not fixture-verified yet.

## Next action
Add isolated PTY-relay fixtures for input/output, window-size propagation, terminal restoration, and supported foreground behavior. Then investigate the recorded cwd/guest-ID mismatch using read-only launcher/runtime evidence. Do not retry login in the current guest until package-owned login side effects have a safe disposable target and rollback evidence.
