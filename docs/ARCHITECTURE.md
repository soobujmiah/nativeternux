# Architecture

NativeTernux architecture: three tiers, each more capable but more complex.

---

## Tier 1 — Native (Current Focus)

```
┌─────────────────────────────────────────────────────────┐
│ Android                                                  │
│                                                          │
│  Termux:X11 app  ◄──── X11 display ────┐               │
│                                          │               │
│  Termux (native)                         │               │
│  ├── xfce4-session                      │               │
│  ├── xfce4-panel                        │               │
│  ├── xfwm4                              │               │
│  ├── thunar                             │               │
│  ├── xfce4-terminal                     │               │
│  ├── pulseaudio                         │               │
│  ├── dbus-daemon                        │               │
│  ├── mesa (Zink + Turnip)               │               │
│  └── chromium (optional)                │               │
│                                          │               │
│  Adreno 825 (SM8735) ◄── Zink/Turnip path│              │
└─────────────────────────────────────────────────────────┘
```

**Key difference from ternux:** No PRoot, no Debian, no proot-distro. Everything runs in the Termux app sandbox directly.

**Advantages:**
- No 19 GB proot rootfs overhead
- No ptrace-based compatibility layer
- Direct access to Android hardware (KGSL, DRM)
- Faster startup (no container init)
- Simpler uninstall (just `pkg uninstall` + delete `~/.local/share/nativeternux`)

**Limitations:**
- musl libc (not glibc) — some Linux-only binaries won't run
- No systemd — service management is manual
- Package ecosystem smaller than Debian
- Some apps compiled for glibc won't work

---

## Tier 2 — Proot (Future)

Lightweight Debian container for glibc-only workloads.

```
┌─────────────────────────────────────────────────────────┐
│ Tier 1 (Native) +                                      │
│                                                          │
│  proot-distro (separate named rootfs)                  │
│  ├── debian userland (glibc)                          │
│  ├── blender (if needed)                               │
│  └── dev toolchains (llvm, rust, etc.)                 │
│                                                          │
│  Shared: /sdcard, network, display (:0)                │
└─────────────────────────────────────────────────────────┘
```

**When to use:** Only when a specific app requires glibc or a Linux-specific binary.

**Rootfs:** Named `nativeternux-debian` (separate from existing `debian` proot). Minimal package manifest — only what's needed, not the full 1511-package current setup.

**Target size:** ~3-4 GB (vs current 19 GB).

---

## Tier 3 — Hybrid (Future)

Smart dispatch between native and proot based on app requirements.

```
nativeternux start --hybrid
        │
        ├──→ Native path (Termux packages)
        │      ├── terminal (alacritty/kitty/xfce4-terminal)
        │      ├── file manager (thunar)
        │      ├── browser (chromium)
        │      ├── CLI tools (git, python, node, cargo)
        │      └── AI agents (codex, claude, hermes)
        │
        └──→ Proot path (lightweight debian)
               ├── blender
               ├── ffmpeg (if native build fails)
               └── any glibc-only workload
```

**Dispatch logic:**
- Check if package exists in Termux → use native
- Check if app requires glibc → route to proot
- Shared `/sdcard`, shared display, shared network
- Explicit per-path file sharing (no blanket `~/.ssh` or `~/.config` mount)

---

## Display & Audio Pipeline

Both tiers share the same display/audio path:

```
Application (OpenGL/Vulkan)
       │
       ▼
    Mesa (Zink or Turnip)
       │
       ▼
    X11 protocol
       │
       ▼
    Termux:X11 app  ◄─── socket :N
       │
       ▼
    Android SurfaceFlinger  (Adreno 825)
```

```
Application (PulseAudio)
       │
       ▼
    pulseaudio (Termux-native)
       │
       ▼
    Android audio HAL
```

---

## Filesystem Layout

```
~/nativeternux/           ← This repository (source of truth)
~/bin/nativeternux        ← CLI symlink (future: after install)
~/.local/share/nativeternux/
  ├── lib/                ← Runtime libraries (copied from repo)
  ├── state/              ← Session state (pids, display number)
  └── logs/               ← Runtime logs
~/.config/nativeternux/   ← User config (future)
```

No shared paths with existing ternux/debian by default.
