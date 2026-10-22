# Testing and qualification

Run implementation checks from Native Termux over SSH 8022. Preserve Native Termux and the active Codex PRoot session. Source/fixtures, actual device observations, and owner reports are different evidence classes.

## Repository checks

From the checkout:

```sh
bash scripts/repo_test.sh
bash tests/test_cli_help.sh
python3 -m tools.repo_knowledge verify
git diff --check
```

The unit/fixture suite covers lifecycle identity/refusal, previews, journals/recovery, services, authorization, Web sessions, broker, and clients. CI records the actual result in [generated status](../../.repo/STATUS.md). Failed imports are failures. These checks do not qualify a real guest, reboot, accelerator, or fresh install.

## Real Firefox checks

The opt-in checker runs installed Firefox ESR only from a named `ternuxx-replay-*` disposable alias; it refuses the protected default `debian` workload. It starts an ephemeral loopback Web runtime/private test state and permits only catalog/session-inventory reads. The browser login can trigger PRoot-Distro's Termux profile injection in the selected replay guest, so the checker reports that possibility and must never be pointed at the owner's working guest. It does not start/attach/stop a Ternuxx-managed guest terminal session.

```sh
python3 tools/check_web_ui.py --distro ternuxx-replay-p4
python3 tools/check_web_ui.py --distro ternuxx-replay-p4 --visible
```

Run from the repository root in Native Termux. Visible mode uses the existing X11 display without starting a desktop/Android Activity. Optional `--screenshots "$PREFIX/tmp/ternuxx-web-ui-review"` saves scoped captures; delete them after inspection.

Headless checks require exact 390/752/1440 CSS-pixel viewports. The disposable browser's minimum width is adjusted through loopback Marionette control. Visible mode reports actual content size, which can differ from window size. Checks cover login/hidden state, navigation/search, overflow, action stability, the 8022 control boundary, and the vendored terminal renderer/dialog. No guest start/attach request is sent.

