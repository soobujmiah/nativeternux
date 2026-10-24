# P6 capability and support-boundary review — 2026-10-24

Phase: `P6`
**Evidence class:** source/test review and direct Native Termux checks.
**Disposition:** P6 complete as a capability and support-boundary assessment. Unsupported GPU inference, NPU, and offline inference remain explicitly unavailable or unverified; this review does not qualify them for release.

Gate: PASS

## Acceptance criteria

- The selected Native CPU path has a named model, shared client route, bounded execution contract, and direct repeat evidence.
- Stock rendering, experimental rendering, and inference are reported as separate capabilities, with each direct workload limited to its observed result.
- Offline inference, GPU inference, and NPU execution are explicitly unqualified or unavailable where direct repeatable evidence is absent.
- CLI, TUI, Web, and GTK capability copy and actions use the reviewed shared CPU operation contract.
- The full repository fixture suite, generated-state check, and document inventory validate after the changes.

## Evidence

| Capability | Verified result | Product boundary |
|---|---|---|
| CPU inference | One pinned Qwen3 0.6B Q4_0 model runs through the shared CLI/TUI/Web/GTK path with explicit CPU-only bounds. A monitored 20-run marker test passed. | Partial support for the named model/device only. The short repeat is not a prolonged thermal, general quality, or broad-model qualification. |
| Stock graphics | The installed stock Mesa stack rendered OpenGL through llvmpipe. The stock GLES verifier was unavailable; Vulkan found no valid GPU and performed no draw. | Software-rendered OpenGL only for the tested stack; no stock GLES/Vulkan draw claim. |
| Experimental graphics | Fresh extraction from the locally retained checksum-verified Mesa package set passed bounded OpenGL, GLES, and Vulkan workloads on the Adreno 825. | Device-specific experiment only. No stable official distribution/clean-install route exists, so the candidate stays outside release support. |
| Network-independent inference | A fresh `unshare -n true` attempt returned `Operation not permitted`. Earlier process-scoped socket/egress filters did not produce a successful inference run. | Offline inference remains unverified; no offline claim is made. |
| GPU inference and NPU | No GPU inference runtime/workload or usable Native NPU inference path was verified. | Unavailable; no acceleration claim. |
| Client contract | CLI, TUI, Web, and GTK route bounded CPU actions through the shared management service; the duplicate Web controls were removed and capability text is aligned. | Fixture and source coverage does not establish complete visual/accessibility parity. |

Direct details are in the [CPU workflow evidence](2026-10-24-native-cpu-inference-workflow.md), [stock Mesa recheck](2026-10-24-native-stock-mesa-recheck.md), [experimental graphics recheck](2026-10-24-native-graphics-fallback-recheck.md), and [client capability-copy audit](2026-10-24-p6-client-capability-copy-audit.md).

The full Native Termux repository harness passed **690/690** in **110.249 seconds**. `python3 -m tools.repo_knowledge verify` reported **0 findings**; `git diff --check` passed. The document inventory was regenerated after the current-state edits and its local-link audit is part of that generated record. A live `tx status --json` check after verification still reported the Native supervisor, X11, XFCE, and audio owner as running; the Termux app and desktop were not closed or stopped.

P6 closes because the named CPU path and graphics fallbacks have direct bounded evidence, while unsupported and unreproducible paths are explicitly excluded from support. The unresolved graphics distribution path, longer stability, offline behavior, GPU inference, and NPU remain limits for release/hardening review; they are not represented as implemented features. P7 is next: audit the existing Native software catalog and build only the install/update/remove lifecycle and client actions that can be safely previewed and verified.
