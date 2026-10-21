# P3 worktree review and Native recheck — 2026-10-21

Phase: `P3` remains in progress. This is a read-only review of the existing Native Termux worktree and a current status snapshot; it is not a P3 exit audit. A later owner decision on phase order supersedes the open-boundary observation below; see [P3-before-P4 decision](2026-10-21-p3-before-p4-owner-decision.md).

## Worktree review

Reviewed the existing 20 modified tracked files and 7 untracked files in the Native checkout at the start of this review. The checkout was `main` at `dfa3f63`, matching `origin/main`. All existing edits were preserved; no commit or push was made.

The implementation changes add a preview-confirmed TUI attached-login route for the fixed `debian-interactive` profile; bounded `NETLINK_SOCK_DIAG` fallback and per-source provenance for SSH listener diagnostics; Termux-specific PulseAudio profile sanitation and a headless service environment; and an explicit Termux Bash invocation from the Cron boot helper. The associated fixtures and docs were reviewed. The TUI route is fixture-only and remains unqualified on the live guest. The SSH fallback fails closed when Android denies both procfs and netlink. No PRoot guest was entered and no service, desktop, boot script, or Android setting was changed during this review.

## P3 boundary reconciliation still required

The owner-required interactive terminal capability spans CLI, TUI, Web, and GTK. The shared broker and Web/GTK terminal transports are described as P4 work in `docs/architecture/INTERACTIVE-PROOT-TERMINALS.md`; P3 is still the only active phase and the roadmap prohibits starting future-phase implementation before P3 passes. The earlier CLI/TUI-only boundary proposal is explicitly withdrawn, and no owner-accepted limitation is recorded. Therefore the all-client terminal gate remains open and must not be reported as accepted or complete. Resolve this phase-boundary decision before the P3 exit audit; do not infer an exception from the withdrawn proposal.

## Current Native read-only status

At `2026-10-21T17:39:29+06:00`, through the managed 8023 CLI endpoint after Termux had been reopened:

- `tx status --json` reported display `:1` as `stale`; the recorded supervisor, X11, and XFCE processes were absent; GUI visibility was unknown.
- Doctor reported the managed `ternuxx-sshd` process identity, valid config, and loopback SSH banner as passing. Listener-to-port correlation remained unknown because procfs and netlink observations were both denied.
- Doctor separately warned that native SSH configuration is wildcard-bound with password authentication enabled; process owner and external reachability were unknown.

No desktop recovery or SSH policy change was performed. The earlier 2026-10-20 workstation snapshot claiming Native XFCE `:1` was running is historical and is superseded for the current observation by this recheck.

## Reboot gate and next action

Private checkpoint `TERN-20261021-RB07` is prepared and `NOT_READY`; no Android restart has been reported or performed in this review. Its post-restart procedure is owner-operated and must only be run after the owner restarts Android and reconnects through 8022. First resolve the open P3 shared-client terminal boundary and complete remaining pre-reboot work; then verify only RB07 and keep every unknown explicit. Do not invoke boot helpers manually or repeat a restart automatically.

No tests or static checks were run as part of this review. Existing dated verification remains as recorded in its own evidence files and is not re-attributed to this review.

## Evidence

- Native checkout state and existing diffs: `git status --short --branch`, `git diff`, and `git ls-files -co --exclude-standard` on port 8022.
- P3 order and exit criteria: `docs/ROADMAP.md` and `project/phase-state.json`.
- Current terminal boundary: `docs/architecture/INTERACTIVE-PROOT-TERMINALS.md`, `docs/evidence/2026-10-21-p3-interactive-terminal-contract-reconciliation.md`, and the explicitly withdrawn `docs/evidence/2026-10-21-p3-interactive-client-boundary-proposal.md`.
- Reboot gate: `docs/evidence/2026-10-21-p3-pre-reboot-rb07-checkpoint.md` and `docs/testing/REBOOT-RECOVERY-GUIDE.md`.
- Live status: read-only `tx status --json` and `tx mng doctor --json` via the loopback managed CLI; no UI interaction or lifecycle mutation.
