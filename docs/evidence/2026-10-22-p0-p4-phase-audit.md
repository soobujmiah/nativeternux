# P0–P4 phase audit — 2026-10-22

Phase: `P4`
Gate: IN_PROGRESS

## Scope and owner direction

I reviewed completed-phase evidence for P0–P3 and the active P4 source, previous live evidence, and current Native read-only state. The owner clarified that Ternuxx must not depend on PRoot for any core feature. The current product boundary is therefore: Native Termux is self-sufficient for boot/recovery, SSH, CLI, management, state, and native workloads; PRoot remains an optional provider for explicitly routed Linux workloads. A PRoot failure may affect only those selected operations.

This clarification is reflected in the current product vision, project manifest, assistant instructions, architecture, roadmap, and terminal design. Earlier P0 evidence describes the then-approved complementary-layer wording; the current owner direction supersedes that product wording without invalidating the historical P0 documentation/evidence workflow gate.

The owner further clarified on 2026-10-22 that `db`/`droot`, `x.sh`, `xgo`, and `killx` are no longer required for P4 acceptance. The active Debian PRoot workstation/rootfs/data must still be protected; this clarification does not authorize changing those live files or guest state.

## Phase results

| Phase | Audit result | Evidence basis and limits |
|---|---|---|
| P0 — Repository foundation | Pass, historical | `P0-foundation.md` records scope, safety boundaries, generated phase documentation, and read-only review. Its original product framing has been superseded by the Native-first optional-provider clarification above. |
| P1 — Compatibility research | Pass, dated snapshot | `P1-compatibility-research.md` records package/runtime facts as observed on 2026-10-17. Those are historical snapshots, not claims of today's package-index state; refresh compatibility facts in P5/release work. |
| P2 — Native desktop lifecycle | Pass for the recorded Android 16/Termux target | `P2-phase-completion-2026-10-18.md` records exact package preview/apply validation, native lifecycle/recovery, and preservation checks. The later current Native `:1` status is read-only and running. This does not qualify other devices. |
| P3 — Doctor, management, recovery | Pass with explicit checkpoint limitation | The RB08 postboot audit records changed boot identity, matching Native observer, native service ready log, and separate authenticated 8023 readiness checks. The private verifier checkpoint remains `NOT_READY` and auto-resume false because its observer did not capture service health. Canonical recovery modules were installed after RB08; the next boot has not exercised that new module copy. No PRoot-independent cold-boot claim is inferred from the checkpoint alone. |
| P4 — Optional existing Debian PRoot provider | In progress; not accepted | Historical standalone `:0` and direct guest app/GLX on Native `:1` have passing evidence. Nested `:2` had no verified draw/presentation: GLX returned zero frames and DRI3 was unavailable. Fresh Debian replay is fixture-tested only; there is no disposable live guest replay. Today's read-only status reports Native `:1` running, standalone `:0` stopped, `:2` socket absent, Debian installed, and a host PRoot process candidate whose ownership is unverified. No PRoot process was stopped or adopted. |

## Native-core independence audit

- Native boot source starts only native Termux services and records `provider=native_termux; proot_dependency=false`; the RB08 boot log contains that result. Native Runit owns the 8023 daemon, its config, and host keys.
- Postboot Native Doctor verified the 8023 managed process identity/config/banner, and the authorized client authenticated through 8023. PRoot held the client identity in that probe; it did not host the service or server credentials.
- The Native Termux suite passed **660/660** before the client audit update on port 8022. Relevant fixtures include `test_checkpoint_cli_is_native_only_and_records_without_proot` and `test_native_lifecycle_refuses_proot_environment`.
- CLI and TUI call the shared typed management service; Web and GTK bridge also dispatch through that service. Their PRoot calls are inside explicit PRoot resource/action handlers. Catalog discovery is static; a new failure-injection test makes it fail if catalog lookup probes `proot-distro` or lists sessions. The catalog now labels Debian PRoot as optional and unprobed instead of claiming it is installed. Doctor reports an unavailable PRoot command as an informational finding and continues its report.
- Current profile/manager discovery reports the Debian install and keeps PRoot process ownership unverified. The device was not tested with all PRoot processes absent: a process candidate is present and unverified, and I did not signal it. Thus Native-first source/fixture and boot evidence pass, while an owner-safe physical no-PRoot runtime window remains unqualified.

## P4 acceptance still open

1. Audit the Native core call graph and add/verify failure-injection coverage proving that missing `proot-distro`, missing rootfs, or a broken guest cannot block Native boot, SSH, CLI, management, or native workloads.
2. Complete the optional provider's read-only inventory and argument-safe guest command contract, including provider identity, scoped environment, output, exit status, and process ownership.
3. Reconcile separate route results for standalone `:0`, selected apps on Native `:1`, and nested `:2`; keep nested graphics unqualified until an actual draw/presentation passes.
4. Reproduce the selected guest setup only on a separate disposable rootfs, with a positive guard that refuses the existing Debian rootfs and exact rollback.
5. Continue the shared interactive terminal broker and CLI/TUI/Web/GTK adapters as optional PRoot-provider features; their absence must not disable Native clients or management.

