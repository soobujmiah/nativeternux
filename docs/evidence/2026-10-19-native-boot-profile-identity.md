# Native boot-profile identity diagnostics — 2026-10-19

## Finding and implementation

A live read-only check showed that `tx boot profile status` reported the configured profile and prerequisite readiness without checking whether the fixed Ternuxx-managed Termux:Boot script existed or still matched it. Status now reports `managed_script_identity`:

- `match`: exact current managed script for the configured profile.
- `legacy_match`: recognized v1 script with the configured profile semantics.
- `missing`: profile is configured but its script is absent.
- `mismatch`: script bytes do not correspond to the configured profile, or an unmanaged script is orphaned at the reserved Ternuxx path.
- `unsafe`: symlink, wrong owner/mode/type, inspection error, or race during identity-safe open.
- `not_configured`: no profile and no managed script are installed.
- `not_checked`: preview-only response; preview does not inspect current boot files.

The check inspects only `$HOME/.termux/boot/10-ternuxx-profile`, uses `lstat` plus `O_NOFOLLOW`/`fstat`, verifies the Termux UID and mode `0700`, and reads at most 65,537 bytes. It does not follow a script symlink, read unrelated boot scripts, or repair anything. The response contract is schema v2; the profile configuration file format remains schema v1.

## Verification

- Boot-profile tests: 14/14 passed.
- Shared management-service tests: 24/24 passed.
- Full Native Termux suite through SSH 8022: 352/352 passed in 71.703 seconds.
- Live `./tx boot profile status --json` reports configured `cli-only`, script identity `match`, schema version 2, and `read_only=true`.
- Both boot response schemas parse; `git diff --check` passes.
- No boot file, Android setting, service, desktop, or Debian PRoot state was changed.

P3 remains in progress. This check does not prove Termux:Boot delivery, Android background policy, or cold-boot behavior.
