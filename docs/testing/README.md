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

The opt-in checker runs installed Debian Firefox ESR with an isolated Native shared-tmp profile. It starts an ephemeral loopback Web runtime/private test state and permits only catalog/session-inventory reads. It does not start/attach/stop a guest session.

```sh
python3 tools/check_web_ui.py
python3 tools/check_web_ui.py --visible
```

Run from the repository root in Native Termux. Visible mode uses the existing X11 display without starting a desktop/Android Activity. Optional `--screenshots "$PREFIX/tmp/ternuxx-web-ui-review"` saves scoped captures; delete them after inspection.

Headless checks require exact 390/752/1440 CSS-pixel viewports. The disposable browser's minimum width is adjusted through loopback Marionette control. Visible mode reports actual content size, which can differ from window size. Checks cover login/hidden state, navigation/search, overflow, action stability, the 8022 control boundary, and the vendored terminal renderer/dialog. No guest start/attach request is sent.

See [Mozilla's protocol](https://firefox-source-docs.mozilla.org/remote/marionette/Protocol.html). Firefox/PRoot are optional checker dependencies, not Native core dependencies.

## Private Native monitor replay

With Native Runit tools already installed, run `python3 tools/check_monitor_service.py --interval-check`. It starts its own Runit watcher with one fixed service under a private temporary root and separate monitoring state. It verifies fresh registration, idle policy, two Linux-only ticks 30 seconds apart, unchanged workstation policy, and exact test-service exit/removal. It does not stop existing services, change workstation monitoring flags, or start a guest. This replay is opt-in and is not part of ordinary unit tests.

See [registration and evidence](../evidence/2026-10-22-monitor-service-registration.md). Android Activity/focus behavior and cold-boot delivery require separate qualification.

## Evidence and qualification

[Current limits](KNOWN-LIMITATIONS.md), [device compatibility](DEVICE-COMPATIBILITY.md), [client coverage](../architecture/CAPABILITY-MATRIX.md), and [the active audit](../audit/REPOSITORY-AUDIT.md) track remaining gates.

- [CPU](CPU-BASELINE.md), [GPU](GPU-ACCELERATION.md), and [NPU](NPU-ACCELERATION.md) distinguish backend access from workload correctness.
- [Benchmark methodology](BENCHMARK-METHODOLOGY.md) and [report template](reports/REPORT-TEMPLATE.md) define reproducible measurements.
- [P3 RB08 evidence](../evidence/2026-10-22-p3-rb08-postboot-exit-audit.md) records the dated accepted boot path and checkpoint limit.
- [8023 procedures](8023-deployment-and-lifecycle.md) describe preview-first deployment/recovery.
- [Feature/offer matrix](FEATURE-MATRIX.yaml) is a dated classification snapshot requiring individual claim review before use as current coverage.

PASS applies to named criteria/context; PARTIAL means only some stages pass; FAIL requires an executed failure; BLOCKED identifies a prerequisite; UNKNOWN means insufficient evidence. Detection, initialization, workload verification, and release qualification are distinct. Record exact runtime/artifact identity, backend selection, correctness, observed measurements, and limits. Synthetic CI is not physical-device evidence.

CPU/fallback, supported acceleration, diagnostics, reproduction commands, compatibility reports and evidence access remain free-core targets. The public repository has no owner-approved redistribution license/installable release; [readiness](../readiness/README.md) tracks these gates.
