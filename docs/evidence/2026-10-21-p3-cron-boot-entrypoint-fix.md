# P3 Cron boot entrypoint fix — 2026-10-21

Phase: `P3` — remains in progress.

## Finding and repair

The Native Termux host does not provide `/usr/bin/env`, while the Cron boot entrypoint launched the checked-out `tx` shell script directly with `execve`. Its `/usr/bin/env` shebang therefore failed with `CLI could not be executed`.

The Native worktree already contained an owner-authored change that invokes `tx` through Termux's `$PREFIX/bin/bash`. I preserved that change. I added a bounded migration path for the exact committed prior Cron entrypoint hash: preview reports a replacement, apply requires the exact plan ID, and the old bytes are kept in a mode-0600 private snapshot before atomic replacement. Unknown/custom content remains refused. The fixed boot entrypoint itself was not manually executed.

Applied the reviewed replacement through `tx mng boot cron preview enable` and exact-plan apply. It changed only the Ternuxx Cron entrypoint and preserved unrelated Termux:Boot scripts. No package, scheduler, SSH service, PRoot guest, or Android setting was changed by the boot-entry update. The Cron scheduler was left stopped; its registry has zero jobs.

## Verification

- Focused Native Termux Cron boot suite: **18/18 passed**.
- Python compilation and scoped `git diff --check`: passed.
- Live `tx mng boot cron status`: `script_identity=match`, `integration_state=script_configured`, scheduler stopped.
- Live `tx mng boot cron validate`: valid with no blockers.
- Live `tx mng cron status`: zero jobs, scheduler stopped.
- Post-boot authenticated loopback SSH on managed port 8023 succeeded separately. Doctor reported the managed service running, config valid, and SSH banner reachable; listener-to-port ownership remains unknown.
- No reboot or manual boot-script invocation occurred. Actual Android cold-boot delivery remains `not_yet_verified`; the pre-fix `CLI could not be executed` log entry remains historical until a future owner-operated boot provides a new result.

## RB07 and remaining limits

`TERN-20261021-RB07` remains `boot_observed` / `NOT_READY`; automatic resume is disabled. Its saved verification outcome remains `verified_reboot_service_unqualified` because service health and authenticated connectivity were not captured by the boot-time observer. The later live Doctor and authenticated SSH result are separate post-boot evidence and were not written into the private checkpoint.

The post-boot snapshot initially found the recorded `:1` desktop stale, with supervisor/X11/XFCE processes absent. After collecting that snapshot, the owner asked to fix the issues and allowed GUI use. `./tx start --display 1` reconciled the exact stale socket/lock pair and started the Ternuxx-owned X11/XFCE session. Read-only status now reports supervisor, X11, and XFCE live. An X11 capture of `:1` visually showed the XFCE desktop; the temporary screenshot was deleted. Android Activity foreground visibility remains unknown. Debian PRoot was not entered; ownership remains unverified. Android platform Wake Lock state and listener-to-port correlation remain unavailable. These do not get inferred from process names or current SSH reachability.

Doctor after desktop recovery reports 15 pass, 16 info, 1 warning, and 0 errors. The remaining warning is the separately managed 8022 wildcard/password configuration; its current process owner and external reachability are unknown, and it was not changed. The 8023 managed loopback service passes process/config/banner checks and key-authenticated loopback, while listener-to-port correlation remains unknown.

The source/test edits remain uncommitted with the pre-existing Native worktree changes. No commit or push was made.
