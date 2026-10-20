# Ternuxx management API proposal

**Status:** Local application-service slice, in-process HTTP request adapter, private durable request-store primitive, loopback HTTP server, and foreground runtime are implemented. The ordinary API runtime is read-only; authenticated Web mode exposes capability-scoped, durable native desktop and fixed managed SSH 8023 lifecycle, GUI monitoring policy, Native graphics selection, and named PRoot app launch. The owner has accepted CLI, interactive TUI, X11, and Web as clients of the same management system; see [ADR-0004](decisions/ADR-0004-three-interfaces-shared-management.md) and the [implementation plan](SHARED-MANAGEMENT-PLAN.md). Partial Web and TUI clients and a separate installed GTK4 management application now exist; graphics inventory and bounded verification are exposed through the same provider-aware operations to CLI, TUI, Web, and GTK clients; boot/service-manager configuration UI and broad resource parity remain incomplete. A default-deny capability map assigns every current API-v1 operation one explicit scope in [`lib/management_authorization.py`](../../lib/management_authorization.py), with parity tests against the service allowlist. [`lib/management_sessions.py`](../../lib/management_sessions.py) provides memory-only one-use bootstrap/session credentials with scope narrowing, expiry, mutation CSRF, and revocation. [`lib/management_request_policy.py`](../../lib/management_request_policy.py) validates loopback Host/Origin, methods, JSON content type, body size, and request rate. [`lib/management_http_adapter.py`](../../lib/management_http_adapter.py) ties these checks to typed application-service dispatch and security response headers. [`lib/management_request_store.py`](../../lib/management_request_store.py) provides private durable idempotency markers and a sanitized audit trail; the ordinary foreground API keeps mutation routes disabled; Web mode uses the durable request store and grants read scopes plus `desktop.manage`, `desktop.monitor.manage`, `ssh.managed.lifecycle`, `graphics.manage`, and `applications.launch`; these authorize only desktop lifecycle, monitoring policy, managed SSH 8023 start/stop, Native graphics selection, and `proot.app.launch` for fixed catalog IDs only (network requests cannot choose arbitrary desktop-entry IDs). PRoot session lifecycle, shortcut changes, SSH deployment/rollback, boot, and recovery remain unavailable to Web. Cron definition mutations require `cron.manage`, which the Web session does not receive. Timezone reads use `diagnostics.read`; `timezone.set` requires the separate `timezone.manage` capability and remains unavailable through Web because its mutation transport is disabled. The SSH lifecycle adapter targets only the fixed Runit-owned `ternuxx-sshd` service on 127.0.0.1:8023 and requires a fresh preview plan plus confirmation; port 8022 is excluded. [`lib/management_http_server.py`](../../lib/management_http_server.py) binds exactly to `127.0.0.1`, caps workers and request sizes, enforces a total connection deadline, rejects overload, and supports graceful drain. Deadline expiry closes the client connection but does not cancel an operation already running in the service thread. `/health` reports adapter liveness; `/ready` reports whether the owning listener has started and is still accepting work. It returns 503 when that probe is false; shutdown rejects new connections while draining. [`lib/management_http_runtime.py`](../../lib/management_http_runtime.py) creates a per-run bootstrap secret and displays it only on an interactive TTY. The canonical public namespace is `tx mng`; `tx management` is a deprecated compatibility alias. The Python dispatch contract remains internal API version 1, not yet a compatibility promise.

Current local API-v1 allowlist has 84 typed operations, including optional Hermes scheduler status inspection (`agent.hermes.status`, read-only; no task definitions or scheduler configuration are exposed), SSH inspection and fixed native Runit SSH start/stop, native desktop status/start/stop/restart, GUI monitoring status/configuration, and boot-profile status/preview/enable/disable, Ternuxx-only backup/restore, operation-journal reconciliation for SSH service and native boot-profile actions, plus restore rollback, Wake Lock status/acquire/release, continuity status/checkpoint/reboot-observer operations, and a read-only `remote.access.preview` operation for the secret-free private-access policy contract, and `proot.guest.verify` for a fixed, read-only probe of the selected installed Debian guest using an explicit user or the unique regular non-root account resolved from that rootfs. It verifies the actual guest display, renderer, and authenticated Native PulseAudio protocol endpoint without querying or invoking the separate Ternux CLI. The remote preview does not configure or probe a transport; guest verification does not expose general command execution or guest lifecycle controls. CLI wrappers route through `lib/management_service.py`; there is no generic shell execution operation. The browser uses the authenticated HTTP adapter; TUI and Native GTK use fixed local typed dispatch through the same `management_service` operation contract. The GTK bridge accepts fixed typed catalog, inspect, recovery-history, desktop start/stop, monitoring-policy, timezone preference, named PRoot app launch, and preview/apply verbs for managed SSH 8023; it does not accept shell commands or arbitrary operation payloads. The `caller` label is an in-process policy input, not an authentication mechanism, so it must not be exposed as a network API without a separately reviewed authenticated transport.

