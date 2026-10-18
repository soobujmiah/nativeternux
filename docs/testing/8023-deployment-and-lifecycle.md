# 8023 managed SSH deployment and lifecycle qualification

## Reconciliation workflow

Use Native Termux. `ternuxx ssh deploy` without confirmation produces a read-only plan with source/installed hashes, exact unified diff, effective SSH configuration hash, current Runit status, and an exact plan ID. Review it before applying with `ternuxx ssh deploy --yes --plan-id <plan-id>`. Applying atomically replaces only the fixed run definition and records a private rollback snapshot. It does not restart or stop the running unit, touch SSH configuration, or affect manual development SSH on 8022.

To preview and apply a rollback, run `ternuxx ssh deploy-rollback-preview --operation-id <id>`, then `ternuxx ssh deploy-rollback --operation-id <id> --yes --plan-id <plan-id>`. A rollback plan shows its own diff. If automatic rollback after a partial write fails, the deployment journal stays `needs_recovery`; explicit recovery uses that operation's snapshot and resolves the same journal after verification. Never delete a recovery snapshot while its journal is unresolved.

Seven fixture regression tests are in `tests/test_runit_deployment.py`. They cover read-only preview/diff, exact-plan confirmation, apply and explicit rollback, partial write with automatic restore, failed automatic restore followed by recovery, partial explicit rollback recovery, symlinked snapshot refusal, source/config validation, and the absence of Runit up/down/restart actions. These tests do not replace device deployment verification.

## Separate 8023 lifecycle qualification plan

Run this only after a reviewed plan and preserve 8022 as the recovery channel. Do not reboot without explicit owner approval.

1. **Start:** from stopped state, preview then confirm start; verify exactly one owned Runit process, authenticated loopback SSH readiness, and journal completion.
2. **Repeated start:** verify idempotent/no duplicate daemon behavior and stable ownership.
3. **Stop:** confirm the impact on active 8023 sessions; verify only the verified managed process stops and listener disappears. Keep 8022 available.
4. **Repeated stop:** verify no unrelated process is signaled and journal state remains consistent.
5. **Restart:** separately verify stop/start sequencing, readiness deadline, session impact, and recovery if either stage fails.
6. **Listener ownership:** correlate loopback socket inode to process FD and Runit ancestry; record exact commands and permissions. If `/proc/net/tcp*` or process FDs are denied, report `UNVERIFIED`.
7. **Duplicate instance:** safely inject only in a fixture; on device, inspect for duplicates without killing ambiguous processes.
8. **Failure recovery:** exercise startup timeout, stale state and rollback in fixtures first; on device use only a reviewed non-disruptive case and preserve journal/log evidence.
9. **Post-reboot:** remains `UNVERIFIED` until an explicitly approved reboot and authenticated post-boot readiness/ownership checks pass.

Each device result records commit, UTC timestamp, environment, command, expected/actual result, status, evidence path, and limitations. A config syntax pass or SSH banner alone does not prove process ownership or authenticated readiness.
