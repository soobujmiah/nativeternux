# GUI session reconciliation and P3 read-only recheck — 2026-10-19

## Scope and preservation

- Repository: `soobujmiah/ternuxx`, Native Termux checkout `$HOME/ternuxx`, branch `main`, HEAD `69e378eb33247678437bda4b2de9ab25f6bcb91d`.
- The worktree was already dirty with ongoing owner changes. No existing changes were reverted, staged, committed, or pushed.
- Implementation and fixtures changed only the Ternuxx checkout. No PRoot package, rootfs, workspace, launcher, display, acceleration configuration, Termux service, SSH config, boot script, or Android setting was changed.
- No live `tx gui start`, `stop`, `restart`, service lifecycle action, PRoot guest entry, UI interaction, or reboot was run.

## Root cause

`tx gui` routes to `lib/launch.sh::nt_cmd_gui`, then `lib/desktop.sh::nt_cmd_start`. The prior start path checked whether the supervisor PID identity was live; when it was not, it read `session.json.status`. Every status other than `stopped` was rejected with “A prior Ternuxx session is not verifiably stopped (state: running).” It did not reconcile the recorded supervisor, X11, and XFCE identities with current process state. Consequently a valid schema-v2 record left at `running` after its processes exited blocked a new start indefinitely.

A second related defect was that `lib/x11_display.py::prepare()` could remove a dead-PID lock and refused socket without proving that the artifacts belonged to a Ternuxx session. Generic display inspection therefore had a destructive side effect.

## Implementation

- Added `lib/desktop_session_state.py` as the shared, read-only lifecycle classifier and narrow stale-record reconciler.
- `running` now requires all three recorded identities to match `/proc` start ticks, command marker, UID, and child process-group/session identity; the recorded X11 socket and lock must match and the socket must accept a local connection.
- Added explicit `stopped`, `starting`, `running`, `stopping`, `failed`, `stale`, `unknown`, and `unsafe` states. PID reuse is treated as absence of the old process identity; unreadable process evidence stays `unknown`.
- Start now acquires the session lock before state reconciliation. It returns an existing healthy session, refuses in-progress/failed/unknown/unsafe state, and atomically changes a reverified stale record to `stopped` before normal startup. Concurrent invocations are serialized by the existing lock.
- Stop runs the same classifier before journal or signal work and refuses unknown/unsafe ownership.
- State-directory creation verifies each path component and refuses symlinks/foreign ownership. Session record reads use `O_NOFOLLOW` and verify file owner/mode.
- X11 display preparation is read-only. Stale/foreign socket or lock artifacts are preserved and block reuse.
- `desktop.status` management-service dispatch continues through the CLI JSON route, which uses the same classifier. Web mutation routes remain disabled.

## Live Native Termux evidence (read-only)

At 2026-10-19 10:06 UTC, `./tx --json gui status` returned `status=reconciliation_state=stale`, with supervisor/X11/XFCE identities absent and display artifacts absent. Direct helper inspection agreed. The retained session record hash was `959f1194b916dd86a7879457bf76712df7144ccc029f2ec9afdb5814d5620958`; its recorded status remained `running`, mode `0600`, and the private state directory mode was `0700`. No process was signaled and the session record remained unchanged.

**Investigation error disclosure:** During the preceding inspection, `python3 lib/x11_display.py "$TMPDIR" 1` was mistakenly treated as read-only. At that time the recorded X11 PID was absent and the Unix socket refused connections; the helper nevertheless unlinked `$TMPDIR/.X1-lock` and `$TMPDIR/.X11-unix/X1`. It did not alter `session.json`, signal a process, or start a GUI. The two artifacts were absent at subsequent checks. This behavior was removed from generic inspection and covered by tests. The artifact removal was unintended and is not presented as a successful lifecycle recovery.

### Independent SSH ownership check

- **8022:** the development shell was actively usable through the owner-started SSH connection. Native SSH diagnostics reported daemon process present and configured wildcard bind/password plus keyboard-interactive authentication. Listener-to-process correlation and external reachability remained `unknown`; Termux denied listener-table visibility and `ss` was unavailable. Ternuxx did not start, stop, restart, adopt, or reconfigure this service.
- **8023:** `ternuxx-sshd` under Runit was `running`; effective configuration was `127.0.0.1:8023`; a loopback SSH banner responded; source and installed Runit definition hashes matched. Socket-to-process ownership remained `unverified`. No managed-service lifecycle action occurred.

### Shizuku, boot, and PRoot gates

