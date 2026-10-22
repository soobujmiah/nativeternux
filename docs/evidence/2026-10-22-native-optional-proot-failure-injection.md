# Native core optional PRoot failure injection - 2026-10-22

Phase: `P4`
Gate: PARTIAL - unit/fixture plus bounded live Native failure injection

## Coverage

The source/fixture coverage already proved that:

- Catalog construction does not probe PRoot or list its sessions.
- Doctor continues when the optional PRoot inventory adapter raises `FileNotFoundError`; the unavailable provider is informational and inventory stays unknown.
- PRoot-receipt validation rejects missing or replaced rootfs identities before any guest probe.

This follow-up adds a bounded live Native Termux check. It prepends a private temporary `proot-distro` executable to `PATH`; that executable records that it ran, reports an injected failure, and exits 127. The check then invokes only read-only Native CLI/management commands. It does not hide or uninstall the real package, start a guest, mutate a rootfs, or signal a process.

## Live results

From the Native checkout over SSH 8022:

```sh
python3 tools/check_native_proot_independence.py
```

The shim was invoked and the command returned 0. All seven probes were accepted:

| Probe | Result |
|---|---|
| `./tx --help` | exit 0 |
| `./tx mng catalog list --json` | exit 0; `ok=true` |
| `./tx mng boot helpers status --json` | exit 0; `ok=true` |
| `./tx graphics native status --json` | exit 0; `ok=true` |
| `./tx ssh inspect --json` | exit 0; `ok=true` |
| `./tx recovery status --json` | exit 0; `ok=true` |
| `./tx doctor --json` | valid read-only report; PRoot finding remained `info` / inventory unknown |

Doctor exited 1 and reported `overall=warning` because the current Native report also contains a separate existing host warning. This is recorded as a warning-bearing report, not a clean Doctor pass. The injected PRoot failure itself was informational and did not prevent the other six Native operations.

## Regression and environment checks

- `python3 -m unittest tests.test_management_catalog tests.test_doctor_report -q`: **37/37 passed**.
- `umask 022 && python3 -m unittest tests.test_proot_diagnostics -q`: **26/26 passed**. This reproduces GitHub's permissive default umask and verifies the receipt fixture now creates its private state directories explicitly.
- `python3 tools/check_native_proot_independence.py`: exit 0; shim invocation verified; no guest mutation command invoked.
- `bash scripts/repo_test.sh`: **853 passed, 1 skipped**, 126.379 seconds; suite output ended `OK`.

## Limits

This does **not** simulate an actually absent `proot-distro` executable at runtime, a missing/broken guest rootfs, or PRoot processes being absent. Unit tests cover the missing-manager exception path. This does not prove cold boot, desktop startup, SSH authentication, or a native workload draw while PRoot is absent. Those P4 independence checks remain open.

## Evidence

- [P4 phase audit](2026-10-22-p0-p4-phase-audit.md).
- [P4 next-gate reconciliation](2026-10-22-p4-next-gate-reconciliation.md).
- Source/runner: `tools/check_native_proot_independence.py`.
- Fixture regression: `tests/test_proot_diagnostics.py`.

The first GitHub Repository State Contract run for the preceding commit failed the same receipt-fixture test under its default umask. Explicit private directory modes fixed that portability defect. A new GitHub run after pushing this change is still pending.
