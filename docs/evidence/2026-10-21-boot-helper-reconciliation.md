# Termux:Boot helper reconciliation - 2026-10-21

Phase: `P3` - remains in progress.

## Implementation

Added a shared local operation boundary for the two Ternuxx-owned boot helpers:

- boot.helpers.status inspects only the fixed service and recovery helper paths; it does not create state or run scripts.
- boot.helpers.preview shows full before/after content and SHA-256 for deploy or rollback.
- boot.helpers.apply requires a fresh exact plan ID plus explicit confirmation. The preview expires after 15 minutes and apply rejects a changed target or changed repository source.
- Deploy accepts only the previously observed exact legacy hash, the current repository hash, or the hash recorded by this manager. Missing targets, symlinks, unsafe file ownership/modes, unknown custom content, and invalid snapshots fail closed.
- Before replacement, the exact previous bytes and mode are saved in the private state directory. Snapshot files and state records use mode 0600; their parent directories use 0700. Rollback is another preview/apply operation bound to the deployed identity.
- CLI and the shared service expose the contract. Web does not receive boot.manage; no TUI/GTK action is claimed.

## Live Native Termux reconciliation

Read-only status identified both installed files as the known legacy versions. Exact preview output showed only the intended migration from legacy NATIVERNUX_STATE_DIR paths to canonical TERNUXX_STATE_DIR with compatibility fallback, and the recovery-module preference from lib/nativeternux to lib/ternuxx with legacy fallback. Both source scripts passed bash -n. Targets were regular owner files at mode 0700.

Applied the two exact reviewed plans atomically:

| Helper | Installed SHA-256 after apply | Private rollback snapshot |
|---|---|---|
| 00-ternuxx-services | 8dfa04273dd93cc0def5f26b70d496b9f80575f4608bcf079cea993eb04d3119 | f34c88634e7ecc571c325e63f962fc27 |
| ternuxx-recovery | 702f4f21229495bf8725c6e7063877ccd47810fd20f0651ae1e9a79ae9fad64d | 205e015f76e28f5e9fe304950b63dced |

A fresh read-only status then reported both installed hashes equal to repository source (identity=match), mode 0700. Rollback snapshots remain in the private Termux state under boot/helpers/snapshots; exact prior bytes and modes are preserved. No boot helper was executed, and no Termux service, Cron scheduler, SSH process, GUI session, or PRoot process was started, stopped, or restarted.

## Verification

- Fixture tests cover deploy + exact rollback, unknown target refusal, stale target refusal, source drift refusal, expired plans, required confirmation, symlink refusal, and no-write status.
- Focused boot-helper, shared-service, authorization/session, and catalog suite: 60/60 passed.
- Full Native Termux repository suite after final hardening: 634/634 passed in 98.171 seconds.
- Live tx mng boot helpers status after apply: both helpers report match.
- Cold-boot delivery remains unqualified; no reboot was performed. The Ternuxx service start sequence and recovery observer behavior at actual Android boot remain unverified.

## Remaining P3 work

Complete the remaining recovery and concurrency acceptance gates, including validating Ternuxx-owned state after an ordinary app/process interruption without closing this Termux/Codex session. Cold boot remains a separate owner-approved device window. Do not mark P3 complete from source reconciliation alone.

## Evidence

Sources: `lib/boot_helpers.py`, `lib/management_service.py`, `lib/management.sh`, and `scripts/termux-boot/`. Fixture coverage: `tests/test_boot_helpers.py` and `tests/test_management_service.py`. The live targets were inspected and reconciled only through `tx mng boot helpers`; the two private rollback snapshot IDs are listed above.
