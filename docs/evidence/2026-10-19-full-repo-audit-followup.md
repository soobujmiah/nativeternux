# Full repository audit follow-up — 2026-10-19

## Scope and baseline

- Repository: soobujmiah/ternuxx, branch main, base commit 69e378eb33247678437bda4b2de9ab25f6bcb91d.
- The working tree already contained 59 changed/untracked paths before this audit. Existing work was preserved.
- Reviewed project instructions, current state, phase roadmap and latest P3 gate audit, repository manifest/classification, security policy, architecture/management documents, and the changed-path summary.
- The audit did not start/stop services, interact with Android UI, alter boot/SSH settings, enter or mutate the Debian rootfs, or perform a device lifecycle action.

## Findings and follow-up

- Living architecture records still said the Web client and TUI did not exist, while the 2026-10-19 implementation evidence records an authenticated read-only Web UI and service-backed TUI. Updated the architecture overview, ADR-0004, management API proposal, and shared-management plan to describe the implemented partial clients and remaining gaps.
- The P3 phase-state summary still reported the older 326/326 test run and omitted the newer shared clients. Updated the human-authored P3 summary and linked the 2026-10-19 client and audit evidence. Refreshed generated phase blocks with tools/phase_docs.py; P3 remains in progress.
- The Web runtime honored TERNUXX_WEB_MODE by granting desktop.manage and applications.launch, and the page exposed desktop start/restart/stop and PRoot app-launch controls. This conflicted with the P3 requirement that HTTP mutations remain off and lacked the required server-side plan/confirmation contract. Disabled mutation dispatch for all HTTP runtime modes, restricted Web sessions to diagnostics.read, removed mutation controls, and added a regression test that attempts desktop.start with the mode environment variable set. The CLI/TUI path remains separate.
- Updated stale HTTP adapter/session/authorization module docstrings to reflect the implemented transport.

## Verification

- Native Termux repository suite: 343 tests passed in 73.964 seconds with bash scripts/repo_test.sh over the owner-started SSH 8022 shell.
- Repository knowledge verification: 0 findings. Final diff check, JSON parse, and shell syntax check passed. The runtime-focused suite passed 6/6 after the Web mutation fix; the final full suite passed 343/343. Added a regression test showing a Web-mode environment flag cannot authorize desktop.start; the dispatcher was not called.
- This audit relied on fixture/unit evidence; it does not qualify browser UX, general X11 management, cold boot, PRoot ownership, HTTP mutation, or overall P3 completion.

## Next work

P3 remains open. Continue the roadmap's remaining provider/diagnostics and recovery acceptance. Keep reboot readiness UNVERIFIED until explicit owner-approved post-reboot qualification; preserve the existing Debian PRoot/X11 workstation and both SSH endpoints.
