# Shared management implementation plan

**Owner direction recorded:** 2026-10-18
**Architecture:** [ADR-0004](decisions/ADR-0004-three-interfaces-shared-management.md)
**Current project phase:** P4 - Existing Ternux PRoot feature-parity provider — Doctor, management, and recovery

## Product requirement

CLI, X11 GUI, and local Web UI must manage the same Ternuxx resources through the same application-service operations and provider-aware configuration. Routine setup, status, configuration, launch, recovery, and removal must be understandable without CLI knowledge. CLI remains available when graphical services are stopped.

“One system” means one management experience and one Ternuxx-owned state model. It does not merge the native Termux filesystem with the independent Debian PRoot, grant one provider the other's permissions, or let Ternuxx modify the separate Ternux project/rootfs outside an approved adapter.

## Shared operation contract

- The application service is the only owner of validation, provider selection, plans, confirmation, execution, and operation results.
- CLI, X11, and Web are clients/adapters. They must not keep duplicate business logic, edit managed files directly, or accept arbitrary shell commands as a management operation.
- Every resource and operation names its provider (`native_termux`, `proot_debian`, or `shared`). Provider identity, paths, package manager, capability, and evidence remain explicit.
- Read operations report observed state and its source. Mutations return a preview/plan, require explicit confirmation, record progress/results, and support recovery where the operation can be interrupted.
- The Web UI talks only to the versioned loopback API. It never receives a generic shell, arbitrary path-write, ADB-forwarding, or raw environment operation.
- X11 and Android browser clients should use the same Web UI where that works well; the X11 shell remains usable if a browser or HTTP service is unavailable.
- APIs and graphical services start on demand. No always-on listener or GUI boot profile is implied.

## Current state from source and device evidence

- `lib/management_service.py` is a typed local application-service with a narrow operation allowlist. Many P3 operations use it, but the CLI/API coverage is incomplete.
- `lib/management_authorization.py`, `lib/management_sessions.py`, the HTTP adapter/server, and the foreground runtime provide default-deny scopes, one-use session bootstrap, loopback/origin guards, bounded requests, and graceful drain.
- The HTTP runtime starts explicitly in the foreground and requires a TTY-delivered bootstrap secret. Ordinary sessions are read-only; authenticated Web mode grants durable, CSRF-protected mutations for reviewed desktop, SSH/key, graphics, named-app, shortcut, Cron, PRoot session, and replay-guest actions. PRoot dead-session reconciliation now has a preview-confirm flow that updates only an exactly verified exited session record and sends no signal. Broad boot, backup/restore, scheduler, timezone, and recovery-write parity remain open. Browser bootstrap without terminal secret delivery and a general X11 management client also remain unimplemented.
- PRoot GUI apps have been verified as X11 clients on native `:1`; the first PRoot shortcut/app slice now has typed operations in `lib/management_service.py`. CLI shortcuts, desktop-entry launches, and the X11 shortcut manager route through those operations. The list reports Debian as the launch provider and native Termux as the shortcut-storage owner; unknown availability is not promoted to installed.
- `tx tui` now has a guided named-app launch path: the user selects the existing PRoot app ID and explicit `ternuxx`/`ternux` X11 session, confirms, and dispatches through `proot.app.launch`. A Ternux session requires an explicit display. This adapter does not manage the existing desktop or rootfs; source/test evidence is in [the guided launch record](../evidence/2026-10-19-tui-guided-proot-launch.md).
- Shortcut add/remove uses a state-bound preview and explicit confirmation. It preserves unowned, edited, symlinked, or out-of-home entries. Existing exact legacy entries can be safely adopted; ambiguous entries remain conflicts. Removing a launcher never stops its running app.
- The owner confirmed a PRoot Thunar window opened. That confirms app-level display sharing, not a second PRoot desktop or provider unification.

## Serial implementation order

### M1 — Shared operation/resource registry

