# Post-audit safety remediation — 2026-10-20

## Summary

This pass remediated the three scoped code risks from F-03, F-04 and F-06 and added isolated ownership fixtures for F-02. No live PRoot login, PRoot start/stop, rootfs access, Cron daemon/job execution, Termux:Boot installation, GUI, service, listener or database operation was performed. The production Termux:Boot file remained absent and unchanged. P3 remains in progress; P4, interactive workstation, persistence/reattachment and GUI remain unqualified.

The only unexpected side effect was the Python bytecode compile command refreshing ignored cache files. Those files were not removed or restored because no per-file baseline hashes were captured. See Final integrity.

## 1. Fresh baseline and comparison

- Checkout: /data/data/com.termux/files/home/ternuxx; branch main; HEAD 69e378eb33247678437bda4b2de9ab25f6bcb91d; origin https://github.com/soobujmiah/ternuxx.git.
- Fresh baseline before edits: 73 changed tracked paths, 105 untracked files, 112 ignored .pyc files, zero staged paths, zero conflicts. This matches the prior audit’s counts.
- After code and tests, before this report: 73 changed tracked paths, 106 untracked files (the additional path is lib/boot_state_path.py), and 113 ignored files.
- This report raises the expected untracked count to 107. No tracked path was restored, staged or committed. HEAD and branch are unchanged.
- Default Cron jobs and execution-ledger files were absent at the inspected state path. The installed Termux:Boot 20-ternuxx-cron file was absent. No production state was modified.
- The old Ternuxx executable deletions and tx replacements were already present at baseline. They were not changed or restored.

## 2. Finding dispositions

### F-03 — PRoot loader environment: FIXED in source; isolated tests PASS

Before: isolated probe copied the entire host environment; interactive login used an allowlist but explicitly re-added LD_PRELOAD. Thus a host-provided loader variable could affect the native proot-distro process before its guest environment sanitization.

Change: lib/proot_sessions.py now builds the probe environment with _proot_host_environment and removes every LD_* variable. Interactive login applies the same filter before its existing explicit allowlist. This preserves required PREFIX, PATH, TERM, locale, display, audio and Mesa/Vulkan settings; no blanket environment clearing was added. The active shell environment was not changed. No attacker library was loaded.

Tests use harmless sentinel strings for LD_PRELOAD, LD_LIBRARY_PATH and LD_AUDIT and verify both launch environment builders strip them while preserving required runtime settings. The process launch itself was not performed. Live compatibility with the Termux runtime and interactive guest remains unqualified.

### F-04 — Termux:Boot state containment: FIXED for path resolution, directory creation and boot log/lock access; isolated tests PASS

Before: the boot script used a string-prefix HOME check and walked state parents without requiring HOME to be reached. An override outside HOME could reach log/lock creation.

Change: new lib/boot_state_path.py resolves relative overrides beneath canonical HOME, rejects empty/malformed paths, parent traversal, HOME itself, sibling-prefix escapes, symlinks, non-directories, wrong owner and unsafe permissions. Production HOME must be under Native Termux’s home root. Directory creation uses descriptor-relative mkdir/open with O_NOFOLLOW, verifies ownership/modes and returns a pinned boot directory descriptor. The generated entrypoint opens its log and lock relative to that descriptor. The repository script remains byte-for-byte equal to the manager template.

Tests cover absolute and relative paths, nonexistent nested directories, traversal, sibling-prefix paths, symlinked parents/HOME, file components, unsafe permissions, malformed values, a symlink inserted between validation and directory creation, and an entrypoint run with a temporary HOME and fake tx command. Rejected paths produced no writes in the external fixture directory. The installed boot script, receiver and actual boot state were not changed.

Residual limit: the boot entrypoint passes the validated canonical state path to the existing tx/Cron manager, which reopens its state by pathname. The boot log/lock are descriptor-anchored; eliminating a same-UID rename race across the manager’s path-based storage APIs requires a broader dirfd-aware API. The checked component creation fails closed on symlinks observed during the walk.

### F-06 — Cron schema/runtime mismatch: FIXED for new writes and dispatch; isolated tests PASS

Before: schema-v1 and validation accepted Debian PRoot execution, retries, queueing/catch-up, capability claims and startup-trigger flags that the current runtime did not execute as declared.

Change: new validation and updates now permit only:
- environment native-termux;
- one attempt, zero delay and fixed backoff;
- missed-run skip;
- concurrency skip_overlap;
- no per-job capability claims;
- both boot and scheduler-recovery trigger flags false.

Timeout remains bounded to 1–86400 seconds and is passed to the action executor. Output policies remain the implemented discard and bounded-redacted values. The schema now states these limits and includes the implemented scheduler.self_test action.

Compatibility: registry reads explicitly allow structurally valid older v1 records so they remain inspectable. Unsupported legacy policy records are refused before event claim and before launch; they are not silently rewritten or migrated. The default live jobs file was absent, so no migration was needed or applied. If a separately configured state directory contains old jobs, they remain readable but require an explicit later migration or policy edit before dispatch.

## 3. PRoot ownership mismatch fixtures — PARTIALLY FIXED; historical cause UNVERIFIED

The verifier now accepts a proc_root fixture path and checks the recorded process UID against the current Termux UID in addition to start identity, group/session, marker evidence, launcher/rootfs device+inode, translated argv, guest IDs and guest working directory. Production defaults remain /proc. No ownership criterion was weakened.

