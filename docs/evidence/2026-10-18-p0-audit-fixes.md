# P0 audit, fixes, and live baseline — 2026-10-18

## Scope and tested source

- Repository: `soobujmiah/ternuxx`, branch `main`.
- Baseline commit: `dcae006` (after fast-forwarding the generated repository-state sync; the worktree was clean).
- Fix commit: `4eed13a`.
- Native development channel: authenticated SSH on port `8022`, user `u0_a490`; remote identity was confirmed as Native Termux (`PREFIX=/data/data/com.termux/files/usr`, Termux `0.119.0-beta.3`) at `$HOME/ternuxx`.
- No credentials were recorded. No reboot, package change, GUI lifecycle action, service lifecycle action, or runtime-state migration was performed.

## Baseline and regression results

| Test ID | Requirement | Procedure / environment | Result |
| --- | --- | --- | --- |
| BASE-01 | Establish existing automated baseline | `bash scripts/repo_test.sh` on Native Termux at `dcae006` | PASS, 295 tests |
| P0-F1 | Native lifecycle refuses PRoot mutation before side effects | New fixture test runs `stop` and `restart` with Native Termux markers removed while a fixture session is active; checks session bytes, journal, and lock | PASS |
| P0-F2 | JSON values are escaped and `missing` remains an array | New shell-helper regression cases cover quotes, backslashes, newline, Unicode, empty values and typed arrays; live read-only `bash bin/ternuxx --json check` parsed successfully with `missing` as a list | PASS |
| P0-F3 | State helper treats dynamic input as data and preserves state on failure | New tests round-trip quoted/backslash/newline/Unicode key and value, confirm private file mode, verify missing-key and malformed-file behavior, and inject replace failure to confirm the original file is preserved and the temporary is removed | PASS |
| P0-SUITE | Full regression suite after fixes | `bash scripts/repo_test.sh`; Native Termux at the exact source tree committed as `4eed13a` | PASS, 301 tests in 64.370s |
| P0-FOCUSED | Focused shell/state and desktop lifecycle tests | `python3 -m unittest tests.test_core_shell -v` after final test changes | PASS, 5 tests; desktop fixture tests are included in P0-SUITE |
| P0-STATIC | Shell/Python syntax and whitespace | `bash -n` on changed shell entrypoints; Python `compile()` on changed test modules; `git diff --check` | PASS |
| P0-PROOT | Preserve and identify the existing Debian workstation | Read-only `proot-distro list`; read-only `proot-distro login debian --shared-tmp --user sbj -- bash -lc 'id -un; pwd; sed -n "1,5p" /etc/os-release'`; inspected aliases and `~/x.sh` | PASS for identity/presence only: Debian 13, user `sbj`; no launcher or guest mutation was run |

## Findings and dispositions

1. **Native lifecycle guard — CONFIRMED and FIXED.** `nt_cmd_stop()` lacked the native environment guard; `nt_cmd_restart()` called stop before any guard. Both now call `nt_require_termux` before reading state, taking a lock, journaling, or signaling. Start behavior remains guarded. Fixture regression coverage verifies no state, journal, or lock side effects from PRoot.
2. **JSON serialization — CONFIRMED and FIXED.** Shell concatenation did not escape arbitrary values. JSON object/array helpers now use Python's standard `json` module. A typed object helper preserves numeric and array fields; the check output's `missing` field is a JSON array. Live read-only check returned `check=pass`, `missing_count=0`, and a parsed list.
3. **State helper interpolation/atomicity — CONFIRMED as an implementation defect; no caller was found outside `lib/core.sh` at audit time, so no exploit claim is made. FIXED.** Key, value, and path are passed as process arguments; JSON is parsed by the standard library; writes use a same-directory temporary file, fsync, and atomic replace. Malformed state fails without truncating the existing file. Existing schema remains a JSON object of key/value entries.
4. **SSH policy/runtime — PARTIALLY CONFIRMED; ownership remains UNVERIFIED.** Port `8022` is the active manual development channel and authenticated Native Termux shell used for this work. Read-only inspection reports its configured listener as `0.0.0.0:8022` and `[::]:8022`, password and keyboard-interactive authentication enabled, and root login `prohibit-password`; daemon/listener correlation and external reachability are unknown. Port `8023` is separate: Runit reports `ternuxx-sshd` running; the service's effective config reports `127.0.0.1:8023`, and the loopback probe received an SSH banner. Kernel listener PID observation was permission-denied. The installed service run definition hash differs from the repository source hash. No service definition was replaced or restarted because the active managed service and its runtime state must remain intact pending a reviewed change. No reboot qualification was performed in this audit.
5. **Status chronology — CONFIRMED.** Repository docs retain many historical snapshots alongside current status. This report is a dated audit snapshot; older evidence was not deleted or rewritten. Automated and fixture tests, live native checks, reboot qualification, and release readiness remain separate claims.
6. **PRoot scope — EXISTING NARROW INTEGRATION; FULL LIFECYCLE ADAPTER NOT IMPLEMENTED.** Current diagnostics/typed shortcut integration exists in source and tests. The installed Debian 13 environment was identified read-only. Full distro/app lifecycle control remains planned; no workflow was replaced, and no GUI was launched or stopped.
7. **License — CONFIRMED RELEASE BLOCKER.** No root-level `LICENSE` exists. No license was selected or inferred.

A test-authoring assertion initially expected a state file to be absent after the test had created it; the fixture assertion was corrected, then the focused helper tests and final full suite passed. This was a test expectation error, not a product failure.

## Workstation and safety record

The `db` and `droot` aliases, `x`, `xgo`, `killx`, and `~/x.sh` were inspected without executing their lifecycle actions. Debian remained Debian 13 under `sbj`; its rootfs, packages, files, and shell configuration were not changed. Native and PRoot dependency boundaries were not altered. The active 8023 service and the 8022 manual access configuration were not changed.

## Remaining gates

- Resolve the installed 8023 run-definition/source drift with a reviewed, rollbackable service deployment and a separate lifecycle test; do not infer ownership from an SSH banner.
- Keep 8022's wildcard/password configuration documented as a risk until a safe, owner-reviewed remediation preserves manual development access.
- Establish actual listener PID/UID ownership using a permitted observation mechanism.
- Reboot readiness remains `UNVERIFIED` here; it requires an owner-approved reboot qualification.
- Continue the P3 shared-management tests and keep the full Debian adapter in P4 scope.
- Release remains blocked until the owner makes a license decision.