**First registry contract implemented:** `management.catalog` now inventories SSH/Runit, native and PRoot runtime, Doctor, autoboot/background, recovery, add-on/tool and API-backend domains with maturity and provider labels. `doctor.report` joins the same read-only service. PRoot shortcut operations remain the first complete app-management slice. Later operations are explicitly marked planned rather than represented as available.

The product scope also includes PRoot guest lifecycle: adapt/verify the already-installed Debian first; then add preview-first selective distro install/removal (Ubuntu and other supported images) and selectable desktop environments (XFCE4 and alternatives). These lifecycle adapters are not implemented yet. They must preserve the existing guest by default and require explicit distro/desktop choice, plan, confirmation, and recovery. Add-on/plugin and cloud API backends are catalogued as planned; cloud calls stay disabled and secrets are never stored in the catalog.

### M2 — Finish the first shared GUI-app slice

**Source complete; device GUI confirmation pending.** PRoot app launch, shortcut inventory, preview, and apply are provider-aware service operations. CLI, generated desktop entries, and the X11 manager use them. Guest launch, menu registration, and native desktop lifecycle remain separately typed. The previous configured guest account is resolved from Ternux private state at runtime. Fixture tests cover exact confirmation, stale plans, legacy adoption, unowned/symlink preservation, and the rule that removing a launcher does not stop apps. No shortcut was changed during this repository work; the live list reports customized conflicts and preserves them.

### M3 — Non-CLI Web/X11 read-only client

**Status: partial.** The tx web command starts the authenticated loopback server, opens the Android browser, and provides catalog/status views plus reviewed preview-confirmed actions after a one-time terminal-delivered secret. The TUI also provides shared-service views and an allowlisted operation runner, but browser onboarding, X11 Applications-menu entry, general graphical management, and broad client parity remain open.

Serve a small accessible Web client from the same-origin loopback server. Show native and PRoot status with provider labels, evidence age/source, and clear unsupported/unavailable states. Add an X11 Applications-menu entry that starts the on-demand client safely. Design a user-visible bootstrap flow that does not require terminal copy/paste and does not weaken same-origin/session protections. Grant mutation scopes only to reviewed shared-service operations with exact previews, CSRF, idempotency, and client-side confirmation.

### M4 — Confirmed configuration operations

Expose one provider-scoped configuration area at a time (first GUI-app shortcuts, then shell profile/config, then boot and service controls) through plan/confirm/apply/status/recovery service operations. Enable only the exact API mutation scopes that pass security review and device tests. Make each operation usable from CLI, Web, and X11 before starting another area.

### M5 — Unified onboarding and workload catalog

Provide guided setup, optional provider selection, dependency previews, application catalog, progress, and rollback through the same services. Validate user comprehension and operation parity across CLI, Android browser, and native X11. Preserve CLI-only use and off-by-default GUI/boot behavior.

## Current disposition

The M1 domain registry and Doctor service entry are implemented; M1 is not complete because several domain adapters and PRoot lifecycle operations remain. The first app slice and M2 source/fixture gates pass. Web mode grants narrow, durable and CSRF-protected mutations for selected desktop, graphics, SSH/key, named-app, shortcut, Cron, PRoot-session and replay-guest actions; the ordinary API stays read-only. Web PRoot recovery reconciliation shares the typed service and changes only an exactly verified exited session record without signaling a process. TUI and GTK use the same service with typed actions and confirmations. Physical X11 manager interaction, complete browser onboarding, broad resource parity and the remaining recovery writes stay open. P4 remains active; do not infer phase completion from this source slice.

## Completion gates

- A shared-operation contract test proves CLI and API adapters produce the same plan/result for identical typed requests.
- A GUI and browser user can complete the same setup/configuration task without entering commands; explicit confirmation is understandable and provider-labelled.
- Negative tests prove unknown operations, wrong providers, missing capabilities, stale plans, unsafe paths, and cross-origin requests are denied.
- Device evidence records native and PRoot state separately and verifies that removing a launcher or changing a setting does not stop unrelated sessions.
- Documentation, phase state, and generated status identify completed slices and remaining gaps; no milestone is complete based only on source or fixture tests.
