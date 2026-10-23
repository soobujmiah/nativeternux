# Boot-profile catalog identity reconciliation — 2026-10-24

## Finding

The Native read-only `./tx boot profile status --json` result reported the configured `cli-only` profile and `managed_script_identity: match`. The current shared typed catalog nevertheless labeled this resource `source-managed-installed-script-mismatch` and `source-mismatch`. The boot entry is generated from the selected profile by `lib/boot_profiles.py`; it is not a single checked-in static boot-script source file. The catalog therefore contradicted both the implementation and the live status operation.

## Change

The catalog now describes the entry as a managed generated script whose identity is checked through `boot.profile.status`, and identifies the planner as the source with live-query required for installed identity. A focused regression in `tests/test_management_catalog.py` prevents the stale mismatch labels from returning.

## Verification

- `python3 -m unittest tests.test_management_catalog -v`: 8/8 passed.
- `./tx boot profile status --json`: read-only result reported configured `cli-only` and `managed_script_identity: match`.
- After the catalog edit, `./tx mng catalog list --query "Termux:Boot profile" --json` returned the corrected metadata through the Native CLI.
- No boot file, Android setting, service, desktop session, or PRoot state was changed or restarted.

This confirms catalog truthfulness and the current fixed boot-script identity only. Termux:Boot delivery, Android background policy, cold-boot execution, and full installed/configuration parity remain unverified.
