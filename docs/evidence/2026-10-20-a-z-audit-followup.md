# Full repository audit follow-up — 2026-10-20

Phase: `P3` (in progress; P4 remains planned)

## Evidence

## Native target and live state

Connected to the Native Termux checkout at `$HOME/ternuxx` through SSH 8022 using the existing private key selected explicitly; `id` confirmed Android UID `u0_a490` and Native `$PREFIX`. The Native checkout is the shared worktree for this source change. The managed Native desktop remained running on `:1` throughout; no Termux app or GUI session restart was performed.

`tx gui status --json` reported `running`, with the supervisor, Termux:X11, and XFCE live; Android GUI visibility remains `unknown`. `tx mng graphics status native --json` reported Adreno 825, OpenGL accelerated, and the saved KGSL/Freedreno candidate. A separate `tx mng graphics verify native opengl :1 --json` returned `render_verified=true`, renderer `Adreno (TM) 825`, score `561`. Vulkan remains device-enumeration-only with no draw verified. This is a bounded workload result, not presented-display FPS, long-duration thermal evidence, or inference qualification.

## PRoot interactive ownership fix and live acceptance

The exact interactive start preview identified the fixed Debian rootfs and launcher by device/inode and disclosed the installed `proot-distro` normal-login profile/sidecar writes; Ternuxx does not snapshot or roll back those package-owned writes. The first live Ternuxx attempt failed closed during the brief `proot-distro` wrapper-to-`proot` exec transition: the session/group, rootfs/launcher, marker, and login command were visible, but the translated guest cwd and numeric `--change-id` argv had not appeared yet. No shell was admitted. The failed process was absent; a fresh reconciliation preview proved `process_absent`, then exact confirmation marked only that private session record stopped without signaling any process.

The manager now waits up to five seconds for the exact translated PRoot identity before accepting a foreground login. It still requires the rootfs cwd device/inode, exact guest UID/GID argv token, session/process group, marker, launcher/rootfs identity, and fixed login command. It does not relax the checks or retry indefinitely. Fixture tests cover successful delayed exec and bounded fail-closed timeout.

A second exact-preview Ternuxx start succeeded. While it was live, `tx mng proot sessions show` and `health` reported `ternuxx_verified`, matching PID start identity and session group. The guest printed UID/GID `1000:1000` and cwd `/home/sbj`. `exit` completed with code 0 and zero remaining session processes. A separate direct package login used to inspect normal guest behavior also exited cleanly. Existing unrelated PRoot PID 25612 was inspected read-only and preserved. No Debian package install/removal, graphics rewrite, desktop change, or Bionic/glibc library copy occurred.

## Documentation consistency findings

Several current-facing Native graphics paragraphs still described `llvmpipe` and Vulkan incompatibility as the current Native renderer despite later candidate-backed Adreno 825 OpenGL and bounded benchmark evidence. Updated README, architecture, capability/fallback, and PRoot GPU descriptions to distinguish the qualified candidate-backed GL result from stock llvmpipe and from current session state. Native status was rechecked after that documentation review and again reported Adreno 825 / accelerated; Vulkan remains unverified as a draw workload. Dated historical evidence snapshots remain unchanged.

The live private XFCE data directory contains 35 generated PRoot entries; all 35 have only `X-Ternuxx-PRoot` in `Categories`. Parsed live menu XML includes that category under **PRoot Apps** and excludes it from Accessories and Accessibility. No generated PRoot desktop entry exists outside the private Ternuxx XFCE directory. The menu was not visually inspected in XFCE; visual presentation remains a manual acceptance item.

## Remaining phase and release work

- Complete the other P3 ownership/recovery gates in the roadmap: desktop stale-reconciliation race, concurrent lifecycle/recovery cases, and selected service/boot recovery acceptance. Do not activate P4 until the P3 exit gate is reviewed.
- Keep fresh Debian package/config replay and first-install reproducibility open; preserve the installed Debian rootfs and existing workflows.
- Native GLES runner, Native Vulkan drawing, automatic per-workload fallback/API enforcement, clean-install candidate-driver reproduction, VirGL guest workload, nested Xephyr DRI3/presentation, GUI visual acceptance, audio audibility, and NPU workload remain incomplete or unverified.
- Check the generated **PRoot Apps** menu visually on the device; file/category checks alone do not establish how the live XFCE menu presents it.
- Repository knowledge status may be stale until the post-push sync workflow regenerates it; never edit generated `.repo/STATUS.md` by hand.

## Verification

- Native graphics status and bounded OpenGL workload: passed as recorded above.
- Native Ternuxx interactive Debian login: passed with exact ownership checks; exit code 0, no remaining session processes.
- `tests.test_proot_sessions`: 29 passed on Native Termux after the bounded-wait and read-only inventory changes.
- Read-only PRoot session inventory no longer creates `.sessions.lock`; it reads the atomically replaced registry snapshot. A focused test verifies the path stays absent.
- The full Native repository suite passed: 581 tests in 133.632 seconds, exit 0.
- `tests.test_proot_sessions` passed 29/29 on Native Termux. `git diff --check`, strict README bridge, and repository knowledge verification passed after the inventory change.
- Final live check reports Native `:1` supervisor, Termux:X11, and XFCE running; graphics status remains Adreno 825 / accelerated, Vulkan enumeration-only. Every Ternuxx-managed interactive record is stopped/released, and the unrelated PRoot process remains unmanaged and preserved.

## CI portability follow-up

The first GitHub Actions run after the push passed dependency, repository-knowledge, and README-bridge checks, but the Ubuntu test suite exposed one environment-specific failure: `test_gui_and_canonical_proot_gui_reject_unknown_actions` received exit 127 because `lib/proot.sh` directly executed a helper whose shebang names the Termux Bash path. The Native 581-test suite passed. The helper now runs under the active `$BASH` interpreter, preserving the Native interpreter while making the checkout tests portable. The exact failing CI test passes locally after this change; the next pushed CI result is pending.

Overall release remains **NOT RELEASE-READY**; P3 stays in progress and P4 stays planned.
