# Research & Evidence

Dated source links and evidence classifications for NativeTernux design decisions.

---

## Source Hierarchy (per owner brief)

1. **Primary:** Official upstream documentation
2. **Secondary:** Termux package metadata (pkg search results)
3. **Tertiary:** Read-only reference from existing ternux project
4. **Not used:** Forum posts, unverified claims

Each claim below includes: source URL, access date, and confidence level.

---

## 1. Termux:X11 Setup

**Source:** https://github.com/termux/termux-x11
**Accessed:** 2026-10-17
**Confidence:** verified

The upstream guide documents:
- The Android X server app (`termux-x11`)
- The companion `termux-x11` Termux package
- The `x11-repo` repository that provides it
- Launch command: `termux-x11 :1 -xstartup "dbus-launch --exit-with-session xfce4-session"`
- Fallback without `dbus-launch` for some setups

**Evidence classification:** verified — observed in upstream README.

---

## 2. PRoot-Distro Storage Layout

**Source:** https://github.com/termux/proot-distro
**Accessed:** 2026-10-17
**Confidence:** verified

PRoot rootfs lives under `$PREFIX/var/lib/proot-distro/`. This is the existing Ternux deployment path, NOT used by NativeTernux.

**Evidence classification:** verified — confirmed by inspecting `proot-distro list` output and directory structure.

---

## 3. GPU Device Nodes

**Observation date:** 2026-10-17
**Confidence:** verified (from adb session)

- `/dev/kgsl-3d0` — present (Adreno kernel interface)
- `/dev/dri/renderD128` — present
- GPU model: **Adreno 825** (from `cat /sys/class/kgsl/kgsl-3d0/gpu_model`)
- SoC: **SM8735** (Snapdragon platform)
- Device: **25053RT47C** (codename: onyx)

**Evidence classification:** verified — direct device read.

**Important distinction:** KGSL present in ADB context does NOT automatically mean it's accessible from within the Termux app sandbox. Native-Termux GPU path must be validated separately from PRoot-Ternux path.

---

## 4. Mesa Zink / Turnip — Native vs PRoot

**Observation date:** 2026-10-17
**Confidence:** mixed

**What we KNOW works (Proot):**
- `libvulkan_freedreno.so` exists in Debian proot at `/usr/lib/aarch64-linux-gnu/`
- `.cache/mesa_shader_cache_sf/` contains `zink` subdirectory — proof of prior Zink usage
- Blender renders successfully inside the proot session

**What we DON'T yet know (Native):**
- Whether `/data/data/com.termux/files/usr/lib/libvulkan_freedreno.so` in Termux is the same driver
- Whether `MESA_LOADER_DRIVER_OVERRIDE=zink` works without proot
- Whether Turnip ICD is properly registered in native Termux
- Whether glxinfo/vulkaninfo produce valid output in native Termux

**Evidence classification:** zink cache = observed; native acceleration = untested.

**Action required before claiming native GPU support:**
```bash
# Must run IN native Termux process (not proot):
export MESA_LOADER_DRIVER_OVERRIDE=zink
export GALLIUM_DRIVER=zink
glxinfo -B   # if available
vulkaninfo --summary  # already available in Termux
```

---

## 5. Available Termux Packages (Read-Only Survey)

**Date:** 2026-10-17
**Source:** `pkg search` against grimler.se mirror + termux-x11 repo
**Confidence:** verified (package index queried, not installed)

| Package | Repo | Status |
|---------|------|--------|
| xfce4-session | termux-x11 | Available |
| xfce4-panel | termux-x11 | Available |
| xfwm4 | termux-x11 | Available |
| thunar | termux-x11 | Available |
| xfce4-terminal | termux-x11 | Available |
| chromium | termux-x11 | Available |
| alacritty | termux-x11 | Available |
| kitty | termux-x11 | Available |
| pulseaudio | termux-stable | Already installed |
| dbus-x11 | termux-stable | Already installed |
| vulkaninfo | termux-stable | Already installed |
| glxinfo | termux-stable | NOT available |
| mesa-vulkan-icd-freedreno | termux-stable | Already installed (v26.2.4) |
| virglrenderer-android | termux-stable | Already installed |
| termux-x11 | termux-x11 | Already installed |
| termux-api | termux-stable | Already installed (v0.53.0) |
| termux-share | termux-api | Available (`/usr/bin/termux-share`) |

**Evidence classification:** verified — all from `pkg search` output against active mirrors.

---

## 6. TUR (Termux User Repository)

**Source:** https://github.com/termux-user-repository/tur
**Accessed:** 2026-10-17
**Confidence:** observed

TUR is configured in `/etc/apt/sources.list.d/tur.list`:
```
deb https://tur.kcubeterm.com tur-packages tur tur-on-device tur-continuous
```

**Decision:** Do NOT enable TUR by default. Verify package provenance before recommending any TUR package. Blender is available via TUR (`blender/tur-packages 1:3.6.23-13`).

**Evidence classification:** observed — confirmed from sources.list.d.

---

## 7. Existing Ternux Architecture (Read-Only Reference)

**Source:** https://github.com/soobujmiah/ternux
**Accessed:** 2026-10-17
**Confidence:** observed

Read-only inspection of:
- `bin/ternux` — CLI dispatch pattern (lazy-loaded lib modules)
- `lib/phases.sh` — 11-phase install with state tracking
- `lib/desktop.sh` — start/stop/restart lifecycle
- `install.sh` — standalone bootstrapper with remote fallback
- `docs/ARCHITECTURE.md` — PRoot+X11+Mesa stack diagram
- `docs/INSTALLATION.md` — requirements table

**Key patterns adopted for NativeTernux:**
- Same shebang: `#!/data/data/com.termux/files/usr/bin/bash`
- Same lazy-load module pattern (`_tnx_use()` → `_nt_use()`)
- Same command dispatch (`tnx_cmd_*` → `nt_cmd_*`)
- Same JSON output support (`--json` flag)
- Same version/help structure

**Evidence classification:** observed — read-only file inspection, no edits made.

---

## Unresolved Questions

| Question | Why it matters | How to resolve |
|----------|---------------|----------------|
| Does `libvulkan_freedreno.so` in Termux work natively? | Core GPU question | Run `vulkaninfo` in native Termux with `GALLIUM_DRIVER=zink` |
| Is `/dev/kgsl-3d0` accessible from Termux app sandbox? | Zink needs KGSL | Check `ls -la /dev/kgsl-3d0` from native Termux |
| Will XFCE4 from termux-x11 repo work with Termux:X11 display? | Desktop viability | Install + launch test (milestone 2) |
| Does pulseaudio work without proot? | Audio viability | Test `pulseaudio --start` in native Termux |
| Is TUR blender safe to recommend? | Optional workload | Verify signature, version, provenance |