See [Mozilla's protocol](https://firefox-source-docs.mozilla.org/remote/marionette/Protocol.html). Firefox/PRoot are optional checker dependencies, not Native core dependencies.

## Private Native monitor replay

With Native Runit tools already installed, run `python3 tools/check_monitor_service.py --interval-check`. It starts its own Runit watcher with one fixed service under a private temporary root and separate monitoring state. It verifies fresh registration, idle policy, two Linux-only ticks 30 seconds apart, unchanged workstation policy, and exact test-service exit/removal. It does not stop existing services, change workstation monitoring flags, or start a guest. This replay is opt-in and is not part of ordinary unit tests.

See [registration and evidence](../evidence/2026-10-22-monitor-service-registration.md). Android Activity/focus behavior and cold-boot delivery require separate qualification.

## Separate guest terminal replay

The [separate guest setup and broker/CLI replay](../evidence/2026-10-22-fresh-setup-and-probe-safety.md) completed with scoped preservation checks. Follow [the isolated broker procedure](../architecture/INTERACTIVE-PROOT-TERMINALS.md#separate-guest-qualification) after fresh setup succeeds. In a second Native terminal, use that same private state namespace with `./tx terminal start`; review the selected replay alias/rootfs before confirming. Exercise I/O and terminal resizing, use Ctrl+] to detach, then `./tx terminal attach SESSION_ID` and `./tx terminal close SESSION_ID` with the same namespace. Close must show the exact session and profile-specific signal/scope before confirmation.

This is an opt-in device replay, not part of the ordinary unit suite. Terminal content stays out of evidence/logs. Preserve failed state for diagnosis; never force-signal or adopt the working guest. Actual CLI, broker, TUI and Web lifecycles passed on the separate guest; GTK/VTE and remaining cross-client acceptance stay open.

Replay guest retirement is limited to receipt-verified ternuxx-replay-* aliases; the protected Debian guest is rejected. Preview and apply move the whole container directory atomically into private same-filesystem state. Restore has its own exact preview/apply pair and returns the same directory. No guest files are deleted. The shared-service flow passed a live Native CLI preview and an earlier CLI retire/restore cycle on ternuxx-replay-p4. Web/TUI/GTK controls use the same operations; authenticated Web and GTK dialog interaction remain unverified. See the [retirement evidence](../evidence/2026-10-22-replay-guest-retirement.md).

A sequential cross-client handoff uses the same receipt-verified replay guest and private broker:

```sh
"$HOME/.cache/ternuxx-ui-check-venv/bin/python" tools/check_terminal_handoff.py --alias ternuxx-replay-p4
```

It verifies real CLI start/I-O/resize/detach, authenticated Web API attach/I-O/resize/detach, then TUI attach/I-O/resize/detach on the same session; it checks shared inventory and GTK picker visibility, closes that exact test session by preview/apply, and verifies the default Debian root identity/profile. It does not qualify a GTK/VTE attach or a browser-rendered terminal window. A failed run preserves its private state for exact recovery; never target the default Debian alias. See [cross-client evidence](../evidence/2026-10-22-cross-client-terminal-handoff.md).

The opt-in real TUI replay uses the same separately owned guest. From Native Termux, install the pinned checker-only dependencies into a private Python environment and run:

```sh
python3 -m venv "$HOME/.cache/ternuxx-ui-check-venv"
"$HOME/.cache/ternuxx-ui-check-venv/bin/python3" -m pip install -r tools/requirements-tui-replay.txt
"$HOME/.cache/ternuxx-ui-check-venv/bin/python3" tools/check_tui_terminal.py --alias ternuxx-replay-p4
```

The checker requires the completed fresh-setup receipt and exact rootfs identity, uses a private broker/state, and removes them after a passing run. On failure it retains private state and prints exact PIDs for ownership-checked recovery. [Native TUI result](../evidence/2026-10-22-tui-terminal-replay.md). This optional dependency is not needed by the product.

The opt-in authenticated Web terminal replay uses Firefox ESR from the completed separate guest and a private Native Web server/broker:

```sh
python3 tools/check_web_terminal.py --alias ternuxx-replay-p4
```

It drives the real Web page with browser key actions, checks guest I/O and viewport resize, then detaches, reattaches and closes the exact owned session. The working Debian root/profile checks and private-state cleanup follow the same separate-target rule. An optional `--screenshot "$PREFIX/tmp/ternuxx-web-terminal-review.png"` saves one temporary image for visual inspection. See [Web terminal evidence](../evidence/2026-10-22-web-terminal-replay.md). This does not qualify GTK or cross-client handoff.

Guest graphics status and browser availability detection do not enter the guest. Explicit verification can invoke PRoot-Distro's generated-profile writer; HTTP requires `graphics.manage` and CSRF, and read-only API access rejects it. See [the current API contract](../architecture/MANAGEMENT-API.md) and [probe metadata/authorization checks](../evidence/2026-10-22-probe-http-live.json). Full exact probe plans/rollback remain under audit.

## Evidence and qualification

[Current limits](KNOWN-LIMITATIONS.md), [device compatibility](DEVICE-COMPATIBILITY.md), [client coverage](../architecture/CAPABILITY-MATRIX.md), and [the active audit](../audit/REPOSITORY-AUDIT.md) track remaining gates.

- [CPU](CPU-BASELINE.md), [GPU](GPU-ACCELERATION.md), and [NPU](NPU-ACCELERATION.md) distinguish backend access from workload correctness.
- [Benchmark methodology](BENCHMARK-METHODOLOGY.md) and [report template](reports/REPORT-TEMPLATE.md) define reproducible measurements.
- [P3 RB08 evidence](../evidence/2026-10-22-p3-rb08-postboot-exit-audit.md) records the dated accepted boot path and checkpoint limit.
- [8023 procedures](8023-deployment-and-lifecycle.md) describe preview-first deployment/recovery.
- [Feature/offer matrix](FEATURE-MATRIX.yaml) is a dated classification snapshot requiring individual claim review before use as current coverage.

PASS applies to named criteria/context; PARTIAL means only some stages pass; FAIL requires an executed failure; BLOCKED identifies a prerequisite; UNKNOWN means insufficient evidence. Detection, initialization, workload verification, and release qualification are distinct. Record exact runtime/artifact identity, backend selection, correctness, observed measurements, and limits. Synthetic CI is not physical-device evidence.

CPU/fallback, supported acceleration, diagnostics, reproduction commands, compatibility reports and evidence access remain free-core targets. The public repository has no owner-approved redistribution license/installable release; [readiness](../readiness/README.md) tracks these gates.