Synthetic fixture tests verify a complete matching interactive identity and fail-closed handling for stale PID, process-start mismatch/PID reuse, group mismatch, missing marker evidence, malformed marker, launcher argument mismatch, rootfs inode mismatch, wrong UID, wrong working directory, missing proc files/ambiguous evidence and partial registry records. Recovery tests mock the existence probe and confirm no real signal is sent by the fixture.

These fixtures establish that the current verifier accepts its stated contract and rejects the requested mismatches. They do not reproduce the prior live login failure. The historical root cause remains unresolved because the failed process’s complete proc snapshot and exact launcher evidence were not captured and a live retry is prohibited. Keep interactive qualification BLOCKED until a separately authorized, disposable environment captures cwd, status UID, translated argv, marker, start/group identity and rootfs/launcher identity together.

## 4. Source, test and documentation changes

This pass edited existing pre-audit untracked files: lib/proot_sessions.py, lib/cron_registry.py, lib/cron_execution.py, lib/termux_boot_cron.py, scripts/termux-boot/20-ternuxx-cron, schemas/cron-job-v1.schema.json, docs/architecture/CRON-JOBS.md, docs/architecture/PROOT-SESSIONS.md, tests/test_proot_sessions.py, tests/test_termux_boot_cron.py, tests/test_cron_registry.py and tests/test_cron_execution.py.

It created lib/boot_state_path.py and this report. It appended a new section to the already-dirty CURRENT_STATE.md without replacing existing bytes. No previously deleted entrypoint or legacy workflow file was restored.

## 5. Tests and verification

Final isolated regression command, run in Native Termux from the repository with PYTHONDONTWRITEBYTECODE=1 and PYTHONPATH=tests:lib:

    python3 -m unittest test_proot_sessions.PRootVerificationFixtureTests test_proot_sessions.PRootSessionRegistryTests.test_interactive_profile_refuses_non_tty_before_creating_state test_proot_sessions.PRootSessionRegistryTests.test_profile_preview_binds_plan_to_rootfs_launcher_and_profile test_termux_boot_cron test_cron_registry test_cron_execution

Exit status 0; 52 tests passed in 0.678 seconds. The tests use temporary state. Boot integration invokes only a temporary fake tx command. PRoot ownership tests use synthetic proc files and mocks. The TTY test refuses before launching PRoot.

Additional checks:
- Python AST parse of nine source/test files and JSON parse of schemas/cron-job-v1.schema.json: PASS.
- Repository boot script equals generated template: PASS.
- git diff --check: PASS.
- No schema validator dependency was installed.
- Full suite was not run; the broader suite was not needed to validate this narrow remediation and its complete side-effect profile was not established.
- No production Cron, boot, PRoot, GUI, service, network or rootfs test was run.

An earlier py_compile command completed successfully for the same nine Python files but wrote/refreshed ignored bytecode. It was not needed for the final syntax result; AST parsing above is read-only.

## 6. Legacy compatibility

The .bashrc db/droot aliases, x.sh, xgo and killx were not edited or invoked. tx mng remains canonical and the existing tx management alias remains intact. The old ternuxx executable deletions and tx replacement were present in the fresh baseline; no references establishing an external compatibility requirement were found in the scoped source/tests, and this pass did not restore them. tx db remains a PRoot login command, not TXDB. AJ peer-to-login and TXDB remain unidentified and were not implemented.

## 7. Remaining risks and acceptance limits

- F-01 shared rootfs writes through the installed proot-distro normal-login path remain unresolved. No rootfs or profile hook was read or modified in this pass. Live interactive login remains blocked.
- F-02 historical runtime mismatch remains unverified despite synthetic contract tests.
- F-05 PRoot read-only inspection may still create its registry lock file.
- F-07 desktop stale-record check/replace race was outside this remediation and remains unverified.
- F-08 old ternuxx wrapper compatibility remains undecided.
- F-09 AJ peer-to-login/TXDB remain blocked on target identification.
- F-10 GUI/X11/GPU, detach/reattach, production boot delivery and listener ownership remain unqualified.
- Cron boot/recovery delivery remains disabled; no PRoot boot integration was added.
- P3 remains in progress; P4 is not qualified.

Future live acceptance requires separate scope: first resolve the shared rootfs launcher write contract, then use a disposable isolated rootfs/state and genuine TTY; record all identity dimensions and exit status; verify no unrelated session or GUI change. GUI qualification additionally requires current display/socket verification, harmless disposable client evidence and exact cleanup. No production scheduler/boot activation or reboot is part of this report.

## 8. Final integrity

- HEAD remains 69e378eb33247678437bda4b2de9ab25f6bcb91d on main; no commit, push or reference change.
- The 73 pre-existing changed tracked paths and 105 baseline untracked files were preserved. Before the evidence report, untracked count was 106 because of the new helper; the report raises the expected count by one. No staged or conflict entries were introduced.
- No rootfs, profile hook, production Cron/ledger, installed Termux:Boot script, GUI, listener, service, database or active PRoot process was modified or signaled.
- The successful py_compile command refreshed nine ignored cache entries: lib/__pycache__/boot_state_path.cpython-314.pyc, cron_execution.cpython-314.pyc, cron_registry.cpython-314.pyc, proot_sessions.cpython-314.pyc, termux_boot_cron.cpython-314.pyc, and tests/__pycache__/test_cron_execution.cpython-314.pyc, test_cron_registry.cpython-314.pyc, test_proot_sessions.cpython-314.pyc, test_termux_boot_cron.cpython-314.pyc. The ignored count is now 113 versus 112 at baseline. Eight caches were refreshed and the helper cache is new. Since no hashes were captured before compilation, none was removed or restored.
- No other external changes were observed. All edits by this pass are enumerated above; no change was made to the active development session or shared system state.
