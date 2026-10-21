# P3 RB08 postboot and exit audit — 2026-10-22

Phase: `P3` — completion review after the owner-operated RB08 Android restart.
Gate: PASS

## Result

I completed the P3 exit review against `docs/ROADMAP.md`. P3 gates pass with the staged interactive-terminal boundary recorded in the 2026-10-21 owner decision. This completes P3's contract and security-boundary work; it does not claim that P4's shared PTY broker or four-client terminal transports exist.

The private RB08 checkpoint remains `boot_observed`, `NOT_READY`, and `automatic_resume=false`. Its verifier correctly reports `verified_reboot_service_unqualified`: at its observation time, managed service health was not captured. I did not edit that private checkpoint or infer a pass from it. Independent read-only checks after the same changed-boot observation verified the Native service and authenticated connection described below. No task resumed automatically.

## RB08 Native cold-boot evidence

- The private checkpoint reports that the boot identity changed and the matching Native boot observation was found. Checkpoint IDs/nonces and boot identifiers remain private and are omitted here.
- The Native boot log recorded `result=ready; provider=native_termux; proot_dependency=false`. The recovery observer ran and exited 0. The Termux:Boot Cron entry recorded its script identity as matching and scheduler as running, started by the script. The generic `actual_device_boot_delivery` status field remains `not_yet_verified`; the timestamped boot log and matching observer record are the direct evidence used here.
- `tx mng boot helpers status --json` reports both installed shell helpers byte-identical to repository source and mode `0700`. The recovery helper now selects `$PREFIX/lib/ternuxx` first. I created that previously absent directory after this boot and installed only `reboot_recovery.py`, `ssh_diagnostics.py`, and `continuity.py` from checkout source with mode `0600` in a `0700` directory. Their imports resolve from that canonical path. The separate pre-canonical module directory was preserved unchanged. Because this module deployment occurred after the observed boot, the next device boot will exercise the canonical modules; no second reboot was initiated.
- The native managed service uses Termux-owned host keys and `$HOME/.ssh/authorized_keys`; effective config is loopback-only on 8023, public-key authentication enabled, password authentication disabled. Key material was not read, copied, or changed. A one-shot SSH client launched inside the existing Debian PRoot authenticated to native `127.0.0.1:8023`; it returned the expected marker. The same client ran the managed CLI Doctor over 8023 successfully. PRoot supplied only the client identity: native Termux owns the listener configuration, host keys, runit service, and boot entrypoint. The boot record explicitly reports `proot_dependency=false`.
- Postboot `tx mng doctor --json` is read-only. `NTX-SVC-001` passes: runit service running, config valid, process identity verified, and loopback SSH banner present. Socket-to-port correlation remains unknown because Android denies procfs and netlink observations. The independent `tx reboot verify TERN-20261021-RB08` result remains unqualified for the reason above; the authenticated probe is supplementary manual evidence, not a rewrite of the checkpoint.
- Postboot `tx status --json` reports Native `:1` running with supervisor, X11, and XFCE live. GUI visibility remains unknown. The stale session observed earlier was recovered with the authorized `tx start --display 1` lifecycle operation.

## Acceptance criteria

All P3 exit criteria were reviewed in roadmap order. The table records each result and the remaining unknowns without treating unavailable observations as proof. The owner-approved phase-order boundary for the four-client interactive terminal is recorded in `2026-10-21-p3-before-p4-owner-decision.md` and the P3 roadmap.

## P3 exit gates

| Gate | Result | Evidence and limits |
|---|---|---|
| Read-only Doctor, stable findings, fail-closed unknown/conflict handling | Pass | Current native Doctor is read-only; `NTX-SVC-001` verifies service identity separately from unavailable socket ownership. 8022 wildcard/password configuration remains a warning and was not changed. |
| Interactive PRoot TTY ownership contract and client security boundary | Pass for P3 | The fixture-verified contract and the explicit P3-before-P4 owner decision stage the attached interactive terminal transports for P4. Four-client terminal support remains required and is not represented as implemented. |
| Journal, preview, confirmation, rollback, recovery, and concurrency | Pass | Existing P3 operation-specific fixtures and recovery/concurrency evidence remain applicable; current Doctor reports no unresolved operation journal records. No unrelated service/process/rootfs was mutated. |
| Shared P3 management across CLI, TUI, Web, GTK | Pass within recorded boundary | Fixed-profile P3 actions use the shared management service and client capability matrix. Interactive TTY is explicitly staged for P4 by the owner's recorded sequencing decision. |
| Installed boot/recovery helpers match source | Pass | Both installed shell entrypoints match source and mode. The canonical runtime module directory now contains exact current source for the three recovery imports; compatibility directory retained. |
| Native, existing-PRoot, Hybrid, and CLI-only profiles | Pass for P3 definition | Only Native boot was qualified. PRoot boot remains P4 and Hybrid boot P8; guest ownership remains unverified. |
| Android startup/background and Termux:Boot | Pass for observed boot path | Changed boot, matching observer, ready native service log, Cron boot entry result, current managed service identity, and authenticated 8023 client connection were observed. System-wide background-delivery policy and listener inode ownership remain unknown. The checkpoint remains NOT_READY and auto-resume remains false. |
| Exit audit | Pass | Criteria reviewed in order; limitations are kept explicit above. |

## Verification and preservation

- Focused `tests.test_ssh_diagnostics`: 15/15 passed after the Android `comm=run` process-identity fix.
- Full `bash scripts/repo_test.sh`: 660/660 passed.
- `python3 -m tools.repo_knowledge verify`: 0 findings.
- `git diff --check`: passed before this audit was recorded; final repository checks are repeated after phase-state synchronization.
- Native 8022 development shell, managed 8023 service, Debian rootfs/user data, and existing SSH keys/configuration were preserved. No package install, SSH policy edit, service restart, manual boot-helper invocation, commit, or push occurred.

## Follow-up limits

The canonical recovery-module deployment happened after RB08, so its next cold-boot invocation is not yet physically observed. Android's system-wide background policy and 8023 socket-to-process mapping remain unavailable. Neither gap invalidates the directly observed Native boot path and authenticated readiness in RB08; both remain unknown rather than assumed. P4 is the next phase, but no P4 implementation is included in this completion record.

## Evidence

- [RB08 pre-reboot checkpoint](2026-10-21-p3-pre-reboot-rb08-checkpoint.md)
- [P3-before-P4 owner decision](2026-10-21-p3-before-p4-owner-decision.md)
- [P3 Cron/boot concurrency](2026-10-21-p3-cron-boot-concurrency.md)
- [P3 client parity follow-up](2026-10-21-p3-session-client-implementation.md)
- [P3 gate review follow-up](2026-10-21-p3-gate-review-followup.md)
