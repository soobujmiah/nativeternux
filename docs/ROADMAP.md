# Roadmap

Milestone gates and unresolved questions for NativeTernux.

---

## Milestone 1 — Scaffold ✅ (In Progress)

**Goal:** CLI skeleton, documentation, read-only research.

Done:
- [x] GitHub repo created (`soobujmiah/nativeternux`, private)
- [x] `bin/nativeternux` CLI with dispatch pattern
- [x] `lib/core.sh` — logging, JSON, state, requirement checks
- [x] `lib/help.sh` — help text for all commands
- [x] `lib/doctor.sh` — `check` and `doctor` commands
- [x] `lib/info.sh` — `info` command
- [x] `lib/desktop.sh` — `start`/`stop`/`restart`/`status` (stub)
- [x] `lib/phases.sh` — `install` stub (requires `--yes`)
- [x] `README.md` (English)
- [x] `bn/README.md` (Bangla)
- [x] `docs/RESEARCH.md` — dated source links + evidence
- [x] `docs/ARCHITECTURE.md` — three-tier design
- [x] `docs/ROADMAP.md` — this file

Not done:
- [ ] `docs/INSTALLATION.md` — will be written after milestone 2
- [ ] `LICENSE` — needs owner decision on license

---

## Milestone 2 — Functional Desktop 🔲

**Gate:** `nativeternux start` launches a working XFCE session.

Required:
- [ ] Package installation command (`nativeternux install --yes`)
  - Installs: `xfce4-session xfce4-panel xfwm4 thunar xfce4-terminal pulseaudio dbus-x11`
  - Uses `pkg install` (Termux native, no proot)
  - Shows preview before installing, requires `--yes`
- [ ] Real `start` implementation
  - Finds free display number
  - Launches `termux-x11 :N -ac &`
  - Waits for socket
  - Starts pulseaudio + dbus + xfce4-session
  - Tracks PIDs for clean stop
- [ ] Real `stop` implementation
  - Kills only tracked PIDs (no blanket pkill)
  - Cleans only its own socket files
- [ ] Device test: verify XFCE appears in Termux:X11

Unresolved:
- [ ] Does `pkg install xfce4-session` pull in all GTK3 deps correctly?
- [ ] Does `termux-x11 :1 -xstartup "dbus-launch --exit-with-session xfce4-session"` work without modification?
- [ ] PulseAudio: does it start correctly in native Termux without proot?

---

## Milestone 3 — GPU Verification 🔲

**Gate:** Native GPU acceleration proven, not just inferred.

Required:
- [ ] Run `vulkaninfo --summary` in native Termux with `GALLIUM_DRIVER=zink`
- [ ] Run `glxinfo -B` (need to install `mesa-utils` or equivalent)
- [ ] Launch a simple OpenGL demo (e.g., `glxgears` if available, or a small Vulkan triangle)
- [ ] Document renderer string and confirm it's Adreno, not llvmpipe

Unresolved:
- [ ] Is `/dev/kgsl-3d0` accessible from the Termux app sandbox?
- [ ] Does `libvulkan_freedreno.so` in Termux (`/data/data/com.termux/files/usr/lib/`) work without the proot binding trick?
- [ ] What environment variables are needed for native Zink?

---

## Milestone 4 — Optional Workloads 🔲

**Gate:** Common apps available in native mode.

- [ ] Chromium browser (`pkg install chromium`)
- [ ] Alacritty terminal (`pkg install alacritty`)
- [ ] Micro editor (`pkg install micro`)
- [ ] File transfer via `termux-share`

---

## Milestone 5 — Proot Fallback (Optional) 🔲

**Gate:** Lightweight Debian for glibc-only apps.

- [ ] Create named proot rootfs `nativeternux-debian`
- [ ] Minimal package manifest (blender, ffmpeg, dev toolchains)
- [ ] Target size: ~3-4 GB
- [ ] `nativeternux start --proot` launches in lightweight proot

---

## Milestone 6 — Hybrid Dispatch 🔲

**Gate:** Automatic routing between native and proot.

- [ ] `nativeternux start --hybrid`
- [ ] App registry: which apps go native, which go proot
- [ ] Explicit per-path file sharing (no blanket mounts)

---

## Long-Term Vision

- Website with interactive install guide
- Device compatibility matrix (which phones work, which don't)
- Community-contributed device profiles
- Performance benchmarks (native vs proot vs native-with-proot-fallback)