- Doctor reported Shizuku package presence, versionCode 1318, no `rish` command, no observed provider process name with process visibility unknown, provider release/signer identity unverified, and permission/watchdog health unknown. No privileged capability was inferred and Shizuku is not required for basic desktop startup.
- Termux:Boot app and receiver were enabled; three executable scripts were present, while Android delivery/background policy and current cold-boot readiness remained unknown. The installed `10-ternuxx-profile` exactly matched the `cli-only` profile. Installed `00-ternuxx-services` and `ternuxx-recovery` differed from repository source in state/module paths (`nativeternux` versus `ternuxx`); the installed service script starts the Termux Runit service manager, checks `ternuxx-sshd`, and explicitly does not start PRoot. At inspection, `ternuxx-sshd` was the only service reporting `run`; `sshd`, `ssh-agent`, `tx11`, and `tx11-xfce4` reported `down`. The discrepancy was recorded and left untouched. No reboot or boot-script redeployment occurred.
- Doctor found Debian installed but guest/session ownership unverified. No PRoot was entered; existing rootfs, workspace, `db`/`droot`, `x.sh`, `xgo`, `killx`, and validated acceleration paths were not accessed or changed in this work. Their current usability was not freshly tested.

## Verification

- `python3 -m unittest discover -s tests -p 'test_desktop_lifecycle_fixture.py' -v`: **19/19 passed** (isolated fixture; no live session lifecycle action).
- `python3 -m unittest discover -s tests -p 'test_x11_display0.py' -v`: **6/6 passed**; stale artifacts remain present in fixtures.
- `python3 -m unittest discover -s tests -p 'test_desktop_session_state.py' -v`: **14/14 passed**.
- `python3 -m unittest discover -s tests -p 'test_management_service.py' -v`: **25/25 passed**.
- Final full suite: `python3 -m unittest discover -s tests`, **370 tests passed in 86.766 seconds**, exit 0, run in Native Termux through SSH 8022. Expected fixture diagnostics included stale package-index warnings; suite result was `OK`.
- Static checks passed: `bash -n lib/desktop.sh lib/desktop-supervisor.sh`, `python3 -m py_compile lib/desktop_session_state.py lib/x11_display.py`, `python3 -m json.tool project/phase-state.json`, and `git diff --check` (each exit 0). `python3 -m tools.repo_knowledge verify` reported 0 findings (exit 0).
- These are source/fixture and read-only live checks. They do not prove GUI visibility, cold-boot behavior, listener PID ownership, or PRoot parity. The focused 19-test desktop fixture was also included in the final full-suite run after the last source changes.

## Gate status and next approvals

P3 gate is **blocked / not qualified**. Passed: fixture reconciliation, read-only live stale classification, independent 8022/8023 policy reporting, `cli-only` profile identity, and documented service separation. Unresolved: 8022/8023 socket-to-process ownership, installed/source boot-script discrepancy, Android boot delivery/cold-boot evidence, Shizuku health, live GUI readiness/visibility, and broader service lifecycle qualification. P4 remains gated; no Debian PRoot adapter or workload parity change was started.

A reboot readiness exercise still requires owner approval. Proposed procedure: capture the current boot ID and read-only baselines; reboot once; reconnect through owner-started 8022, then verify Termux:Boot delivery logs, exact installed scripts, Runit 8023 status and authenticated loopback readiness, 8022 remains manually owned, GUI session readiness/visibility, and post-boot recovery state. Risks include Android background limits, missed SSH recovery, and GUI/session startup delay. Rollback is to preserve current script/config backups and use the already-provisioned local Termux console or owner-accessible recovery channel; no rollback script deployment is authorized here. Evidence will include before/after boot ID, timestamps, script hashes, service state, and explicit unknowns. Do not reboot until the owner explicitly approves the exact test window and confirms recovery access.

A separate owner authorization is also needed before starting a live GUI session for device readiness verification; repository policy requires explicit authorization for device desktop process start/stop. The stale record itself has not been reconciled on-device.

## Authorized continuation update — 2026-10-19

The initial “no live start” statements above describe the pre-authorization audit checkpoint. Under the subsequent owner directive, one controlled `tx gui` start on `:1` reconciled the stale record and created a supervisor/X11/XFCE session; a repeated start reported the already-running session. Later read-only status confirmed the current session on `:1` with live recorded process identities; GUI visibility remained `unknown`. The separate configurable Activity/focus monitoring policy now defaults disabled. Its live status query is read-only and reports no Activity request or focus probe. No further Activity request or focus poll was made during the monitoring implementation follow-up.