The management HTTP/TCP adapter and PRoot ADB are separate capabilities with independent identity, lifecycle, ports, authorization, and acceptance gates. The optional management listener binds loopback only when explicitly constructed and started; no service currently starts it. See [ADR-0014](decisions/ADR-0014-proot-adb-and-management-tcp.md). The management API exposes typed application-service operations and must not expose generic shell or ADB forwarding.

## Implemented shared PRoot GUI slice

The read-only `management.catalog` operation reports all shared domains, provider maturity, currently available operations, and planned capabilities. `doctor.report` exposes the existing read-only Doctor report through the same service. CLI entry points are `ternuxx management catalog list` and `ternuxx management doctor [--graphics]`. Cloud API is catalog-only and disabled; no credentials are returned or accepted.

The local application service exposes `proot.app.launch` on the verified Native Ternuxx display using either a fixed catalog ID or a validated Debian desktop-entry ID, plus `proot.shortcuts.sync`, `proot.shortcuts.list`, `proot.shortcuts.preview`, and `proot.shortcuts.apply`. Sync writes only Ternuxx-owned Native menu entries under the private XFCE XDG paths. Resource `proot.x11.shortcuts` identifies Debian PRoot as the app provider and native Termux as the desktop-entry storage owner. The list reports app availability as `unknown`; add previews verify the selected executable in the configured guest. The JSON contract is in [`schemas/proot-x11-shortcuts.schema.json`](../../schemas/proot-x11-shortcuts.schema.json).

CLI commands, generated desktop entries, and the X11 shortcut manager call this service. Add/remove previews bind to the exact target and current file state; apply requires the preview plan ID and explicit CLI or GUI confirmation. Only exact Ternuxx-generated entries can be replaced or removed. Unknown, customized, symbolic-link, and out-of-home targets fail closed. App launch accepts a catalog ID; the provider-specific launcher validates the active display and resolves the configured guest user from private Ternux state. The service reports GUI visibility as `unknown` and does not stop unrelated apps or desktop sessions.

The Web runtime grants diagnostic read scopes, `desktop.manage` for the native owned GUI lifecycle, `desktop.monitor.manage` for Activity/focus policy, `ssh.managed.lifecycle` only for preview-first start/stop of fixed managed SSH on port 8023, `graphics.manage` for Native backend selection, and `applications.launch` for catalog-listed PRoot app launches. Mutations require CSRF and a durable idempotency key; desktop and SSH lifecycle actions show confirmations with impact, graphics selection confirms the future-start effect, and named PRoot app launch requires a per-app browser confirmation. Port 8022, SSH deployment/rollback, boot, recovery, PRoot session lifecycle, and shortcut edits are not granted. The ordinary HTTP runtime remains read-only. The client receives a one-time secret in the terminal; browser-friendly bootstrap remains unimplemented. Ordinary foreground API mode keeps mutations disabled.

## Ternuxx-owned PRoot session operations

