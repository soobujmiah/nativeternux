# Native core optional PRoot failure injection — 2026-10-22

Phase: `P4`
Gate: PARTIAL — source/fixture evidence only

## Change

Extended `tests/test_doctor_report.py::DoctorReportTest.test_finding_ids_and_json_contract_are_stable` to run the complete read-only Doctor report after the optional PRoot inventory adapter raises `FileNotFoundError`, representing an unavailable `proot-distro` executable. The report still returns `read_only=true` and `overall=pass`; `NTX-PROOT-001` remains informational and says provider inventory is unknown. No guest/rootfs probe or process action is performed by the injected case.

This supplements the existing test that verifies catalog construction does not probe PRoot and the existing focused missing-manager Doctor finding test. It does not prove physical-device operation with PRoot absent, and it does not cover every Native boot, SSH, CLI, management, or workload call path. That broader independence gate remains open.

## Verification

- `python3 -m unittest tests.test_doctor_report -v`: **29/29 passed**.
- `bash scripts/repo_test.sh`: **849 tests passed, 1 skipped**, exit 0, 102.892 seconds.
- `git diff --check`: passed.
- Execution was in Native Termux over port 8022. No SSH lifecycle, desktop, PRoot process, or rootfs was changed by this test run.

## Evidence

- [P4 phase audit](2026-10-22-p0-p4-phase-audit.md).
- [P4 next-gate reconciliation](2026-10-22-p4-next-gate-reconciliation.md).
- Source: `tests/test_doctor_report.py`.
