# Non-contract CLI app shortcut removal

**Date:** 2026-10-19 (Asia/Dhaka)
**Base:** `69e378eb33247678437bda4b2de9ab25f6bcb91d` (`main`, equal to `origin/main` before this work)
**Execution:** native Termux checkout over SSH port 8022

## Scope

Removed the newly added top-level `tx app` / `tx apps` shortcuts because they bypassed the shared-management operation contract. The shared service's `management app` and shortcut operations remain the authoritative interface. The historical `tx shell` and `tx gui` aliases remained at that checkpoint; the separate bare `gui` Bash function is being retired in the current workstation qualification pass. The PRoot desktop alias was removed in the follow-up below. Canonical PRoot desktop control is `ternuxx proot gui`. The existing `proot-x11-app.sh` and shared-service-backed desktop shortcut manager remain intact.

Deleted only the direct shortcut implementation and its tests (`lib/proot_apps.py`, `tests/test_proot_apps.py`). Added a regression check that `app` and `apps` are not registered commands. Existing unrelated dirty source and untracked files were preserved.

## Verification

- Focused launch-command suite: **7/7 passed**.
- Full native Termux suite (`bash scripts/repo_test.sh`): **333/333 passed in 73.396 seconds**.
- `git diff --check`: clean.
- Python AST parsing: 83 files; JSON parsing: 162 files; Bash syntax check: clean.
- `python3 -m tools.repo_knowledge verify`: **0 findings** before metadata refresh.
- No GUI lifecycle, boot profile, Android setting, PRoot workload, or reboot action was performed.

## Remaining state

P3 remains active. This cleanup does not qualify P3's open provider/diagnostics or reboot gates and does not advance the phase. The 8022 SSH development session remains active; no commit or push was made.


## Follow-up: remove `tx pgui`

The first cleanup left `tx pgui` registered; the owner clarified that it must be removed too. Removed that alias and routed canonical `ternuxx proot gui` directly through the existing repository-owned `scripts/proot-gui0.sh`. The Ternuxx script and current Debian setup were preserved.

- Focused launch suite: **6/6 passed**.
- Full native Termux suite: **332/332 passed in 78.206 seconds**.
- Runtime checks: `tx pgui`, `tx app`, and `tx apps` each report `Unknown command`; `ternuxx proot --help` documents the script-backed canonical route.
- No PRoot lifecycle or rootfs operation was run.
