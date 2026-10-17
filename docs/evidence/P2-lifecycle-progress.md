# P2 native desktop lifecycle implementation progress

- Phase: `P2` (in progress; not a completion record)
- Reviewed: 2026-10-17
- Evidence type: repository source review only
- Device/runtime actions: none; no packages installed and no desktop/service started or stopped

## Source now present

- `lib/desktop.sh` provides initial `start`, `stop`, `restart`, and `status` command paths.
- `lib/desktop-supervisor.sh` records process start ticks and command markers, waits for the X11 socket, starts XFCE under NativeTernux-owned XDG paths, and limits cleanup to recorded child identities.
- Startup failure cleanup uses SIGTERM only. No broad process matching, SIGKILL, wildcard socket deletion, PulseAudio control, Ternux launcher call, or PRoot rootfs access is intended by these files.
- Session state and logs are kept under the NativeTernux state directory; state directory resolution is required to remain under Termux HOME.
- Start and stop use a NativeTernux session lock to avoid concurrent lifecycle operations.

## Not established

- No shell test suite, runtime invocation, package installation, or physical-device desktop validation was performed.
- Exact Termux:X11 command-line and process behavior, socket readiness, DBus/XFCE lifetime, startup rollback, repeated operations, and preservation of an unrelated session remain unverified.
- The current supervisor tracks the launched DBus/XFCE command and X11 command PIDs. Whether TERM to the recorded DBus/XFCE PID always terminates every descendant on the target build is specifically unresolved; verify process-tree cleanup or add an isolated process-group owner before calling the lifecycle safe.
- This implementation must not be treated as release-ready or invoked on the device under the current read-only operation boundary.

## Remaining P2 gate

Review this source implementation, then validate command behavior in an authorized isolated environment and on the target device. Record versioned evidence for successful start, repeated start, partial startup failure, stop, repeated stop, and unrelated-session preservation. Only then consider the P2 completion workflow.
