# Current implementation and qualification limits

This file records current Native Termux limits. The full phase ledger is in [phase state](../../project/phase-state.json); client reach is in the [capability matrix](../architecture/CAPABILITY-MATRIX.md); detailed audit findings are in the [current repository audit](../audit/REPOSITORY-AUDIT.md). Older guest and multi-provider reports are historical.

## Native profile and runtime

- Direct evidence covers one Android 16/API 36, aarch64, Termux 0.119.0-beta.3 device. It does not establish support for other phones, Android versions, or Termux builds.
- The current Native desktop reports `:1`, live supervisor/X11/XFCE, and Native audio owner. Android window visibility is still `unknown`; no cold-boot delivery is claimed from the current live check.
- A read-only post-qualification check found both PRoot packages and executables absent and an empty PRoot-Distro containers directory. Ternuxx has no supported guest workflow.
- The complete Native Termux fixture suite passed 719 tests in 93.753 seconds on 2026-10-24. The suite does not prove Android boot delivery, clean installation, visible GUI acceptance, or physical audio output. Doctor reports runtime availability and model state, but its read-only status does not verify the model hash; inference verifies the hash before execution. Fixture coverage does not prove Android boot delivery, clean installation, visible GUI acceptance, physical audio behavior, or complete live client parity.

## CPU, graphics, and inference

- CPU inference is `PARTIAL`: one pinned Qwen3 0.6B Q4_0 model runs locally through CLI, TUI, Web, and GTK, with size/hash verification and bounded CPU settings. The Termux runtime package remains Termux-managed and is not installed or updated by Ternuxx. The tested package came from the configured Dan Yael mirror listed in the [Termux mirror inventory](https://github.com/termux/termux-packages/wiki/Mirrors); see [third-party notices](../readiness/THIRD-PARTY-NOTICES.md) for exact source and license notes.
- A twenty-run Native smoke returned the deterministic expected marker each time over 63.3 seconds, with about 537 MiB peak child RSS and coarse CPU/SoC thermal reads. This does not establish a prolonged thermal soak, throttling behavior, general model quality, or broad model support. Network-isolated inference has not been verified; Android denied a network-namespace attempt.
- The current installed stock Mesa stack rendered OpenGL through llvmpipe; its GLES verifier was unavailable and Vulkan detected no valid GPU. A separate experimental graphics candidate passed bounded GL/GLES/Vulkan checks on this device, but it has no reproducible clean-install distribution and is not release-qualified. The [stock Mesa recheck](../evidence/2026-10-24-native-stock-mesa-recheck.md) separates these results from candidate runs. Do not infer application-wide GPU or inference acceleration from those tests.
- No GPU inference runtime or workload is implemented. No accessible Native NPU inference path or correct NPU workload is verified. Report these capabilities as unavailable.

## Client, recovery, and release

- CLI, TUI, Web, and GTK use shared management operations and authorization for covered actions. Broader action parity, accessible interaction review, and complete visible acceptance remain open; a catalog entry alone does not prove a client action.
- The latest managed-SSH and Doctor findings are device-specific. The current audit records a wildcard/password-authentication warning on a Native SSH configuration; listener ownership and external reachability remain unknown. Check `tx ssh status --json` before exposing remote access.
- RB08 is the latest recorded owner-operated reboot qualification, but its automated checkpoint remains `NOT_READY`. The current session status does not establish Termux:Boot delivery after another reboot; do not reboot solely for an agent test.
- The repository has no selected project license. Source provenance, a build-specific SBOM, release signing, and release approval remain open. Public source visibility is not permission to redistribute it.

Use `UNKNOWN` when evidence is missing, `BLOCKED` for a concrete prerequisite, and `FAIL` only for an executed failed criterion. Record observed workload and viewport values instead of assuming that requested settings were achieved.
