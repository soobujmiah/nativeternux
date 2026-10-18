# ADR-0004: Three interfaces share one management layer

- **Date:** 2026-10-17
- **Status:** accepted by owner on 2026-10-18; implementation is incremental
- **Type:** application-architecture

## Context

Ternuxx must serve CLI users and people who prefer graphical workflows. The owner confirmed that CLI, local Web UI, and X11 GUI should perform the same management tasks through shared state and services, so users do not need to know CLI commands for routine setup or configuration. Native Termux and the existing Debian PRoot remain separate providers with distinct homes, permissions, package managers, and ownership. The user experience and Ternuxx-managed configuration should be unified without pretending the underlying environments are one filesystem or security boundary.

## Proposed decision

Create one shared management layer as the authority for configuration, capability state, permission checks, plans/confirmations, operation/task lifecycle, providers, diagnostics and recovery.

- CLI uses the application services directly and remains usable with all graphical services stopped.
- Web Visualizer is a thin client of a versioned local management API. Start the API on demand, loopback-only, when needed; do not require a permanent daemon for CLI use.
- X11 Desktop GUI is another thin client of the same application services/API. It does not own system state and must report when X11 is unavailable.
- Automation uses named application-service operations, never a separate unrestricted shell path.
- All interfaces use the same schemas, capability registry, authorization rules, operation IDs and evidence records.

The CLI management service, versioned local API, loopback HTTP server, authorization/session primitives, and a read-only foreground runtime now exist. A Web UI and general X11 management client do not yet exist; the recent PRoot shortcut manager is a task-specific X11 dialog and is not the shared interface layer. HTTP mutation dispatch remains disabled. See [shared management implementation plan](../SHARED-MANAGEMENT-PLAN.md) for the staged completion sequence and current gaps.

## Alternatives considered

- **Separate CLI/Web/GUI logic:** rejected; behavior and permission checks would drift.
- **Always-on background management daemon:** defer; Android background limits and continuous memory cost are not justified before an on-demand API is measured.
- **Web-only product:** insufficient for the explicit X11 Desktop GUI product target; reusing the Web UI in a supported X11 browser remains a candidate, subject to dependency/resource evidence and owner decision.
- **GUI directly edits config and launches shell commands:** rejected; this bypasses shared validation and authorization.

## Consequences

- CLI operations use the shared service contract; operation coverage is still incomplete and must expand without bypassing typed validation.
- API and GUI work depends on stable schemas and security review.
- UI changes cannot bypass operation preview, confirmation, provider ownership, or recovery state.
- A backend outage must not disable the CLI; graphical clients show unavailable state and recovery guidance.
- A cross-interface contract test must prove the same request produces the same validated plan/result through CLI and API adapters.

## Acceptance criteria for implementation

- Define service/resource schemas, error codes, operation states and versioning.
- Define which commands remain direct read-only CLI paths and which mutations require plan/confirm.
- Threat-review localhost browser access, session bootstrap, CSRF, origin/host validation and cancellation behavior.
- Measure candidate API/UI dependencies against the approved download, installed-size, RAM and startup budgets.
- The same shared service operation is callable through CLI and authenticated local API, with matching plan, result, provider, and evidence semantics.
- The Web UI works in an Android browser and the X11 desktop without separate business rules or direct filesystem/shell access.
- Routine setup and configuration can be completed without CLI knowledge, using clear preview, confirmation, progress, and recovery flows.
- Native Termux and PRoot resources are presented together but remain explicitly provider-scoped; actions cannot silently cross provider boundaries.
- Browser bootstrap and API mutation remain disabled until their end-to-end security and device acceptance gates pass.

## Evidence

- [Master Phase 0 audit](../../evidence/PHASE-0-MASTER-AUDIT.md)
- [Unified workstation proposal](../UNIFIED-WORKSTATION.md)
- [Management API proposal](../MANAGEMENT-API.md)
- Current source: `bin/nativeternux`, `lib/desktop.sh`, `lib/phases.sh`; no API/UI implementation exists.
