# Ternuxx architecture

Ternuxx has a self-sufficient Native Termux control layer and an optional Debian PRoot workload provider. [Vision](PRODUCT-VISION.md) defines the intended workstation; [phase state](../project/phase-state.json) owns acceptance and [client coverage](architecture/CAPABILITY-MATRIX.md) owns current interface limits. Dated runtime measurements belong in evidence.

## Native core and clients

Desktop lifecycle uses the Native supervisor and shared identity/recovery modules. Boot, SSH, continuity, CLI, management, state, and native workloads must remain usable without PRoot.

Management dispatches through `lib/management_service.py`, shared authorization/session policy, and the catalog. TUI calls the local service; Web uses the loopback HTTP adapter; GTK uses the typed desktop bridge. Some direct CLI paths use specialized modules, so API registration is not proof of equal client coverage.

Web uses a one-time bootstrap code, scoped capabilities, exact Host/Origin checks, CSRF, and durable idempotency for permitted writes. Fixed bounded Ternuxx log sources are exposed; arbitrary paths and Android-wide logs are not. The Web action area scrolls independently from details; quick controls invoke real selected-resource actions. All clients consume catalog category order.

## Source and installed deployment

The source command is `./tx`; the installed `tx` shim dispatches to the checkout. New Web/TUI processes load current source; a running Python process may still hold old imports.

GTK is separately compiled with source/bridge/binary identities. Runit/Termux:Boot helpers and canonical recovery modules under `$PREFIX/lib/ternuxx` are separate deployment targets. Each needs exact source/installed comparison and deployment verification. Clean Git state alone does not prove live parity.

## Optional PRoot provider

Typed `proot-distro` operations resolve the target account/rootfs and pass bounded argv/environment. Lifecycle operations require verified process identity. Unknown processes, including the working Codex guest, are not adopted or stopped.

PRoot is a compatibility environment under the Android/Termux UID, not a VM or security sandbox. Existing mounts and same-UID host access must be accounted for. A selected workspace is an application access contract, not proof that the guest filesystem is confined to it. Native Bionic and Debian glibc libraries remain separate.

Route implementations include standalone Debian GUI `:0`, selected apps on Native `:1`, and nested Xephyr `:2`; readiness/audio/graphics evidence is separate per route. See [sessions](architecture/PROOT-SESSIONS.md), [Hybrid integration](HYBRID-INTEGRATION.md), and [display/audio](architecture/NATIVE-GRAPHICS-AUDIO.md).

## Interactive terminal broker

The optional Native broker owns fixed-profile PTYs through a private same-UID Unix socket. Attachments are generation-bound with one writer, bounded I/O, short-lived Web tickets, and fresh start/close plans. CLI, TUI, Web/xterm.js, and GTK/VTE lifecycles and one sequential cross-client handoff have passed on a disposable replay guest. Exact replay-guest retirement and restoration passed through CLI, authenticated Web API, and installed GTK; visible Firefox Web acceptance now passes for the authenticated catalog, search, status controls, terminal rendering, action layout and responsive viewports; full mutation/client parity and broader provider/configuration and reproducibility acceptance remain open. See [visible Web acceptance](evidence/2026-10-22-web-ui-visible-acceptance.json). See [interactive terminals](architecture/INTERACTIVE-PROOT-TERMINALS.md).

## Host integrations and recovery

Termux:X11, PulseAudio, Termux:API, Termux:Boot, and Runit have explicit ownership. X11 readiness and Android Activity visibility are separate. A guest app launched on an existing verified display does not implicitly request the Android Activity.

[P3 RB08 evidence](evidence/2026-10-22-p3-rb08-postboot-exit-audit.md) records the observed Native boot path. PRoot/Hybrid boot and the current recovery module copy's next boot remain separately unqualified. State and journals use Native private storage; changes require validated targets, bounded impact, serialization, and appropriate preview/confirmation/recovery. Targeted guest configuration preserves pre-state and rollback.

## Graphics, compute, and applications

Native and Debian backends are separate runtime contexts. The graphics manager distinguishes enumeration, context creation, bounded draws, and application qualification, and reports software rendering. A draw is not inference or NPU evidence. See [graphics qualification](testing/GPU-ACCELERATION.md) and [research](RESEARCH.md).

CPU is the baseline. Ternuxx has no integrated inference engine or NPU runtime. Wine/Hangover is an optional application-provider proposal requiring per-app architecture, graphics, input/audio, and recovery evidence; a Native Vulkan draw does not qualify Wine/DXVK. See [Wine](WINE-NATIVE.md), [software](SOFTWARE-CATALOG.md), and [optimization](OPTIMIZATION.md).

Full application lifecycle, clean-device reproduction, fresh-setup rollback, client parity, and release qualification remain roadmap work tracked in [the audit](audit/REPOSITORY-AUDIT.md).