The local typed service exposes proot.profiles.list/show, proot.sessions.list/show/health, proot.start.preview/start, proot.stop.preview/stop, proot.recovery.inspect, proot.recovery.reconcile.preview, and proot.recovery.reconcile for the fixed Debian profile registry. Read and preview calls require diagnostics.read; start and stop require proot.session.manage, an exact fresh plan and confirmation. Recovery inspection is read-only. Reconciliation requires a fresh preview, exact confirmation and positive evidence that the recorded process exited or its PID was reused; it marks the record exited without signaling or adopting the current process. The foreground interactive profile uses a private controlling PTY, requires a real caller TTY, and is not exposed to Web/background callers. A live login passed cwd, guest UID/GID, marker, rootfs, launcher, process-start, and session-group verification, then exited cleanly. Startup waits a bounded five seconds for installed proot-distro to exec the actual PRoot process; a mismatch still fails closed. Its start preview discloses that installed proot-distro normal-login code can write the shared guest profile and container sidecar state. Its CLI remains attached until the shell/session exits; no detach/reattach capability is advertised. The Web adapter grants only `applications.launch` for named PRoot app launch; it does not grant `proot.session.manage` or expose PRoot session lifecycle. See [PRoot session ownership](PROOT-SESSIONS.md).

## Current UI surface audit — 2026-10-19

## Current UI implementation — 2026-10-19

All four client surfaces now use the catalog's stable categories/resources and the same management operation service. CLI remains the broadest command surface. TUI navigation is category-first, searchable, concise, and no longer asks ordinary users for raw operation IDs or JSON; it supports safe no-argument status inspection, guided PRoot app launch, confirmed native desktop start/stop, preview-confirmed managed SSH 8023 start/stop, advanced recovery journal history, and GUI monitoring-policy configuration. Web Console renders categorized searchable/filterable resources and details from `management.catalog`, invokes supported read operations, supports confirmed desktop lifecycle requests, preview-confirmed managed SSH 8023 start/stop, exposes recovery journal history, and edits the GUI monitoring policy over the authenticated loopback API. Its session grants read scopes plus `desktop.manage`, `desktop.monitor.manage`, and the narrowly scoped `ssh.managed.lifecycle`; SSH deployment/rollback and other mutations remain unavailable. The separate GTK4 application is installed at `$PREFIX/libexec/ternuxx/management-center`, launched with `tx gui` (also available as `tx mng center`), and uses the same typed local management-service dispatcher through `scripts/management_desktop_bridge.py`. It offers categorized searchable resource browsing, live inspection, confirmed desktop start/stop, preview-confirmed managed SSH 8023 start/stop, a recovery-history action, and the Activity/focus policy form.

The client theme uses a green-on-dark palette and the shared `implemented`, `partial`, `external`, `unverified`, `unavailable`, and `planned` capability vocabulary. Activity/focus monitoring defaults off; status operations do not launch Termux:X11. Port 8022 remains inspect-only. The browser uses CSRF and durable idempotency for mutations; GTK/TUI actions are fixed typed operations and never generic shell execution.

Current interface gaps: the GTK app has not been opened for visual/manual interaction testing; no automatic Activity polling was enabled. The TUI now lists its implemented guided actions for the selected resource; Web mobile CSS has been tightened, but rendered mobile acceptance remains unverified. These clients do not yet expose SSH 8023 deployment/rollback, boot enablement, PRoot shortcut apply/remove, recovery apply, generic server deployment, safe service-log readers, or operation progress. Read-only recovery journal history is available in Web, TUI, and GTK. Web lifecycle calls are synchronous within the API deadline, so long-running operation identity/progress is not yet implemented. These gaps do not change the P3 gate or certify P4 compatibility.

## 1. Contract principles

- Version base path: `/api/v1`; incompatible contract changes require a new major version.
- Intended caller: the same-device visualizer. Default listener is loopback only; no LAN binding.
- Transport is an adapter to the shared application services. CLI and HTTP do not keep separate business rules.
- Request bodies are typed and validated. Never accept a shell command or arbitrary environment map as an operation.
- Mutations are previewed, explicitly confirmed, executed as tracked operations, and verified.
- Use a separate inference API/auth scope if one is implemented; this API is privileged workstation management.
- This proposed interface does not mean these operations are currently available.

## 2. Resource shapes

### Error

```json
{
  "error": {
    "code": "confirmation_required",
    "message_key": "operation.confirmation_required",
    "request_id": "opaque-id",
    "details": {"plan_id": "opaque-plan-id"}
  }
}
```

Messages may be localized by the client using `message_key`; do not make clients parse prose. Never include stack traces, keys, prompts, or sensitive paths in public error text.

### Operation

