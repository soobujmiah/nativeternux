# Ternuxx management API proposal

**Status:** Local application-service slice, in-process HTTP request adapter, private durable request-store primitive, loopback HTTP server, and explicit read-only foreground runtime are implemented. The owner has accepted CLI, X11, and Web as clients of the same management system; see [ADR-0004](decisions/ADR-0004-three-interfaces-shared-management.md) and the [implementation plan](SHARED-MANAGEMENT-PLAN.md). No Web client, general X11 management client, or boot/service-manager integration is implemented. A default-deny capability map assigns every current API-v1 operation one explicit scope in [`lib/management_authorization.py`](../../lib/management_authorization.py), with parity tests against the service allowlist. [`lib/management_sessions.py`](../../lib/management_sessions.py) provides memory-only one-use bootstrap/session credentials with scope narrowing, expiry, mutation CSRF, and revocation. [`lib/management_request_policy.py`](../../lib/management_request_policy.py) validates loopback Host/Origin, methods, JSON content type, body size, and request rate. [`lib/management_http_adapter.py`](../../lib/management_http_adapter.py) ties these checks to typed application-service dispatch and security response headers. [`lib/management_request_store.py`](../../lib/management_request_store.py) provides private durable idempotency markers and a sanitized audit trail; the foreground runtime keeps mutation routes disabled. [`lib/management_http_server.py`](../../lib/management_http_server.py) binds exactly to `127.0.0.1`, caps workers and request sizes, enforces a total connection deadline, rejects overload, and supports graceful drain. Deadline expiry closes the client connection but does not cancel an operation already running in the service thread. `/health` reports adapter liveness; `/ready` reports whether the owning listener has started and is still accepting work. It returns 503 when that probe is false; shutdown rejects new connections while draining. [`lib/management_http_runtime.py`](../../lib/management_http_runtime.py) creates a per-run bootstrap secret and displays it only on an interactive TTY. The Python dispatch contract remains internal API version 1, not yet a compatibility promise.

Current local API-v1 allowlist includes SSH inspection and fixed native Runit SSH start/stop, native desktop and boot-profile status/preview/enable/disable, Ternuxx-only backup/restore, operation-journal reconciliation for SSH service and native boot-profile actions, plus restore rollback, Wake Lock status/acquire/release, continuity status/checkpoint/reboot-observer operations, and a read-only `remote.access.preview` operation for the secret-free private-access policy contract, and `proot.guest.verify` for a selected Ternux guest companion status check plus fixed, typed native `ternux --json status` and `ternux --json backend show` summaries when available. Native Ternux values remain self-reported with identity and ownership unverified; the configured backend and renderer are kept separate from the actual guest renderer, and the process-based PulseAudio field is kept separate from the typed native `pactl info` endpoint summary; neither is treated as audible-output proof. The remote preview does not configure or probe a transport; guest verification does not expose general command execution or Ternux lifecycle controls. Its optional `user_source=ternux-state` resolves the guest account from Ternux's private state file in memory and never places the account value in the response. CLI wrappers route through `lib/management_service.py`; there is no generic shell execution operation. Calls from a non-CLI interface are rejected by the current dispatch policy. The `caller` label is an in-process policy input, not an authentication mechanism, so it must not be exposed as a network API without a separately reviewed authenticated transport.

The management HTTP/TCP adapter and PRoot ADB are separate capabilities with independent identity, lifecycle, ports, authorization, and acceptance gates. The optional management listener binds loopback only when explicitly constructed and started; no service currently starts it. See [ADR-0014](decisions/ADR-0014-proot-adb-and-management-tcp.md). The management API exposes typed application-service operations and must not expose generic shell or ADB forwarding.

## Implemented shared PRoot GUI slice

The read-only `management.catalog` operation reports all shared domains, provider maturity, currently available operations, and planned capabilities. `doctor.report` exposes the existing read-only Doctor report through the same service. CLI entry points are `ternuxx management catalog list` and `ternuxx management doctor [--graphics]`. Cloud API is catalog-only and disabled; no credentials are returned or accepted.

The local application service exposes `proot.app.launch` (an explicit, read-only-preflighted `session_owner=ternux` and display selection is available for an already-running native Ternux session), `proot.shortcuts.list`, `proot.shortcuts.preview`, and `proot.shortcuts.apply`. Resource `proot.x11.shortcuts` identifies Debian PRoot as the app provider and native Termux as the desktop-entry storage owner. The list reports app availability as `unknown`; add previews verify the selected executable in the configured guest. The JSON contract is in [`schemas/proot-x11-shortcuts.schema.json`](../../schemas/proot-x11-shortcuts.schema.json).

CLI commands, generated desktop entries, and the X11 shortcut manager call this service. Add/remove previews bind to the exact target and current file state; apply requires the preview plan ID and explicit CLI or GUI confirmation. Only exact Ternuxx-generated entries can be replaced or removed. Unknown, customized, symbolic-link, and out-of-home targets fail closed. App launch accepts a catalog ID; the provider-specific launcher validates the active display and resolves the configured guest user from private Ternux state. The service reports GUI visibility as `unknown` and does not stop unrelated apps or desktop sessions.

The local HTTP API can perform the read operation under its read scope. HTTP mutation transport remains disabled, and `applications.manage`/`applications.launch` are not granted by the current browser runtime. No Web client or browser session bootstrap is implemented yet.

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

Native SSH lifecycle routes, setup/migration, state transitions, configuration schemas, and redaction rules are specified in the [Native SSH lifecycle contract](SSH-LIFECYCLE.md). Those routes are still proposed; adding them here does not mean any interface or SSH service manager is implemented.

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
