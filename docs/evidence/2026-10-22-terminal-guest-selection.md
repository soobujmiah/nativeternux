# Production terminal broker guest selection — 2026-10-22

Phase: `P4`
Gate: IN_PROGRESS

## Implementation

I added an explicit Native broker startup selection for `debian` or a guarded `ternuxx-replay-NAME` container. The default is unchanged. Discovery, executable/account preflight, exact preview, recorded launcher arguments and the final pre-exec identity check use the same selected target. The plan is bound to rootfs/launcher identities; a working-Debian plan cannot start a replay guest. No terminal protocol field permits clients to supply a guest path, user, command or alias.

The separate-state [qualification procedure](../architecture/INTERACTIVE-PROOT-TERMINALS.md#separate-guest-qualification) uses the production assembly without stopping the existing broker. The current Codex guest is preserved. An exactly duplicated test fixture helper was removed without dropping a test.

I also reproduced three attachment leaks before fixing the shared CLI/TUI relay: explicit Ctrl+] detach, an initial resize failure, and loss of the local terminal after a start lease was acquired. All now release the exact writer lease in an outer finally block. Detach never requests guest close/stop, and terminal/signal restoration remains separate from lease cleanup.

## Evidence

- Focused Native session tests: 39/39; production broker assembly tests: 3/3; attachment cleanup regressions: 3/3; TUI shared-service tests: 38/38.
- Full Native regression suite: 732/732 passed in 97.671 seconds; [source-bound result](2026-10-22-terminal-guest-regression.json). CLI help, repository-state verification, phase refresh and diff checks passed.
- All three attachment regression cases failed against the prior implementation and passed after the cleanup change.
- Regression cases cover selected-root/launcher agreement, wrong-target plan refusal before any fork, rejected paths/flags/foreign aliases, symlink refusal without fallback, both broker preview callbacks, spawn selection and CLI default/explicit argument routing.
- Read-only live Native discovery found distinct working and replay rootfs identities. The production assembly built with `ternuxx-replay-p4` without opening a socket or launching a guest.
- A separate live production broker process answered typed status and exited cleanly in its own temporary state directory. No guest start request or working-service signal was sent.
- The separate guest package provisioning was still active at this checkpoint. No terminal lifecycle, GUI render, rootfs rollback or all-client acceptance is inferred from these checks.

## Continuation

Finish and verify fresh setup preservation, then run the complete four-client terminal lifecycle on the separate guest. The [full audit](../audit/REPOSITORY-AUDIT.md) remains active.