```json
{
  "id": "opaque-random-id",
  "kind": "service.start",
  "state": "running",
  "stage_key": "service.waiting_for_ready",
  "progress": null,
  "created_at": "RFC3339 timestamp",
  "updated_at": "RFC3339 timestamp",
  "cancellable": true,
  "provider": "native_termux",
  "result": null,
  "error": null
}
```

`progress` is `null` unless a truthful percentage is available. Stages are preferred for package/runtime tasks without a meaningful percentage. Operation states and transition rules are defined by the shared application layer; see [unified architecture](UNIFIED-WORKSTATION.md#5-operation-and-state-model).

### Capability

```json
{
  "id": "inference.gpu.native",
  "provider": "native_termux",
  "stage": "detected",
  "status": "unknown",
  "workload_id": null,
  "evidence_id": null,
  "limitations": ["No verified workload"],
  "observed_at": "RFC3339 timestamp or null"
}
```

Never infer `active` from hardware presence. Workload and evidence references are mandatory for `workload_verified` or `release_qualified`.

## Timezone preference operations

The shared service exposes `timezone.status`, `timezone.list`, and `timezone.set`. Reads require `diagnostics.read`; changing the persisted preference requires the distinct `timezone.manage` capability. The local CLI supports all three. The authenticated Web runtime does not grant `timezone.manage`, and its mutation transport remains disabled for this operation. The Native Termux provider reads Android's packed tzdata when ordinary TZif files are unavailable; status reports the provider and database version. No location or external IP-geolocation request is made.

## Cron Job Registry operations

The shared service provides `cron.status`, `cron.jobs.list`, `cron.jobs.show`, `cron.jobs.validate`, `cron.jobs.next_runs`, `cron.jobs.create`, `cron.jobs.update`, and `cron.jobs.remove`. Read/preview operations require `diagnostics.read`; create/update/remove require `cron.manage`. See [Cron Jobs](CRON-JOBS.md) for persistence, schedule and trigger semantics. These calls manage definitions only: there is no scheduler, executor, run history, Termux:Boot delivery, or scheduler-recovery delivery. Web/TUI/GTK currently expose status and list reads only; the CLI and API support typed registry changes. Web does not receive `cron.manage` and must not present mutation controls.

## 3. Proposed route groups

All routes below are design candidates. Read routes may return unavailable/unknown modules instead of pretending they are implemented.

| Method/path | Purpose | Safety |
|---|---|---|
| `GET /api/v1/status` | Overall app/provider/service summary | Redact IDs and private paths; read-only. |
| `GET /api/v1/capabilities` | CPU/GPU/NPU/provider stages and evidence references | Include context, age, limitations. |
| `GET /api/v1/services` | Service status, owner/provider, health | Expose only Ternuxx-managed records. |
| `GET /api/v1/launch-targets` | Available named launch targets and their provider/requirements | Do not expose shell strings or private paths; unavailable providers remain explicit. |
| `GET /api/v1/launch-profiles` | Configured workspace and boot profile summaries | Return selected targets only; boot remains opt-in. |
| `GET /api/v1/launch-sessions` | Managed GUI/service sessions and allocated resources | Only sessions with verified Ternuxx ownership; distinguish server health from Android activity visibility. |
| `GET /api/v1/shell-profiles` | Native and PRoot shell selections, adapter readiness, theme and managed-config revision | Separate providers; redact host and guest paths. |
| `GET /api/v1/shells` | Shell availability and version per provider | Detection is not installation or selection; report unknown when not checked. |
| `GET /api/v1/shell-themes` | Built-in themes supported by each provider/shell adapter | Include provenance, compatibility and whether optional dependencies are required. |
| `GET /api/v1/shell-config/{provider}` | Current managed shell configuration and revision | Return only Ternuxx-owned settings/snippets; never dump arbitrary user RC files. |
| `GET /api/v1/software/catalog` | Provider-specific optional software IDs, availability, dependencies, and evidence | No executable commands or arbitrary install strings in catalog output. |
| `GET /api/v1/software/selections` | Saved desired optional selections by provider | Desired state is not proof of installed state; keep these distinct. |
| `POST /api/v1/software/plan` | Preview selected optional catalog IDs for native and/or an explicitly selected PRoot guest | No side effects; return exact provider, repository/package IDs, dependency closure, conflicts, size confidence, and protected-target check. |
| `GET /api/v1/models` | Managed model metadata and sessions | Never scan arbitrary paths. Hide private full paths by default. |
| `GET /api/v1/runtimes` | Runtime installation/readiness/compatibility | Detection is not execution proof. |
| `GET /api/v1/providers` | Native, PRoot, local runtime and configured cloud provider states | Cloud configuration never returns credentials. |
| `GET /api/v1/operations` | Paginated local operation history | Redacted, bounded retention. |
| `GET /api/v1/operations/{id}` | Operation state/result/error | Enforce ownership and authorization. |
| `GET /api/v1/operations/{id}/events` | Progress/event stream, preferably SSE | Same-origin/session protected; bounded/reconnectable; no secret values. |
| `POST /api/v1/plans` | Validate request and produce exact preview | No side effects; include plan hash/state version/expiry/impact. |
| `POST /api/v1/shell-profiles/plan` | Preview shell selection, theme change, managed-config edit, or package requirement for a specified provider | Typed operation only; do not accept arbitrary command text or write paths. |
| `POST /api/v1/shell-profiles/migration-plan` | Preview migration from the current shell to another shell within the same provider | Show mapped, unsupported, and user-selected import entries; never execute or raw-copy the old RC file. |
| `POST /api/v1/shell-config/validate` | Validate a draft against its selected shell/provider adapter | No file writes or package changes; return structured diagnostics. |
| `POST /api/v1/shell-config/preview` | Produce a unified diff and rollback/backup plan for a managed config or theme change | No side effects; bind the preview to provider, shell, revision, and exact draft hash. |
| `POST /api/v1/plans/{id}/confirm` | Confirm one exact, unexpired plan | Single-use session-bound token; revalidate state and permissions. Creates operation ID. |
| `POST /api/v1/operations/{id}/cancel` | Request cooperative cancellation | Return whether cancellation was accepted; never imply immediate rollback. |
| `GET /api/v1/evidence/reports` | List local test reports and qualification states | Filter/paginate, redact identifying facts. |
| `POST /api/v1/diagnostics/export-plan` | Preview a safe diagnostics export | No upload; reveal fields/redactions before local export. |

The broader Native SSH lifecycle contract, deployment/migration routes, and configuration changes remain specified separately in the [Native SSH lifecycle contract](SSH-LIFECYCLE.md). The current client scope includes only preview-first start/stop of the already managed 8023 Runit service; it does not grant configuration, deployment, or 8022 lifecycle control.

Avoid generic `POST /command`, `POST /shell`, arbitrary file write, arbitrary URL fetch, and generic proxy endpoints. Each state-changing operation type must have a named application service and explicit input schema. Launch plans use named operation kinds such as `launch.run`, `launch.stop`, `launch.restart`, and `boot.profile.set`; a target ID is resolved against the validated registry and never treated as a command line.

Optional software installation uses `POST /api/v1/software/plan` with provider names and catalog IDs only. It resolves each provider through its own package adapter, previews dependency closure and exact target, and cannot silently retry in another provider. Core-only is the noninteractive default. A PRoot plan identifies a Ternuxx-managed guest; the existing Ternux rootfs is excluded unless a separately approved integration explicitly scopes it.

## 4. Mutation lifecycle

1. Client submits a typed request to create a plan.
2. Server validates current state, provider ownership, prerequisites, path scope, and user permission; returns affected resources, exact package/model/service changes, risks, cancellation/rollback limits, plan hash, and expiry.
3. Client presents the plan and obtains deliberate user confirmation. Confirmation is bound to the exact plan, action, current state version, session, and short expiry.
4. Server revalidates and consumes the confirmation once; creates an opaque operation ID and journals the action before mutation.
5. Client polls the operation or subscribes to events. Events use stable codes, stage keys, timestamps, and redacted diagnostics.
6. Server reports verified outcome, fallback, partial state, or `needs_recovery`; it never marks success from process creation alone if readiness is required.

Cancellation and rollback are distinct. A cancelled task may have partial effects; response includes the observed state and next recovery action.

## 5. Local web security

- Listen on explicit loopback addresses only, not `0.0.0.0`/`::`.
- Validate `Host` against the exact local origin and validate `Origin` on browser mutations. Reject missing/unexpected origins where browser session semantics require it.
- Same-origin static UI; no wildcard CORS. Use a CSRF token and custom request header for mutations.
- Issue an unpredictable short-lived local session token through a reviewed bootstrap flow. Do not put it in URLs, localStorage, logs, or copied links. Prefer memory-only browser storage; refresh by explicit local session establishment.
- Bind session to an explicit permission scope and inactivity expiry. Read-only status can have lower scope than mutation confirmation.
- A future adapter must enforce the exact scope assigned to each operation by `lib/management_authorization.py`; unknown operations and missing scopes deny by default. The map is not session/bootstrap authentication and grants no authority by itself.
- The current session primitive stores only token digests in memory, consumes its local bootstrap secret once, caps session lifetime, narrows session scopes to launcher-approved scopes, requires a session-specific CSRF proof for mutations, and supports individual/global revoke. It does not define how a launcher securely presents the bootstrap secret or persist/recover sessions.
- The request-policy helper and in-process adapter enforce exact loopback origin/Host, GET/POST, bounded JSON POST bodies, request rate, authorization, CSRF, safe error shaping, no-store/security response headers, and mutation replay checks. The optional durable request store writes private at-most-once markers and allowlisted audit metadata, never request bodies, arguments, tokens, or responses. A completed or interrupted duplicate is not replayed; callers must inspect fresh state. Mutation transport remains disabled by default and requires explicit opt-in plus a durable store. Session credentials remain memory-only, so a process restart invalidates sessions. The optional HTTP server binds only to `127.0.0.1`, caps concurrent workers at 16, bounds headers/body and total request time, rejects excess connections, and drains in-flight handlers during shutdown. Deadline expiry closes the HTTP connection; it does not cancel an operation already dispatched to a service. The server has no automatic startup/service integration, and no device listener or browser qualification has been run.
- `GET /health` is the adapter liveness route. `GET /ready` returns `ready=true` only while the owning loopback listener's serving thread is alive and not shutting down; otherwise the adapter returns 503 with `ready=false`. It passes through the same Host/Origin and rate policy. During drain, the listener rejects new connections. Readiness indicates transport availability, not Android GUI visibility, guest ownership, SSH reachability, or workload readiness.
- Limit request bodies, concurrent operations, event backlog, and request rate. Reject content types not in the route schema.
- Sanitize output, validate paths after canonicalization, and prevent symlink escape from managed roots.
- Avoid storing prompt/model contents or provider secrets in operation records. Redact identifiers before report export.
- Optional off-home access is an owner-approved product requirement under [ADR-0013](decisions/ADR-0013-owner-controlled-remote-access.md). Implementation and device enablement still require transport-specific threat review and explicit owner action; keep loopback services unchanged and do not enable remote mode through a configuration toggle alone.

## 6. Separate inference interface

If a local inference API is selected, define it independently. A compatible `/v1/...` route may be useful, but is an owner/runtime decision. It must not inherit administrative authority. Use a separate token/scope, explicit model allowlist, input/token/resource limits, and provider routing policy. A cloud request must identify the data destination and must not happen as an invisible fallback from a local route. Avoid request-body logging by default.

## 7. Client compatibility and errors

Clients declare supported API major version. Server returns a clear unsupported-version error for unknown major versions and an additive capability list for optional modules. A feature absent from the current build returns a stable `not_implemented`/`provider_unavailable` code rather than a fabricated empty success.

Expected errors include `invalid_request`, `permission_denied`, `confirmation_required`, `plan_expired`, `state_changed`, `provider_unavailable`, `not_implemented`, `resource_busy`, `operation_not_cancellable`, `needs_recovery`, and `rate_limited`. Each error has a stable code, localized message key, request ID, and safe details.

## 8. Contract validation before implementation

Before coding, review this draft against the chosen implementation language, Termux process model, API security tests, CLI service boundaries, and accessibility/localization approach. Add schema validation and contract tests before exposing the listener. Tests must prove: no non-loopback binding; origin/CSRF rejection; no credential echo; preview/confirm state binding and single use; exact operation ownership; path traversal rejection; cancellation honesty; and consistent CLI/API service outcomes. CI-only tests do not establish Android device readiness.


## Categorized resource discovery (catalog v2)

`management.catalog` accepts optional `category`, `query` (up to 120 characters), and `status` filters. The response uses schema version 2 and returns stable categories, resource descriptors, supported/planned operations, dependency hints, authority, boot/background policy, diagnostics, recovery and source identity. Discovery is read-only: it does not probe Android Activity/focus, start services, or reconcile live resources. Use `tx mng catalog list [--category ID] [--query TEXT] [--status STATE]`.

A listed operation is exposed only when present in the shared API allowlist. Port 8022 is an external read-only resource; 8023 is the existing Ternuxx/runit managed resource. A catalog entry does not imply ownership or live health. Audio ownership, Android cold-boot readiness, and PRoot process ownership remain unverified where the resource descriptor says so. The response is defined by `schemas/management-catalog.schema.json`.
## Browser bootstrap and clipboard handling

The `tx web` browser launcher creates a memory-only one-time bootstrap secret and sends it on stdin to `termux-clipboard-set`; the generic `tx mng http serve` API path is unchanged. The Web secret is not placed in a URL or routine output. If clipboard copy fails, the server closes without disclosing the secret. An operator may explicitly pass `--show-secret-on-clipboard-failure` to use a private terminal fallback. Device clipboard mutation is only performed when the owner invokes `tx web`; fixture tests do not alter the live clipboard. The web server remains loopback-only.


## Cron execution history slice — 2026-10-19

API v1 adds read-only cron.executions.list and cron.executions.show under diagnostics.read. The CLI exposes tx mng cron executions list [--job-id ID] [--limit N] and show EXECUTION_ID. History uses the private schema-v1 ledger; it does not start a scheduler or execute a job. TUI, Web and GTK do not yet expose execution-history controls. Cron status distinguishes the available internal execution core from the absent scheduler process. Mutating execution, scheduler lifecycle, cancellation, retries and trigger delivery have no API operations.


## Cron runtime and PRoot session inventory (2026-10-19)

The API now includes cron.scheduler.start and cron.scheduler.stop, classified as
mutations requiring the narrow cron.scheduler.manage scope and mutation CSRF in
authenticated HTTP transport. Start accepts only a bounded poll interval;
stop requires an explicit confirmed=true. Neither operation is granted by the
current Web bootstrap. cron.status separates scheduler process liveness, lease
ownership and dispatch health. PRoot session list/show operations are read-only
and use the shared private ownership registry. A general PRoot lifecycle mutation
is not exposed through the API; only the fixed isolated probe was exercised by
the internal lifecycle test module.


## Termux:Boot Cron integration operations

The local shared service exposes `boot.cron.status`, `boot.cron.validate`, and `boot.cron.preview` as `diagnostics.read`; `boot.cron.enable` and `boot.cron.disable` require `boot.manage`. Enable/disable require an exact fresh preview plan ID and explicit confirmation. The server-side manager only creates/removes the dedicated `20-ternuxx-cron` file after identity checks; the Web bootstrap does not receive `boot.manage`, so Web remains read-only. The script invokes only the Cron scheduler CLI. Neither API inspection nor preview starts the scheduler or changes startup files.


## Ternuxx-owned Debian sessions (2026-10-20)

The shared service exposes profile/session reads and preview-first lifecycle operations: proot.profiles.list/show, proot.sessions.list/show, proot.start.preview, proot.start, proot.stop.preview, and proot.stop. Reads/previews use diagnostics.read; start/stop require the narrow proot.session.manage capability and exact plan ID plus confirmation. The fixed profiles are isolated-probe and debian-interactive; neither accepts arbitrary shell strings. The latter requires a local TTY and enters the already installed Debian guest as sbj, matching the db alias's distro/user/shared-tmp selection. It does not start GUI or services.

The HTTP runtime does not grant proot.session.manage, so Web mutation stays unavailable. TUI and GTK remain read-only for PRoot lifecycle. Full profile/process ownership rules, schema-v1 migration, rootfs/launcher identity and live disposable-probe evidence are in [PRoot session architecture](PRoot-SESSIONS.md). Existing unmanaged guest processes remain unowned. Interactive shell and GUI lifecycle qualification remain outstanding.
