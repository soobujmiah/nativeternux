# P3 owner visual acceptance and boot/Cron recheck — 2026-10-20

Phase: `P3`

## Owner visual acceptance

The owner explicitly accepted the visual review for the installed GTK management client, TUI, Web interface, and Native XFCE PRoot Apps menu on 2026-10-20. This closes the owner-review item previously listed in the P3 active-work summary. It is owner-supplied acceptance; no new screenshot or pixel measurement was made during this recheck. Native XFCE `:1` remains live. The machine-readable `gui_visible` field remains `unknown` because visibility is not inferred from process/socket readiness.

The owner separately confirmed that Native XFCE is visible on the Android screen. This is recorded as human visual confirmation. The live `gui_visible=unknown` field remains a machine-observation limitation; it does not override the owner's report.

## Boot and Cron live recheck

- Termux:Boot package and `BOOT_COMPLETED` receiver report enabled; startup and system delivery policy remain `unknown`.
- Ternuxx's exact managed Cron boot script is present as the fourth regular executable in `$HOME/.termux/boot/`; source/target identity matched after preview-bound installation.
- `tx mng cron status --json` reports scheduler `running`, instance `sched-3e23060200dc456fb293c26d4273d09d`, verified lease and healthy dispatch, zero configured jobs, zero executions, and `device_boot_delivery=not_qualified`.
- The installed boot script was invoked directly. It exited successfully and reported the already-running instance (`started_by_script=false`), confirming duplicate protection and the script-to-CLI route. This was a manual test, not a device-boot event.
- Existing `00-ternuxx-services` and `ternuxx-recovery` installed copies differ from current repository source. This recheck did not replace them; the legacy recovery module remains the installed runtime target, and an exact, state-preserving deployment flow is not implemented for these entries.
- Fixture coverage includes simultaneous-lifecycle exclusion by a held private session lock and recovery refusal while that lock exists. These are source fixture checks, not an Android boot or scheduler race test.

## Gate result

**Partial; P3 remains in progress.** Owner visual review is accepted, the configured Cron path is live and duplicate-safe, and lifecycle lock contention is covered. Actual cold-boot delivery, manual-open/background policy, Android startup restrictions, and the stale service/recovery script deployment path remain unqualified. The existing SSH/Codex and Native GUI sessions were kept alive, so this recheck did not reboot the device. Do not mark a manual script run as boot-delivery evidence.

## Verification

The Native full fixture suite passed 597/597 in 103.066 seconds after increasing the desktop fixture's scoped cleanup timeout from 8 to 20 seconds. The previously timing-out stale-record fixture passed in isolation and in the final full run. The suite does not exercise Android boot delivery.

## Evidence

Live observations were obtained over the existing Native Termux SSH 8022 checkout on 2026-10-20. Related source/fixture gates are in [`docs/ROADMAP.md`](../ROADMAP.md), [`tests/test_desktop_lifecycle_fixture.py`](../../tests/test_desktop_lifecycle_fixture.py), and [`tests/test_desktop_session_recovery.py`](../../tests/test_desktop_session_recovery.py).
