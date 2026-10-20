# Shared Native and Debian graphics management — 2026-10-20

Phase: `P6` (preparatory implementation; phase remains planned)

## Evidence

## Scope and implementation

The graphics inventory, verification, and Native backend preference now use Ternuxx's shared management service (`graphics.provider.status`, `graphics.provider.verify`, and `graphics.provider.select`). CLI, interactive TUI, Web, and GTK clients call these typed operations. Native and Debian results remain separate providers and libc environments.

The Native selector accepts only the already qualified extracted KGSL/Freedreno candidate or the stock system stack. It writes a private state file atomically; the selection applies to future Ternuxx desktop starts. Those starts carry a Turnip ICD manifest only when its library path matches the qualified candidate. Vulkan device enumeration is reported separately and is not called a rendered Vulkan workload.

The Debian provider runs the existing fixed read-only guest verifier. It does not install packages or alter guest configuration. The existing Zink/Turnip path already passed verification, so no Debian config change was needed in this continuation.

## Device evidence

- Target runtime: Native Termux on Android 16, aarch64; Termux 0.119.0-beta.3. Checkout branch `main`, starting HEAD `845c4e22dff6f88a304e2a505e82b1690d6aac2b`; pre-existing uncommitted work and owner artifacts were preserved.
- Current native display `:1`: `glxinfo -B` through the shared status operation reported `Adreno (TM) 825`, `Accelerated: yes`. Native Mesa candidate: 26.3.0-devel, commit `98f3d6229d`; stock Termux Mesa remains installed separately.
- Shared Native verification ran `glmark2 --off-screen` with `build`, `texture`, and `shading` scenes at 1280×720, four seconds each, `--frame-end finish`, `--swap-mode immediate`. It reported `GL_RENDERER: Adreno (TM) 825`, score 608, `render_verified: true`. This is a synthetic off-screen-mode benchmark through the current X11-backed Termux workload path; it is not presented-display FPS or a long thermal test.
- Shared Native status found the isolated Turnip ICD and enumerated `Adreno (TM) 825`. It explicitly reports `device-enumeration-only; no draw verified`. Native Vulkan rendering remains unverified.
- Shared Debian status entered the existing Debian guest using its fixed read-only verifier on display `:1`: X11 reachable, PulseAudio control endpoint reachable, renderer `zink Vulkan 1.4(Adreno (TM) 825 (MESA_TURNIP))`, status `complete`. The verifier reported `packages_changed: false`, `guest_write_command_invoked: false`, and no host or guest services started or stopped. Audible output is not established by socket reachability.
- Native stock `llvmpipe` and `softpipe`, plus candidate Zink over Turnip, have separate earlier device evidence in [native continuation audit](2026-10-20-native-continuation-audit.md) and [off-screen benchmark](2026-10-20-native-offscreen-glmark2.md). Those results remain workload-specific. VirGL remains unqualified; its recorded service was stale and no native `virpipe` DRI driver was found.
- After the owner explicitly allowed restarting only the managed GUI, `tx --json restart` restarted Ternuxx display `:1`; Codex, SSH 8022, and the Termux app session remained available. The desktop returned to `running` with supervisor, X11, and XFCE live. Read-only `/proc` inspection confirmed the XFCE environment contains `VK_ICD_FILENAMES` pointing to `$TERNUXX_STATE_DIR/graphics/providers/native-mesa-0219ff84/freedreno-isolated.json`. Post-restart Native status still reports Adreno (TM) 825 / accelerated, and shared off-screen OpenGL verification rendered successfully (score 608). The API still labels Vulkan as enumeration-only. A fresh Debian status remained `complete` with Zink/Turnip on Adreno 825; no guest writes, package changes, or service lifecycle changes occurred.

## Interfaces and checks

- CLI: `tx mng graphics status native|debian`, `tx mng graphics verify native|debian opengl|gles|vulkan [:N]`, and `tx mng graphics select native kgsl-freedreno|system`. The older `tx graphics native status|enable|disable` entry delegates to the same management operations and only accepts the qualified candidate.
- TUI offers status, OpenGL/GLES/Vulkan verification, and a confirmed Native selection.
- Web exposes the same operations through its authenticated local session, with confirmation and idempotency key for selection.
- GTK Management Center exposes provider status, OpenGL verification, and a confirmation dialog for Native selection. Its binary was rebuilt and installed from this checkout; `--self-check` reports GTK 4.24.1. Prior installed binary, launcher, and identity are retained in the private rollback directory `~/.local/share/ternuxx/rollback/management-center-pre-select-20261020`.
- Focused desktop and management tests passed 67/67; management service/catalog/session/HTTP runtime tests passed 65/65; graphics selector tests passed 4/4; GTK C source passed `clang -fsyntax-only`; shell syntax and Python compilation checks passed.
- Full repository suite passed 566/566 in 90.379 seconds. GTK source passed `clang -fsyntax-only`; `git diff --check` passed. The desktop restart and post-restart status/render probes above also passed.

## Limits and rollback

This is an integrated provider inventory, workload probe, and Native preference selector; automatic per-application fallback policy, per-workload API enforcement, crash-journaled selector rollback, Native Vulkan draw verification, and full manual Web/TUI/GTK interaction acceptance remain incomplete. The Debian guest stays under its existing Ternux configuration and is not managed for writes by this selector.

To switch future Native desktop starts back to the system graphics stack, run `tx mng graphics select native system`. To restore the verified KGSL candidate, run `tx mng graphics select native kgsl-freedreno`. Either choice leaves the currently running desktop untouched. The prior GTK installation can be restored from the private rollback directory above using the owner's normal maintenance workflow.


## Private provider-state relocation follow-up

To remove a checkout-path dependency, the extracted candidate was copied into `$TERNUXX_STATE_DIR/graphics/providers/native-mesa-0219ff84/`; SHA-256 for `libdril_dri.so` and `libvulkan_freedreno.so` matched the source copy. The ICD manifest was rewritten to the private-state library path. The saved selection now points there; selecting the candidate validates four pinned file hashes from `config/graphics/native-kgsl.json`. `tx mng graphics status native` still reports Adreno 825 / accelerated GLX and Turnip device enumeration. A focused test for OpenGL ES API labeling passes; the shared manager now reports GLES unavailable until a dedicated runner is provided. The already-running GUI was not restarted, so it retains the prior inherited checkout candidate path until its next managed start. No clean-install provider installer exists yet.

The repository suite passed 572/572 after adding PRoot adoption and graphics profile validation coverage. `python3 -m tools.repo_knowledge verify` returned 0 findings.
