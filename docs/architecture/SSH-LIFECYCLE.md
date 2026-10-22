# Native SSH connection and lifecycle contract

Native Termux owns SSH and recovery; Debian PRoot is an optional client/provider. Port 8022 is the owner's development channel and is inspection-only for Ternuxx lifecycle. Port 8023 is the separate loopback-only `ternuxx-sshd` product service. Preserve both channels during this task.

[Client coverage](CAPABILITY-MATRIX.md), [phase state](../../project/phase-state.json), and [the repository audit](../audit/REPOSITORY-AUDIT.md) own current progress. The earlier combined design/runtime narrative is preserved in [dated history](history/2026-10-22-ssh-lifecycle.md); its old daemon, password, PID, listener-correlation and command-name claims are historical.

## Implemented behavior

`tx ssh inspect` and `native.ssh.status` report redacted configuration, service/process identity, effective bind/auth policy and bounded loopback banner reachability. They do not read credential files, expose raw config or authenticate. Procfs and SOCK_DIAG listener observations are separate; restricted visibility remains unknown.

`tx ssh start|stop` first previews the exact fixed service. Apply requires `--yes --plan-id PLAN_ID`, rechecks definition/manager/state identity and journals before Runit control. All four clients expose scoped managed-8023 status/start/stop through the common service. A catalog entry alone is not a client action.

`lib/runit_deployment.py` separately reconciles the fixed run definition using a validated plan, private backup and rollback. Definition replacement does not restart a daemon or change SSH config. Credential wizard, general connection profiles, authenticated post-action readiness, caller-session correlation, SSH boot toggle and selectable Wake Lock policy remain incomplete.

Current Native inspection reports the 8023 loopback service running with valid configuration, verified process/definition identity, a protocol banner and effective `AuthenticationMethods publickey`. Kernel listener-to-process correlation remains unknown when Android denies both observation paths. This inspection is not a fresh authenticated-login test. [RB08](../evidence/2026-10-22-p3-rb08-postboot-exit-audit.md) records its separately dated authenticated check.

## Identity and credential requirements

Keep the Native Termux account, SSH client key, SSH server host key, management session and guest account distinct. Client private keys stay with their client; the server receives only public authorization material. A management login is not SSH login proof, and an SSH login is not automatic API authorization.

Key generation/enrollment/removal, password management and recovery must be implemented as typed shared-service operations before their CLI/TUI/Web/GTK controls become active. Each mutation needs a redacted inventory, exact preview, explicit confirmation, serialized write, preserved working access and tested rollback. Never overwrite an existing key, rotate host identity implicitly, log private material or export credentials into repository/evidence/ordinary backups.

The existing 8022 and 8023 endpoints share one Termux account. A password reset or shared authorized_keys edit can affect both endpoints. A credential preview must identify that impact; it cannot describe an account-wide change as 8023-only. Protect the current development identity and retain a proven local recovery path. A future separately scoped authorized-key file requires an explicit, validated managed-config migration.

A lost private key is not recoverable from its public key. Recovery needs a working authorized client or local Termux access to enroll a replacement. Do not suggest password recovery when effective service policy rejects passwords. Auth policy is discovered live and preserved until replacement access is verified.

If new private material is explicitly requested, use a new unused private destination and a protected reference; distinguish file permissions from hardware-backed storage. No secrets in command arguments, URLs, public logs, screenshots, journal payloads or Git.

## Shared service and lifecycle rules

CLI, guided TUI, authenticated loopback Web and GTK use the same typed management contracts. Clients do not write configs, keys or boot files directly. There is no arbitrary-command endpoint. Native control remains available without PRoot or a graphical client.

A future setup/migration plan must identify provider, principal, endpoint, current ownership, selected auth, host identity, affected sessions, boot/Wake Lock effects, rollback and exact owned paths. Validate a separately staged config with sshd and a bounded authenticated candidate connection before cutover. Unknown ownership, endpoint conflicts, failed auth or ambiguous identity blocks mutation. Never stop an external daemon to make validation possible.

Stop/restart must account for the caller's access path and preserve an out-of-band recovery route or obtain explicit acknowledgement of the exact disconnect. Journal before mutation; repeated requests must not duplicate daemons, authorization entries, boot hooks or Wake Lock owners. Broader setup/recovery and remote-access scope remain planned.

## Boot, Wake Lock and continuity

The installed Native service boot helper starts the official Runit supervisor and checks managed SSH readiness. It does not enter PRoot. Per-service SSH startup selection is not implemented. The current run script acquires the `native.sshd` lease; owner-selectable lease policy remains a requested feature. A proposal's “never by default” policy is not the current installed behavior.

Wake Lock accounting is owned by `lib/wakelock_manager.py`. A workload may release only its own lease; stopping a guest cannot release Native SSH's lease. Android's app-global holder state can remain unknown even when Ternuxx accounting is verified.

[Continuity implementation](CONTINUITY-IMPLEMENTATION.md) distinguishes boot observations, current readiness and private checkpoints. No agent/task resumes automatically. Existing rootfs, host identity, working clients and owner-managed 8022 remain preserved.

## 8. Test contract and fixtures

The original SSH-01–SSH-15 acceptance matrix remains in [the preserved contract](history/2026-10-22-ssh-lifecycle.md#8-test-contract-and-fixtures). Its fresh-setup, candidate/auth failure, identity/no-overwrite, client parity, idempotency, boot, Wake Lock, provider independence, authorization and conflict cases remain requirements; listed cases are not proof of executed coverage.

[Fixtures](../../tests/fixtures/ssh/README.md) contain synthetic metadata, never live credentials. Current fixtures cover diagnostics, fixed lifecycle/deployment, plans, journals, rollback and security boundaries. Complete credential/setup/client acceptance and a safe disposable runtime replay remain open. Existing Codex PRoot and Native Termux must not be stopped for an independence test.

## Evidence boundaries

[Current entrypoint inventory](../evidence/2026-10-22-native-entrypoint-inventory.json) checks all three source Runit definitions, all three boot helpers, tx shim and installed canonical recovery modules. It does not certify all configuration, future boot execution or fresh setup. [8023 procedures](../testing/8023-deployment-and-lifecycle.md) and dated evidence describe earlier lifecycle/authentication results; use live inspection for current process, policy and ownership facts.
