# GUI Activity monitoring policy

The Linux Termux:X11/XFCE session and the Android Termux:X11 Activity are separate resources. `tx gui`, desktop status, Doctor, and management API status calls never launch the Activity or inspect Android focus. Manual Linux GUI startup remains available; open Termux:X11 yourself when you want to view it.

## Shared policy

The policy is managed through the same API used by CLI, TUI, Web UI, and GTK:

- `desktop.monitor.status` is read-only.
- `desktop.monitor.configure` updates policy through the CLI, guided TUI/GTK controls, or Web form.
- CLI: `tx gui monitor status|enable|disable|configure`.
- Web UI has a separate monitor panel. The form uses the desktop.monitor.manage capability. Other Web resource actions have their own separately scoped permissions; the full current client boundary is in the capability matrix.

Schema version 1 lives at `$TERNUXX_STATE_DIR/gui-monitoring.json`, in the private Ternuxx state directory. Updates use a same-directory temporary file, fsync, atomic replace, a private mode-0700 lock directory, and mode 0600. Symlinks, foreign owners, broad permissions, malformed schemas, and intervals outside 30 seconds through 24 hours are rejected. Accepted units are seconds, minutes, and hours; storage normalizes them to seconds.

Defaults are `enabled=false`, 300 seconds, `focus_check=false`, and `activity_launch=false`. Enabling Linux-only monitoring does not query Android. Activity package availability is queried only if focus checking or launch is explicitly enabled. Activity launch requires focus checking and occurs only if Linux GUI health is `running`, Termux:X11 is reported available, and the Activity is verified in the background. Foreground state, missing Android command access, or ambiguous output prevents a launch.

## Scheduler and status

One Runit-owned scheduler process runs `scripts/termux-services/ternuxx-gui-monitor/run`. A process-wide `flock` prevents duplicate loops. It reloads policy at bounded intervals; disabled policy performs no Activity or focus checks. The scheduler is not auto-started by status, diagnostics, GUI startup, or API reads. `scheduler=not_running` means policy is saved but no scheduler process has the lock; `enabled=true` alone is not evidence that scheduled monitoring is active.

Status distinguishes Linux health (from `desktop.status`), Android Activity availability, Activity focus, last check/result, freshness, next check, scheduler state, and error. The status operation itself sets `activity_requests_performed=false` and `focus_probe_performed=false`. Scheduler outcomes append JSON lines to `$TERNUXX_STATE_DIR/log/gui-monitoring.log`; the private policy stores the last check, result, Activity/focus result, and last error.

Android `dumpsys` output may be restricted or vary by platform. Unreadable or ambiguous output is `unknown`; it is not treated as background and cannot trigger Activity launch. No Activity request or focus probe was run during policy implementation or tests. The live monitor policy remains absent/default-disabled, and the new scheduler service has not been installed or started on the device.

## Qualification

Fixture tests validate defaults, safe persistence, schema and interval bounds, symlink rejection, Linux-only checks, singleton locking, freshness, and launch gating for background/foreground/unknown states. Real-device qualification must be explicitly enabled by the owner later, begin with focus checks and Activity launch disabled, verify interval/log behavior, and only then opt into Activity launch. The current task did not enable or start the scheduler.
