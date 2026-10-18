# Native Ternux X11 app handoff evidence

**Observed:** 2026-10-18, Native Termux over owner-started SSH 8022. **Repository HEAD:** 5232a20b63c5f9f66d8f3e74208ed5bff8c4340a plus the uncommitted changes listed below. **Purpose:** launch one fixed Debian GUI app on the already-running Native Termux/Ternux X11 session without starting/stopping either desktop.

## Baseline and safety

- ternux status --json: v1.4.0; status=running, x11_running=yes, PulseAudio stopped, VirGL stopped.
- ternux backend show --json: backend=zink, vulkan=yes, renderer=unknown, Adreno 825.
- Existing Debian guest: Debian 13.7, user sbj; existing rootfs was used in place. The pre-existing PRoot login PID 16526 was not signaled or closed.
- The current GUI is the owner's Native Termux/Ternux session on :1. The owner clarified that the current ~/x.sh/aliases are intentionally customized. No x.sh, x, xgo, or killx file/configuration was written.
- No Ternux/Ternuxx start/stop/restart/cleanup, Android Activity request, package operation, boot change, or reboot occurred.

## Renderer check

Command:

    proot-distro login debian --shared-tmp --user sbj --env DISPLAY=:1 -- glxinfo -B

Observed: display :1; GLX renderer query reports Vendor Mesa, Device zink Vulkan 1.4 (Adreno (TM) 825 (MESA_TURNIP)), Mesa 25.0.7, Accelerated: yes. This is direct evidence for this guest GLX process on :1. It does not prove server PID ownership, all XFCE processes' renderer, inference capability, or benchmark performance. The host Ternux backend summary still reports renderer unknown. A prior glxgears frame rate is not used as acceleration evidence.

## Implemented app handoff and live result

The shared operation now accepts optional session_owner and display; Ternux selection requires an explicit display. CLI example:

    ./ternuxx management app launch files --session ternux --display :1

The helper performs read-only checks of Ternux's self-reported running/X11 and Zink/Vulkan state, validates the selected X11 socket and Debian guest xdpyinfo, then runs only a fixed catalog app. It does not ask Android to foreground Termux:X11 and does not claim display/audio lifecycle ownership. The existing default Ternuxx session route remains the default; the shortcut manager is refused for Ternux selection because its dialogs are scoped to the Ternuxx desktop.

The command started the Debian Thunar process (observed PID 17894) under a new transient PRoot invocation and left it running for the owner to inspect/close. No machine-observable GUI visibility assertion was collected; gui_visible remains unknown. This is a process-start and X11-connectivity pass, not full PRoot lifecycle qualification.

## Automated checks

- python3 -m unittest tests.test_proot_shortcuts -v: 12/12 PASS.
- bash -n scripts/proot-x11-app.sh lib/management.sh: PASS.
- python3 -m py_compile lib/proot_shortcuts.py lib/management_service.py tests/test_proot_shortcuts.py: PASS.
- git diff --check: PASS.
- bash scripts/repo_test.sh: 312/312 PASS on Native Termux after the final code changes. This is not CI/build, listener ownership, reboot, or GUI-visibility qualification.

## Limits and next checks

- Native Ternux self-reported status is not proof of X server process ownership. PID/socket ownership remains unverified.
- Ternux/Ternuxx session lifecycle and audio lifecycle remain outside this adapter.
- Current :1 GLX path is Zink/Turnip accelerated; no CPU/GPU inference workload or benchmark was run.
- The launched Thunar window/process remained open at final verification and should be closed by the owner when finished. A follow-up repo-test run was briefly interrupted during reconnect, then a clean rerun completed 312/312. The old login PID 16526 and its existing environment remain untouched.

## Follow-up status correction (2026-10-18)

The Thunar PID reported above was absent from a later read-only process snapshot; this historical launch result does not establish that the window remains open or visible. GUI visibility is unknown. See [live session state reconciliation](2026-10-18-live-session-state-reconciliation.json) for the current check.
