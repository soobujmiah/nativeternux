# Native Ternuxx continuation audit — 2026-10-20

## Repository and execution target

I used the owner-started SSH 8022 development shell, as required by `AI_ASSISTANT.md`. Runtime checks confirmed Native Termux (Android kernel, UID `u0_a490`, Termux `PREFIX`) and the canonical checkout at `$HOME/ternuxx`. The remote is `https://github.com/soobujmiah/ternuxx.git`; branch `main` is at `845c4e2` and matches `origin/main`.

The tracked worktree was clean. The untracked `.qualification/` directory contains the earlier extracted Mesa 26.3.0 candidate and its run evidence. The untracked `.superdesign/` directory contains owner design artifacts. Both were preserved. No source or generated state files were edited by this read-only audit.

## Project authority and phase

I read the repository contract, current state, README, roadmap/phase status, project vision and architecture, security, knowledge-sync guidance, PRoot GPU guidance, GPU qualification record, and relevant W7l execution evidence. The repository's native checkout is the implementation authority; the separate `soobujmiah/ternux` project/rootfs remains outside this task. P3 is `in_progress`; P4 is `planned`. No phase gate should be marked complete from the prior candidate-process result.

The current W7l evidence establishes that an extracted community Mesa/Turnip build can enumerate Adreno 825 and render a bounded GLX workload when invoked with the candidate environment. The ordinary Native XFCE/GTK session remained on stock llvmpipe. No Native Mesa package was installed, no shared library was replaced, and the Debian PRoot renderer is separate evidence.

## Fresh live-state observation

At 2026-10-20 12:46:20 +06, `./tx gui status --json` returned:

- display: `:1`
- Ternuxx lifecycle: `stale`
- supervisor, Termux:X11, XFCE: `absent`
- GUI visibility: `unknown`

At the same time, `./tx proot status --json` reported Debian installed, the PRoot manager available, two host process candidates with ownership `unverified`, and `guest_entered=false`. I did not enter Debian or touch its rootfs.

This current state supersedes the earlier checkpoint that described Ternuxx XFCE `:1` as running. Since the session is absent, the next W7l integration test would **start** a new Ternuxx GUI session on `:1` with the candidate Mesa environment; it would not restart an active session. That operation is not performed in this audit. It requires explicit authorization because it changes Native GUI/session state; that authorization is pending.

## Actions and result

This audit used 8022 only. It did not install or remove packages, replace graphics libraries, change compositor settings, start or stop services, enter PRoot, modify Android settings, or run tests. The phase remains P3 in progress and overall release remains NOT RELEASE-READY. The candidate artifacts and owner design directory remain untracked and untouched. No commit or push was made.

## Authorized W7l follow-up — bounded session test

After I recorded the audit, the owner authorized the work needed within Ternuxx repo scope. I started a new Ternuxx GUI session on `:1` with the extracted Mesa candidate, verified the live `xfwm4` candidate environment and compositor `true`, measured Adreno 825 GLX output, then confirmed stock llvmpipe fallback on the same display. The bounded GL workload rendered 600 frames in 5.0 seconds and ended at its planned seven-second timeout. I stopped the exact Ternuxx-owned session afterward; current status is stopped. The candidate remains extracted only; no package/system library was changed. Human-visible UI, sustained stability, broad app coverage, GPU inference, and persistent provider integration remain unverified. Full evidence is in [the workstation execution record](2026-10-20-workstation-qualification-execution.md).


## Authorized off-screen benchmark and fresh-install package follow-up — 2026-10-20

After the audit, the owner authorized benchmark installation and execution and later requested that glmark2, Xvfb, and xdotool be included on fresh Native installs. Installed glmark2 and Xvfb with its three dependencies; xdotool 4.20260303.1 was already installed. Candidate off-screen scenes scored 721 (730/711/727 FPS) versus stock llvmpipe score 113 (101/163/79 FPS). A separate surfaceless pbuffer workload measured 252.00 FPS at 1280x720 and 140.28 FPS at 1920x1080. glmark2 needed an X connection and labeled its surface windowed; candidate GLX on Xvfb failed while the stock virtual display selected llvmpipe. The source base package list and installation docs now include all three tools; no post-edit package preview/apply was run. Details and logs: [Native off-screen benchmark evidence](2026-10-20-native-offscreen-glmark2.md). The test session and temporary Xvfb were stopped. P3 remains in progress, P4 planned, release not ready.
