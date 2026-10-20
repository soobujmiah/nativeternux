# Native off-screen graphics benchmark — 2026-10-20

## Setup and workload

Ran in Native Termux checkout $HOME/ternuxx over SSH 8022. Installed configured Termux X11 repository package glmark2 version 2023.01-3 after previewing its transaction: 6,851,468 bytes downloaded, 11.5 MB additional installed size, and no new dependencies. The Mesa candidate remains extracted only; no Mesa or graphics driver package was installed.

The Termux glmark2 build could not initialize its canvas without an X server, so the Ternuxx-owned test session on :1 was started with the extracted candidate environment. Ran glmark2 --off-screen --size 1280x720 --frame-end finish --swap-mode immediate for build, texture, and shading scenes, four seconds each. Repeated with candidate variables removed. Stopped the exact Ternuxx session afterward; final tx gui status --json says stopped, supervisor/X11/XFCE absent. No Debian guest was entered.

## glmark2 results

| Renderer | build FPS | texture FPS | shading FPS | glmark2 score |
|---|---:|---:|---:|---:|
| Candidate Freedreno, Adreno 825, Mesa 26.3.0-devel 98f3d6229d | 730 | 711 | 727 | 721 |
| Stock Mesa 26.2.5, llvmpipe LLVM 21.1.8 | 101 | 163 | 79 | 113 |

Candidate selected GL_VENDOR=freedreno, GL_RENDERER=Adreno (TM) 825. Fallback selected GL_VENDOR=Mesa, GL_RENDERER=llvmpipe (LLVM 21.1.8, 128 bits). Raw logs: graphics/native-mesa-0219ff84/glmark2-candidate-offscreen-20261020.log and graphics/native-mesa-0219ff84/glmark2-stock-offscreen-20261020.log.

## Separate surfaceless EGL result

A GLES 3 pbuffer workload explicitly used EGL_PLATFORM_SURFACELESS_MESA, a 1280x720 surface, a fixed 48-iteration full-screen fragment shader, and glFinish() after each frame. Candidate result: 2,520 frames in 10.000 seconds = 252.00 frames/sec. At 1920x1080 it rendered 1,403 frames in 10.002 seconds = 140.28 frames/sec. The GLES source can be built with `clang -O2 -Wall -Wextra -o offscreen-gles graphics/native-mesa-0219ff84/offscreen-gles.c -lEGL -lGLESv2`. Source and raw logs: graphics/native-mesa-0219ff84/offscreen-gles.c, graphics/native-mesa-0219ff84/offscreen-gles-20261020.log, and graphics/native-mesa-0219ff84/offscreen-gles-1920x1080-20261020.log. This synthetic workload is not an application or displayed UI FPS claim.

## Xvfb follow-up

Installed Termux X11 repository package xorg-server-xvfb version 21.1.25-1 after previewing the transaction: 692 KB total download and 2.154 MB additional installed size, including three new dependencies (libfontenc, libxfont2, xorg-protocol-txt). A temporary local-only Xvfb display :99 was started with TCP disabled. Stock glxinfo -B exited 0 and identified llvmpipe / Accelerated: no. Under the extracted candidate environment, glxinfo -B exited 1 and reported the X connection broken; candidate GLX did not qualify on Xvfb. The temporary Xvfb process was stopped after each probe. Logs: graphics/native-mesa-0219ff84/xvfb-20261020.log, graphics/native-mesa-0219ff84/glxinfo-stock-xvfb-20261020.log, and graphics/native-mesa-0219ff84/glxinfo-candidate-xvfb-20261020.log.

## Limits and interpretation

The Termux glmark2 binary needed a reachable Native X display for its canvas despite --off-screen; it printed Surface Size: 1280x720 windowed. Treat these as glmark2 off-screen-mode results through an X11/GLX canvas, not as a display-independent surfaceless-only benchmark. The stock run warned GLX swap-control extensions were unavailable and the swap interval could not be set; --frame-end finish and --swap-mode immediate were requested, but the warning remains a caveat. Candidate scene rates exceed 120 FPS, so this workload was not capped at 120 FPS. This does not measure the display's presented FPS, maximum GPU capacity, long-duration thermal behavior, other app performance, inference, or release readiness.

The Mesa candidate remains uninstalled. glmark2 and xorg-server-xvfb remain installed by owner authorization. Stock llvmpipe remains available. P3 remains in_progress, P4 planned, overall release NOT RELEASE-READY.

## Fresh-install package selection

Owner requested that glmark2, Xvfb, and xdotool be included on fresh Native Ternuxx installs. The base package list now includes glmark2, xorg-server-xvfb, and xdotool so the preview-first installer resolves them from configured official Termux repositories. On this device glmark2 and Xvfb were installed through their previewed package transactions; xdotool 4.20260303.1 was already installed, so APT preview showed no change for it. The package list is updated, but no fresh install or apply was run.


The text logs in `graphics/native-mesa-0219ff84/` were copied from the device qualification scratch; only trailing whitespace and line endings were normalized. Measurement values and output lines are preserved. The candidate binaries themselves are not committed. The provenance is the community draft [lfdevs/termux-packages PR #25](https://github.com/lfdevs/termux-packages/pull/25), source commit `0219ff84b372c9d38aad4e40f448c20ec3d1588e`, workflow run `36377469447`; this is not an official Termux release and has no stable artifact URL in the profile.
