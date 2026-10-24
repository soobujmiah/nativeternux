# P6 client capability and consistency audit — 2026-10-24

Phase: `P6`
**Evidence class:** repository source review, contract tests, and direct Native Termux smoke.
**Scope:** CPU inference and graphics claims/actions across CLI, TUI, authenticated Web, GTK, and the shared management service.

## Evidence

The shared catalog called CPU's desired state `local-offline-cpu` although network-isolated execution had not been verified. The Web called the third-party KGSL tree “verified” without saying it was experimental, already-extracted device-local input. Its CPU control block also existed twice, producing duplicate status/install/remove/run buttons. Finally, public `tx ai` called `cpu_inference.py` directly while TUI, Web, and GTK called the shared management service.

The catalog now uses `bounded-local-cpu` and explicitly leaves offline execution unverified. It describes the KGSL option as experimental, local files only, and not installed by Ternuxx. TUI, Web, GTK, and CLI selection guidance says the choice affects future desktop starts and does not change the running desktop. The duplicate Web action block was removed. All public `tx ai` status, model preview/apply, and run commands now submit the same `inference.cpu.*` operations through `management_service.py`; prompts travel through stdin, and model apply requires the exact action-matched confirmation plus a current plan ID.

## Verification

- Focused catalog, TUI, Web, GTK, and management-service contract tests passed.
- The Web's embedded JavaScript passed `node --check`; the GTK client passed `clang -fsyntax-only -Wall -Wextra ...` with Termux GTK4 flags; `lib/ai.sh` passed `bash -n`.
- Live `tx ai status` and `tx ai model preview` returned the shared service operations. A live bounded `tx ai run --max-tokens 32`, with its prompt provided on stdin, returned exactly `NATIVE_CPU_OK` with backend `CPU`.
- The complete Native Termux repository suite passed **690 tests in 110.990 seconds**.
- No live UI click or desktop restart was part of this source-copy audit. Visible owner acceptance remains separate.

## Remaining limits

This evidence does not qualify network-isolated/offline execution, GPU inference, NPU execution, general application graphics, or the experimental KGSL candidate for release. P6 remains active while its supported workload boundary is reviewed.
