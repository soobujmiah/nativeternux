# ADR-0011: Unified Native SSH connection and lifecycle management

- **Status:** Accepted owner requirement; contract documented, implementation pending
- **Date:** 2026-10-17
- **Type:** native-service-management

## Context

Native Termux owns native SSH connectivity and must recover it without Debian PRoot or a guest agent. The owner also requires guided first-time setup, compatible migration from the existing manual SSH setup, secure identity/authentication handling, boot recovery, Wake Lock ownership, continuity evidence, and consistent CLI/Web/X11 management. The repository currently has SSH proposals but no shared SSH service implementation or management UI. The active manual server's configuration and ownership remain unknown until a redacted read-only inspection.

## Decision

Use one `native_ssh` application service as the authority for discovery, config plans, authentication policy, service lifecycle, Termux:Boot, Wake Lock leases, connectivity tests, and recovery. CLI calls the service directly; Web and X11 GUI call the same versioned API. Keep desired config, secret/key references, and observed runtime/continuity state separate. Preserve the current Termux principal, manual keys, auth policy, listener, and session until a replacement is staged, validated, explicitly approved, and has a verified rollback path. Do not create a Linux OS user implicitly.

PRoot is an independent optional provider. Native SSH, boot, and continuity work without it. PRoot may use named bounded native diagnostics over configured SSH after separate authorization; connectivity is not blanket permission. The interface, state machine, schema, setup/migration, security, and test contracts are in [SSH-LIFECYCLE.md](../SSH-LIFECYCLE.md).

## Consequences

- SSH management cannot be independently reimplemented in CLI, Web, or X11 clients.
- A setup wizard validates before persisting active desired configuration and never overwrites unknown/manual config or keys.
- Web management authentication is distinct from SSH client authentication and the Android Termux login principal.
- Termux:Boot is native-only and optional; Wake Locks default off and use per-owner leases.
- Public docs and reports contain no secrets, key bytes, raw config, or private paths.
- Acceptance remains pending until test fixtures/contracts and owner-operated physical-device checks pass.

## Alternatives rejected

- **Direct `sshd_config` writes from each UI:** bypasses shared validation, authorization, migration, and rollback.
- **Stop the current `sshd` then test a replacement:** can interrupt the working session before the replacement is known to work.
- **Use PRoot/systemd/agent for native recovery:** violates native ownership and reboot independence.
- **Treat SSH authentication as management authorization:** grants more authority than the connection requires.
- **Create arbitrary Termux OS users:** Android/Termux process identity is not a general Debian user-management facility.

## Evidence status

No setup, SSH lifecycle, API, GUI, Web UI, boot, or Wake Lock operation is implemented or qualified by this ADR. The active manual setup must first be inspected read-only with sensitive values redacted. See the [phase roadmap](../../ROADMAP.md) for the implementation gate.