## Existing Ternux CLI preservation audit (read-only, 2026-10-22)

- Native Termux scanned the existing Debian rootfs directly without entering it. Rootfs identity observed: UID 10490, mode 0755, device 65086, inode 3240111.
- The old Ternux guest companion remains at `/usr/local/bin/ternux` as an executable regular file (UID 10490, mode 0755, 4376 bytes; SHA-256 `7d9202ef018ac70ee94940290e4ccef0ce1a57fd12d190aa336dad25b0d6acf2`). No installed Debian package or dpkg file list matching Ternux was found, so it appears to be a manually installed standalone CLI. Its source header describes a guest companion and says Android-side lifecycle belongs to the host CLI; the binary was not executed.
- Read-only `./tx mng proot status --json` reports Debian installed and `guest_entered=false`. It observes PRoot PID 15279 as an ownership-unverified candidate and reports Ternuxx session records stopped. No PRoot process was stopped/adopted and no rootfs, CLI, package, or guest data was changed.
- Conclusion: the old Ternux CLI was **not removed** while preserving the current PRoot. The owner says db/droot, x.sh, xgo, and killx are no longer required for P4 acceptance; no removal was requested or performed in this audit.

## Verification performed

- Current Native read-only commands: `./tx mng proot status --json`, `./tx mng proot profiles list --json`, `./tx mng proot sessions list --json`, and `./tx pgui status --json`.
- Full Native Termux suite from the 8022 repository shell: `bash scripts/repo_test.sh` — **660/660 passed** in 97.641 seconds. No device boot, desktop, SSH service, or guest lifecycle action was run by this audit.
- After the client/catalog audit update, `python -m unittest tests.test_management_catalog -v` on Native Termux — **7/7 passed**, including injected PRoot-probe failures and optional/unprobed provider labeling. `python -m unittest tests.test_doctor_report tests.test_management_catalog -v` — **36/36 passed**, including missing-manager Doctor behavior. `bash scripts/repo_test.sh` rerun on port 8022 after Doctor failure-injection coverage — **662/662 passed** in 89.878 seconds.
- P4 broker transport/channel slice in `lib/terminal_broker.py`: private same-UID Unix socket, bounded strict JSON framing, typed dispatcher, one-writer/generation-bound attachment registry, bounded I/O/output retention, and preview-bound close callbacks. Socket paths are not adopted or replaced. A read-only broker-status operation is exposed to CLI, TUI, authenticated Web, and GTK resource inspection; it reports `not_running` when no broker exists and never probes PRoot. The broker still does not spawn/relay PTYs or connect terminal clients. `tests.test_terminal_broker` — **7/7 passed**; cross-client/management focused tests — **117/117 passed** on Native Termux. Full `bash scripts/repo_test.sh` — **673/673 passed** in 107.220 seconds. No live guest was entered.
- Historical P4 device results are linked from [full Debian GUI qualification](2026-10-20-proot-full-gui.md), [graphics live recheck](2026-10-20-graphics-live-recheck.md), and [fresh guest reproducibility](2026-10-20-proot-fresh-reproducibility.md).
- Current phase state is `P4=in_progress`; no P4 gate is marked complete.

## Evidence

- [P0 foundation completion](P0-foundation.md)
- [P1 compatibility research](P1-compatibility-research.md)
- [P2 completion evidence](P2-phase-completion-2026-10-18.md)
- [P3 RB08 postboot exit audit](2026-10-22-p3-rb08-postboot-exit-audit.md)
- [P3-before-P4 owner decision](2026-10-21-p3-before-p4-owner-decision.md)
- [P4 full Debian GUI qualification](2026-10-20-proot-full-gui.md)
- [P4 graphics recheck](2026-10-20-graphics-live-recheck.md)
- [P4 fresh guest reproducibility](2026-10-20-proot-fresh-reproducibility.md)

## P4 PTY spawn foundation follow-up — 2026-10-22

`proot_sessions.spawn_login_interactive()` separates exact-preview fixed-profile PTY startup from the caller-owned foreground relay. It retains rootfs/launcher identity checks, private session/group checks, and verified failure cleanup, and returns the PTY master FD only after session ownership is verified. The existing CLI/TUI path still performs its foreground relay through this helper. A fixture mocks `pty.fork`, process identity, and verification and confirms the broker-facing helper does not require a client TTY.

`python3 -m unittest tests.test_proot_sessions -v`: **35/35 passed**. Full Native Termux `bash scripts/repo_test.sh`: **674/674 passed** in 108.294 seconds. `python3 -m py_compile lib/proot_sessions.py` and `git diff --check` passed. No PRoot login was started; the helper is not wired to a persistent broker, so broker PTY ownership, I/O relay, and client attachments remain open. P4 stays in progress.
