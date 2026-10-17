# NativeTernux

**বাংলা:** অ্যান্ড্রয়েড ফোনে PRoot বা Debian container ছাড়াই সরাসরি Termux-এ XFCE ডেস্কটপ চালাতে সাহায্য করে। কোনো root প্রয়োজন নেই।

---

**English:** Run an XFCE desktop on Android directly inside Termux — no PRoot, no Debian container, no root required.

## What is this?

NativeTernux is a Termux-native desktop project. Unlike [ternux](https://github.com/soobujmiah/ternux) (which uses PRoot + Debian), NativeTernux runs everything from Termux's own package repositories:

- **XFCE4 desktop** from the `termux-x11` repository
- **Chromium browser** from the `termux-x11` repository
- **GPU acceleration** via Mesa Zink + Turnip (Adreno Vulkan drivers already in Termux)
- **PulseAudio** for sound (already installed in your Termux)
- **Termux:X11** for the display server

## Current status: Milestone 1 — Scaffold

| Item | Status |
|------|--------|
| CLI skeleton | ✅ Complete |
| `check` command | ✅ Implemented |
| `info` command | ✅ Implemented |
| `doctor` command | ✅ Implemented |
| `help` / `guides` | ✅ Implemented |
| Package installation | ⏳ Milestone 2 (needs `--yes` consent) |
| Desktop launch | ⏳ Milestone 2 (requires packages) |
| GPU benchmarking | ⏳ Milestone 3 |
| Hybrid mode (Proot fallback) | ⏳ Milestone 4 |

## Quick start (after milestone 2)

```bash
# Check what's ready
nativeternux check

# See system info
nativeternux info

# Install required packages (one-time, requires --yes)
nativeternux install --yes

# Start the desktop
nativeternux start

# Stop the desktop
nativeternux stop
```

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design.

**Tier 1 — Native (current focus):**
```
Android → Termux packages → XFCE4 + Chromium + Zink/Turnip → Termux:X11
```

**Tier 2 — Proot (future):** Light Debian container for glibc-only tools (blender, ffmpeg, dev toolchains).

**Tier 3 — Hybrid (future):** Smart dispatch — native apps go to Termux, Linux-only apps go to Proot.

## License

PolyForm Noncommercial 1.0.0 plus the Ternux commercial-use addendum.
See [LICENSE](LICENSE) and [LICENSE-SCOPE.md](LICENSE-SCOPE.md).

NativeTernux is a separate project from [soobujmiah/ternux](https://github.com/soobujmiah/ternux). Both share the same license but have independent codebases and purposes.

## Repository

- **Source:** https://github.com/soobujmiah/nativeternux
- **Docs:** https://soobujmiah.github.io/nativeternux/ (future)
- **Issues:** https://github.com/soobujmiah/nativeternux/issues
