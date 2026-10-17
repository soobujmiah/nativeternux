# NativeTernux — Installation

> **Warning:** Package installation is NOT implemented in milestone 1.
> This document describes the intended flow.

## Prerequisites

1. **Termux** from F-Droid or GitHub (not Play Store)
   - Version: 0.119.0-beta.3 or newer
2. **Termux:X11** app installed
   - Version: 1.03.01 or newer
   - https://github.com/termux/termux-x11/releases
3. **termux-x11** package enabled
   ```bash
   pkg install termux-x11
   ```
   (This enables the `x11` repository)
4. **At least 2 GB free** on `/data`

## Check readiness

```bash
nativeternux check
```

This reports what's installed and what's missing. No changes are made.

## Install packages

```bash
nativeternux install --yes
```

This will install (via `pkg install`):
- `xfce4-session` — XFCE session manager
- `xfce4-panel` — XFCE panel
- `xfwm4` — XFCE window manager
- `thunar` — XFCE file manager
- `xfce4-terminal` — XFCE terminal emulator
- `pulseaudio` — audio server (if not already present)
- `dbus-x11` — D-Bus X11 integration (if not already present)

**No PRoot packages are touched.** No system files are modified.
No existing Ternux/debian environment is affected.

## Start the desktop

```bash
nativeternux start
```

This will:
1. Find a free X11 display number
2. Launch Termux:X11 on that display
3. Wait for the X11 socket
4. Start PulseAudio (if not running)
5. Launch XFCE4 via dbus

**Termux:X11 app** will open automatically showing the desktop.

## Stop the desktop

```bash
nativeternux stop
```

Stops only the processes that nativeternux started.

## Uninstall

```bash
pkg uninstall xfce4-session xfce4-panel xfwm4 thunar xfce4-terminal
rm -rf ~/.local/share/nativeternux
```

No Proot container is created, so nothing to clean there.
