# Official Termux:Boot Cron integration — 2026-10-19

Phase: `P3`

## Summary

Implemented an opt-in manager for the official Termux:Boot companion app and `$HOME/.termux/boot/` convention. No generic Android init/systemd integration was introduced. The Ternuxx-owned target is exactly `20-ternuxx-cron`; the manager refuses unknown files, symlinks, unsafe directory paths, stale plans, or targets that change after preview. Enable creates this one script with mode `0700`; disable removes only its exact verified content. Existing entries are preserved.

The generated Python entrypoint uses Native Termux's absolute Python and checkout `tx` paths, sets the native `PREFIX`/`PATH`/`TERMUX_VERSION` context, invokes only `tx mng cron start --yes`, and has a 20-second command timeout. It uses a private append-only bounded result log and an invocation lock. The Cron daemon's existing lease/instance identity prevents duplicate scheduler processes. Safe test mode accepts a custom state directory only when the exact isolated-test marker is present.

Shared API operations are `boot.cron.status`, `boot.cron.validate`, `boot.cron.preview`, `boot.cron.enable`, and `boot.cron.disable`. Read operations require `diagnostics.read`; writes require `boot.manage`. The CLI is `tx mng boot cron ...`; changes require a fresh plan ID and `--yes`. The Web bootstrap does not receive `boot.manage`, so these writes are not exposed there.

## Repository and preservation

- Repository: Native Termux `$HOME/ternuxx`.
- Branch/HEAD: `main`, `69e378eb33247678437bda4b2de9ab25f6bcb91d`.
- Worktree status entries: 161 before this increment; 165 at the last recorded source/evidence check, before generated phase documentation refresh. Pre-existing dirty and untracked work was preserved; no reset, clean, stash, commit or push occurred.
- The existing device boot directory had three entries: `00-ternuxx-services` (SHA-256 `53b6745a930af57434cc046861f5df11d9a6aaf76529a857ab4c2cc978ac9b4e`), `ternuxx-recovery` (`4861f2145f58e3d21f0dd4619e30f4a09f555df9a78bfbe515757a567d417c26`), and `10-ternuxx-profile` (`df3061286504d00f090989510bec0874a691ce6bd77f1b68108493d474bb0635`). They were listed and hashed only; none was modified.
- The target `$HOME/.termux/boot/20-ternuxx-cron` was absent on inspection and remained absent at final verification. The repository template is `scripts/termux-boot/20-ternuxx-cron` (SHA-256 `6a71350b32eaf0b96663ed2aab13a3468e8af705bf455a246f234f2582beea9b`). No actual enable/disable was applied.

## Live read-only observations

- `./tx boot status`: `com.termux.boot` confirmed installed; package enabled; `BOOT_COMPLETED` receiver enabled; boot directory present with 3 regular executable scripts. System delivery policy remains unknown.
- `./tx mng boot cron status`: integration `integration_not_configured`; target identity `missing`; companion `confirmed_installed` and enabled; receiver enabled; scheduler stopped/not alive; no script result; actual device-boot delivery `not_yet_verified`.
- `./tx mng boot cron validate`: correctly reports invalid because the dedicated script has not been configured.
- `./tx mng boot cron preview enable`: returned create-only plan for `$HOME/.termux/boot/20-ternuxx-cron`, mode `0700`, SHA-256 `89661de6acbb5fe48e2445a306b8622289f5b8134966296b163dda3d58fdeb99`, plan ID `e67361f1d96adebef5db2881`, and `requires_confirmation=true`. The plan was not applied.

Package detection is delegated to bounded read-only PackageManager path/list queries. An explicit package-manager denial or unfamiliar output maps to `unknown`, not absence. Here the current query positively returned installed/enabled/receiver-enabled states. Ternuxx did not install or open Termux:Boot. The owner must install it from a compatible source and launch it once manually if that has not already been done.

## Isolated safe-mode proof

A temporary directory under Native Termux HOME held a fresh empty Cron state and the exact safe-test marker. The generated entrypoint was invoked twice with `TERNUXX_BOOT_SAFE_TEST=1` and `TERNUXX_STATE_DIR` pointing only to that temporary state. Both invocations exited 0. The private log contained `started` then `already_running`; both entries carried the same scheduler instance ID. The PID and `/proc` start identity were verified against the scheduler record. The fixture scheduler was stopped using `tx mng cron stop --yes` with the same temporary state, then verified stopped; the temporary directory was removed.

This demonstrates the script-to-CLI path and duplicate protection in an isolated runtime. It does not prove Termux:Boot delivered the script during device boot. No production job ran.

## Verification

- `python3 -m unittest tests.test_termux_boot_cron tests.test_runtime_diagnostics tests.test_management_service tests.test_management_sessions tests.test_management_http_runtime -v`: **69 passed**, 0.948 s test runtime, exit 0.
- `bash scripts/repo_test.sh`: **487 passed**, 104.398 s, exit 0.
- `python3 -m unittest tests.test_termux_boot_cron -v`: **9 passed** during focused iteration, exit 0.
- Native Python compilation, `bash -n lib/management.sh bin/tx tx`, schema JSON parsing, `git diff --check`, and `python3 -m tools.repo_knowledge verify` passed; knowledge verification reported 0 findings.
- Live command syntax and read-only outputs: `./tx mng boot cron status`, `./tx mng boot cron validate`, `./tx mng boot cron preview enable`, `./tx boot status`.

## Safety and remaining qualification

No reboot, app install/open, boot-hook enable/disable, production Cron start, production job execution, SSH/PRoot/GUI/audio/Hermes lifecycle action, rootfs edit, or unknown-listener operation occurred. The only scheduler process started/stopped was the isolated empty-state fixture with verified Ternuxx instance ownership.

Termux:Boot is confirmed installed/enabled with its boot receiver enabled, but actual device-boot delivery is **unverified** until the owner performs a reboot and confirms the script log and matching scheduler identity. P3 remains in progress; P4 remains unqualified. The integration stays opt-in and disabled on device.

## Evidence

Source and tests: `lib/termux_boot_cron.py`, `scripts/termux-boot/20-ternuxx-cron`, `tests/test_termux_boot_cron.py`; shared routing/policy in `lib/management_service.py`, `lib/management_authorization.py`, `lib/management_sessions.py`, and CLI in `lib/management.sh`.
