# P3 gate review follow-up — 2026-10-21

Phase: `P3` — remains in progress.

This is a current gate review, not a P3 exit audit or completion record. The P3 exit audit is deferred because the shared-client boundary and Native boot qualification are still open.

## Scope reviewed

Compared the P3 deliverables and exit gate in `docs/ROADMAP.md` with `project/phase-state.json` and the latest available evidence for PRoot TTY ownership, session-client parity, Cron mutation parity, boot-helper reconciliation, Cron/boot concurrency, bounded logs, and SSH diagnostics. Existing test counts below are reported only from those dated evidence records; no test suite was run for this follow-up.

## Current Native read-only observations

- `tx mng doctor --json` at `2026-10-21T08:08:56Z` returned `read_only: true`. Managed SSH process identity and loopback banner passed independently. Listener ownership stayed unknown: procfs=`permission_denied`, netlink=`permission_denied`, source=`none`. Evidence: [SSH diagnostics follow-up](2026-10-21-p3-ssh-netlink-fallback.md).
- `tx status --json` at approximately `2026-10-21T08:16Z` returned `status=stale`, `display=:1`, and supervisor/X11/XFCE=`absent`; `gui_visible=unknown`. No process or service was started, stopped, or signaled.
- Existing Debian guest ownership remains unverified. No guest was entered. No boot script was run and no device restart occurred.

## P3 gate disposition

| Gate area | Current disposition | Evidence/remaining point |
|---|---|---|
| Read-only Doctor and fail-closed reporting | Source/fixture evidence exists; current read-only JSON report works and exposes both denied listener sources. | Continue to preserve unknown ownership; no device API currently supplies the missing listener-to-port mapping. |
| Interactive PRoot TTY ownership contract | Fixture-verified in the existing 34-test contract record. | Live guest qualification belongs to P4. The earlier failed attempts exposed no guest shell and caused no signal or rootfs repair. |
| Shared client action parity | **Open.** TUI has a fixture-tested attached interactive-login route; Web and GTK expose only the bounded isolated probe for non-CLI session operations. | Roadmap requires an owner-accepted client-specific boundary when an action is not available in all clients. No such acceptance is recorded for the foreground TTY-only profile. |
| Journal, preview, recovery, and concurrency | Component evidence exists for Cron mutation and boot-helper preview/apply/rollback and lock serialization. | This review does not claim a whole-phase pass; retain the operation-specific limits in their evidence records. |
| Installed boot/recovery helpers | **Pass for source reconciliation.** Installed identities match repository source; exact prior bytes/modes have private rollback snapshots. | No helper was executed; runtime boot delivery is a separate gate. |
| Boot profiles and provider boundary | Native boot profile remains the only P3 qualification target; PRoot and Hybrid boot remain deferred to P4/P8. | Existing guest ownership stays unverified and unmanaged. |
| Android cold-boot/background delivery | **Open; owner-window gated.** | Roadmap requires an owner-authorized Android restart and post-boot read-only checks. A manual helper invocation is not evidence. |
| P3 exit audit | **Not ready.** | Run only after the open client-boundary and device-boot gates are resolved or explicitly recorded as owner-blocked under the roadmap. |

## Restart requirement

No Android restart is needed to finish this repository-side review. A user-operated Android restart will be needed later to qualify the P3 cold-boot gate. That restart will end the current SSH/Codex work connection, so schedule it only after the remaining non-reboot P3 work is ready and an owner-approved boot window is set.

The stale `:1` status is a separate desktop-session state, not proof that Android itself needs a restart. This follow-up did not start or repair that session.

## Evidence

- P3 criteria and serial order: `docs/ROADMAP.md` and generated `docs/PHASE-STATUS.md`.
- Current phase source: `project/phase-state.json`.
- PRoot TTY contract: `docs/evidence/2026-10-21-p3-proot-tty-contract-audit.md`.
- Shared-client status: `docs/evidence/2026-10-21-p3-session-client-parity-audit.md` and `docs/evidence/2026-10-21-p3-session-client-implementation.md`.
- Cron, boot-helper, and concurrency evidence: `docs/evidence/2026-10-21-cron-mutation-client-parity.md`, `docs/evidence/2026-10-21-boot-helper-reconciliation.md`, and `docs/evidence/2026-10-21-p3-cron-boot-concurrency.md`.
- SSH source-specific denial: `docs/evidence/2026-10-21-p3-ssh-netlink-fallback.md`.

## Desktop session follow-up

After the owner clarified that the Termux:X11 Activity was already open and authorized the GUI session to be enabled, `tx start --display 1` was run through the Native Ternuxx checkout. Ternuxx reconciled the exact stale `:1` socket/lock pair using its recorded absent X11 PID, reported Native PulseAudio ready, and started its X11/XFCE session on `:1`. A subsequent read-only `tx status --json` returned `status=running`, `supervisor=live`, `x11=live`, and `xfce4_session=live`. `gui_visible` remains `unknown`; the session state does not prove what is rendered on screen. No phone restart occurred, and no Debian guest or SSH service was changed.
