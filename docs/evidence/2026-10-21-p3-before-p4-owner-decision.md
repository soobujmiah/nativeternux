# Owner decision: confirm P3 before P4 — 2026-10-21

Phase: `P3` remains active; this records phase ordering and does not complete a gate.

## Decision

The owner directed: “P3 e agey ses koro confirm koro tarpor P4” — complete and confirm P3 before starting P4.

This is an approved implementation sequence, not withdrawal or permanent deferral of the product requirement. Interactive terminal support remains required in CLI, TUI, Web, and GTK. During P3, Ternuxx verifies the fixed-profile ownership/security contract and keeps unsupported Web/GTK terminal transports visibly unavailable. After P3 is confirmed, P4 implements the shared PTY broker and all-client transports described in `docs/architecture/INTERACTIVE-PROOT-TERMINALS.md`. No client may expose a host shell or arbitrary command, argv, rootfs, user, environment, or working-directory override.

## P3 completion boundary

P3 remains open until all P3 exit criteria pass. The private RB07 checkpoint still requires the owner's Android restart and post-boot verification. The agent must not initiate that restart or run boot helpers manually. After the owner reconnects on 8022, verify only `TERN-20261021-RB07`, keep failed/unknown results explicit, and run the P3 exit audit only if every required gate passes. Start P4 only after the P3 completion is recorded.

This decision does not claim that the P4 terminal capability is already implemented or that any device/reboot gate passed.

## Evidence

- Owner's direct instruction in this session: complete and confirm P3 first, then P4.
- P3 exit order and gate: `docs/ROADMAP.md` and `project/phase-state.json`.
- P4 shared-broker plan: `docs/architecture/INTERACTIVE-PROOT-TERMINALS.md`.
- Pending owner-operated reboot verification: `docs/evidence/2026-10-21-p3-pre-reboot-rb07-checkpoint.md`.
