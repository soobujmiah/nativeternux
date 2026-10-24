# Ternuxx architecture

Ternuxx is a Native Termux-only workstation manager for Android. Its public command is `tx`; the installed shim dispatches into `$HOME/ternuxx`. Product state lives under `$TERNUXX_STATE_DIR` or the default `$HOME/.local/share/ternuxx`, and installed runtime modules live under `$PREFIX/lib/ternuxx`.

Native Termux owns desktop lifecycle, boot/recovery, SSH, service supervision, state, diagnostics, and workloads. The Native desktop uses Termux:X11 and Native Termux packages. Ternuxx does not start or depend on Debian PRoot and does not invoke the separate Ternux project or launcher.

## Shared management

The local management service exposes a typed operation allowlist to the CLI, TUI, authenticated loopback Web UI, and GTK management center. Clients share validation, authorization, preview/confirmation, journals, and result reporting. Each client may support a subset of the Native operation catalog; unsupported actions are not shown as active controls.

The Web service binds to loopback, uses one-time bootstrap, scoped sessions, same-origin checks, CSRF, and durable idempotency for permitted writes. It has no generic shell or arbitrary file API. Native GTK is separately built and installed with source/bridge/binary identity checks.

## Native process ownership

Ternuxx controls only the Native services and processes it records. Desktop and service recovery requires exact process/config identity and refuses ambiguous ownership. Termux:X11 Android Activity visibility is reported separately from server readiness. SSH management applies only to the fixed Native Runit service; the separately owner-managed development port remains external to product lifecycle controls.

## Graphics and audio

Native graphics selection is stored in private Ternuxx state and applies to future Native desktop sessions. Diagnostics identify the observed renderer and workload; installed libraries or device nodes alone are not acceleration evidence. Native PulseAudio is managed as a Native service. No guest library paths or cross-userspace handoff exist.

## Scope migration

The 2026-10-24 owner decision made Ternuxx Native-only and superseded the prior PRoot/hybrid architecture. See [ADR-0017](architecture/decisions/ADR-0017-native-only-product-and-proot-retirement.md) and the [removal audit](evidence/2026-10-24-native-only-proot-removal-audit.md). Older PRoot evidence remains historical and must not be used as current Native qualification.
