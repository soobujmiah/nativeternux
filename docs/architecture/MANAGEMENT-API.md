# Management service and local HTTP contract

The shared typed service is implemented; full client/action parity and live qualification remain open in [client coverage](CAPABILITY-MATRIX.md) and [the audit](../audit/REPOSITORY-AUDIT.md). [Current handoff](../../CURRENT_STATE.md) and [phase state](../../project/phase-state.json) own progress. The API is internal version 1, with no released compatibility promise.

## Authoritative implementation

| Contract | Source |
|---|---|
| Operation names, argument allowlists and application dispatch | [management_service.py](../../lib/management_service.py) |
| Exact required capability per operation | [management_authorization.py](../../lib/management_authorization.py) |
| Memory-only bootstrap/session lifetime, scope and CSRF rules | [management_sessions.py](../../lib/management_sessions.py) |
| Host/Origin/method/body/rate validation | [request policy](../../lib/management_request_policy.py) |
| Authenticated typed HTTP dispatch and safe errors | [HTTP adapter](../../lib/management_http_adapter.py) |
| Private durable mutation admission/idempotency and audit metadata | [request store](../../lib/management_request_store.py) |
| Loopback listener, concurrency, deadlines and drain | [HTTP server](../../lib/management_http_server.py) |
| Read API versus interactive Web grants and browser handoff | [runtime](../../lib/management_http_runtime.py) |

CLI uses `tx mng` and specialized commands; TUI and the Native GTK bridge call the same local service. The local `caller` label is not network authentication. Browser clients use the authenticated loopback adapter. No management endpoint accepts arbitrary host commands, environment maps, file-write paths or ADB forwarding. [Interactive guest terminal transport](INTERACTIVE-PROOT-TERMINALS.md) is a separate fixed-profile, ownership-checked PTY contract.

## Transport and permissions

The foreground listener binds exactly to `127.0.0.1`. `/health` reports adapter liveness; `/ready` reports the owning listener's ability to accept work. Neither proves GUI visibility, SSH authentication or guest/workload readiness. Network deadlines do not cancel work already dispatched to the service.

The `/api/v1/session` exchange consumes one local bootstrap secret and narrows the requested capabilities to the runtime grant. Bearer and CSRF secrets remain in memory, outside URLs, ordinary logs and durable request records. Reload/restart continuity remains an open client issue; a consumed bootstrap secret is not reusable.

Typed requests to `/api/v1/operations` use `api_version`, `request_id`, `operation` and an allowlisted `args` object. Mutations require the exact capability, session-specific CSRF header and durable admission/idempotency policy. Unknown operations/scopes deny by default. The source owns per-operation preview, confirmation, journal and rollback semantics; some requested workflows remain incomplete.

The ordinary API permits its read capabilities and disables mutations. Authenticated Web mode separately grants scoped desktop/monitoring, managed SSH 8023 lifecycle, graphics, named apps/shortcuts, Cron definition changes and fixed PRoot/terminal actions. It does not grant arbitrary SSH configuration, 8022 lifecycle, broad shortcut sync, boot/recovery writes or scheduler/timezone writes. Use the runtime allowlists rather than a copied operation count.

## Web terminal generation wire contract

The authenticated `/api/v1/terminal` route keeps its broker attachment generation as an integer inside Native code. Its Web JSON lease encodes that random 63-bit generation as a canonical decimal string. Every follow-up Web terminal request must return that string unchanged. The adapter validates its bounded decimal syntax, converts it to the exact integer and compares it with the owned attachment before contacting the broker. Numeric JSON generations are rejected because JavaScript cannot represent every 63-bit value exactly. Session, attachment, origin, capability, CSRF and one-time channel-ticket checks still apply. [Live browser result](../evidence/2026-10-22-web-terminal-replay.md).

## Graphics and guest probe execution

`graphics.provider.status` for Debian performs installed-distribution inventory without entering the guest. It reports verification as not run. An explicit verification action is required for display/audio/renderer observations.

`graphics.provider.verify` and `proot.guest.verify` require `graphics.manage` and mutation CSRF in HTTP. They are excluded from ordinary read-only API access. The earlier `guest.diagnostics.read` scope is removed; clients must establish an explicitly permitted control session rather than treating guest execution as a read grant.

The bounded guest probe payload does not install packages or control services, but PRoot-Distro can write its generated guest profile during login even in isolated mode. Result `read_only` is false once login was attempted; `probe_payload_read_only` remains true and `safety.launcher_profile_write_possible` identifies the launcher effect, including failed/timeout attempts. This metadata is not a rollback proof. Exact guest-probe preview/rollback remains open under A29; preserve the working Codex guest during qualification.

## Browser launch and bootstrap

`tx web` offers Android, an installed Native browser, Debian Firefox ESR, or Auto (Native, then PRoot, then Android). Browser availability detection reads the validated rootfs executable without logging into it. Opening a selected PRoot browser remains an explicit guest launch and can run its launcher hooks.

Android receives the one-time code through clipboard stdin. Native/PRoot form handoff uses the bounded X11 path; code never belongs in process arguments or URLs. Default failed handoff closes the temporary server; private terminal fallback is explicit. [Browser evidence](../evidence/2026-10-22-native-ui-and-audit-remediation.md) separates responsive/visible checks from guest terminal acceptance. Exact focus targeting and reconnect behavior remain under audit.

## Related contracts and open work

- [SSH lifecycle](SSH-LIFECYCLE.md): 8023 is the fixed managed service; 8022 is the preserved owner development channel. Key generation/enrollment/revocation, exact rollback, managed-service autostart and next-start Wake Lock preferences have shared four-client controls; disposable authentication passed. Password/recovery decisions, post-repair live authentication, GTK visual interaction and cold-boot delivery remain open.
- [PRoot sessions](PROOT-SESSIONS.md): ownership, bounded profiles, exact stop plans and safe reconciliation. Interactive close discloses terminal hangup and verified private-session job groups; it never uses a force signal.
- [Cron registry](CRON-JOBS.md): saved definitions and shared preview/apply/history. Scheduler lifecycle, retry/cancellation/delivery and recovery have separate qualification.
- [Continuity](CONTINUITY-IMPLEMENTATION.md): observed boot, current readiness and private checkpoint status are distinct.
- [Testing](../testing/README.md): fixtures, fresh loopback checks, real clients and device/workload qualification prove different scopes.

I preserved the [earlier combined proposal and implementation narrative](history/2026-10-22-management-api.md) with its links relocated. Its duplicated status sections, former operation count, old commands, read-only guest execution claims and earlier client restrictions are historical. Broader resource routes, asynchronous progress/cancellation, inference and remote access in that proposal remain designs unless current source and evidence implement them.
