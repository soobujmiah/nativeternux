# Native boot-profile preview/apply parity — 2026-10-19

## Finding and change

The native `tx boot profile preview <profile>` output and the managed Termux:Boot script were rendered separately. Their commands matched, but the supported `cli-only` and `native` preview text omitted the final newline present in the managed script bytes. Preview is the consent artifact for applying boot profile changes, so these outputs now have an explicit byte-for-byte parity contract. The preview output includes the managed script's terminating newline, and regression assertions compare both supported profile previews directly with `_managed_script()`.

The `proot` and `hybrid` boot profiles remain blocked until their ownership-aware providers exist. No profile was enabled, disabled, or applied on the device.

## Verification

- Focused Native Termux boot-profile tests: 12/12 passed.
- Full Native Termux repository suite through SSH 8022: 347/347 passed in 69.117 seconds.
- `git diff --check`, JSON parsing, and generated phase-document refresh passed.
- Runtime profile files, Termux:Boot scripts, Android settings, services, desktop, and the Debian PRoot were not changed.

P3 remains in progress. Reboot/cold-boot qualification remains unverified and was not attempted.
