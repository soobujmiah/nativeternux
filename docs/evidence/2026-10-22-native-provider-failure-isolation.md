# Native PRoot provider-failure isolation - 2026-10-22

Phase: `P4`
Gate: PARTIAL - missing distribution and refused guest login were injected on Native; real guest/rootfs absence was not altered.

## Method

`tools/check_native_proot_independence.py` now runs the same seven read-only Native core probes under three private `PATH` injections: the `proot-distro` command exits 127; the manager reports no installed Debian guest; and the manager reports Debian but refuses `login` with exit 127. Each guest scenario also places a `proot` tripwire first on `PATH`. The injected manager records only operation names. The guest is never launched and no rootfs, package, service, credential, or process is changed.

## Native results

All seven core probes passed in all three scenarios: `tx --help`, management catalog, boot-helper status, Native graphics status, SSH diagnostics, recovery status, and Doctor. Doctor remained read-only, kept the PRoot finding informational, and exited 1 because an unrelated existing host warning remains; this is not a clean Doctor pass.

- Missing inventory: `tx proot verify --distro debian ...` returned `status=not_installed`, `guest_entered=false`; the injected manager trace contains only inventory reads, no `login` call.
- Broken login: the manager returned Debian in its synthetic list, then refused the `login` request. Verification returned `status=unknown`, no guest-write command and no package change. The verifier reports `guest_entered=true` because it attempted the manager login; this shim proves that value does not prove a real guest process started. The `proot` tripwire was not reached.
- Manager command failure: the injected manager exited 127; all seven Native probes remained usable and Doctor reported unknown PRoot inventory as informational.

Exact command report: [live failure-injection JSON](2026-10-22-native-optional-proot-failure-injection-live.json).

## Regression and limits

- `python3 -m unittest tests.test_proot_diagnostics -q`: **28 passed**. New tests cover a missing installed distribution (no login) and failed login (unknown state and conservative launcher-profile-write disclosure).
- `python3 tools/check_native_proot_independence.py`: exit 0 across all three scenarios.
- `bash scripts/repo_test.sh`: **856 passed, 1 skipped**, 128.443 seconds.
- The existing Debian guest, replay guest, PRoot process table, and rootfs were not used as test targets. The check does not prove behavior when the actual `proot-distro` package is removed, a real rootfs directory/file is missing or malformed, all PRoot processes are absent, or during cold boot/native workload execution. Those remain separate qualification gaps.

## Evidence

- [P4 next-gate reconciliation](2026-10-22-p4-next-gate-reconciliation.md).
- [Earlier command-failure injection](2026-10-22-native-optional-proot-failure-injection.md).
- Source and tests: `tools/check_native_proot_independence.py`, `lib/proot_diagnostics.py`, `tests/test_proot_diagnostics.py`.
