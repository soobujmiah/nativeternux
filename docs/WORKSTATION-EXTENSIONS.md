# Workstation additions to consider

These ideas could make the pocket workstation more useful beyond features already in [my product vision](PRODUCT-VISION.md) and [the delivery roadmap](ROADMAP.md). They are proposals for owner review, not approved release promises. An idea should enter the roadmap only with a clear user need, a safe ownership boundary, and a testable acceptance gate.

| Priority | Idea | Why it may help | Cost or risk | Suggested gate |
|---|---|---|---|---|
| High | **Docked-workstation profile** for keyboard, mouse, external monitor, density, and window layout | Makes the phone practical at a desk and keeps the UI usable across handheld and larger displays | Android display/input behavior varies by device; desktop-mode APIs are not guaranteed | Test input, resolution changes, rotation, suspend/resume, and Termux:X11 visibility on the target device |
| High | **Project workspaces** with private Native roots, environment notes, and selected handoff files | Gives Native projects a predictable home and makes selected file handoff clear | Path permissions and shared-storage boundaries; avoid syncing secrets | Workspace roots private by default; every bind/share is visible and revocable |
| High | **Portable backup/export and migration** for Ternuxx configuration and workspace manifests | Helps recover from app reinstall/device replacement and supports safer upgrades | Archives can contain secrets or become large; restore can overwrite user files | Manifest, checksums, schema migration, preview, rollback snapshot, and path confinement pass fixture tests |
| Medium | **Offline-ready catalog and package plan** | Useful with weak connectivity and prevents website snapshots being mistaken for current package state | Package metadata/downloads go stale; cached packages need provenance | Label cached metadata with retrieval time; revalidate source/signature and availability before install |
| Medium | **Workload queue with pause/resume where supported** | Makes long renders, builds, and model jobs easier to manage on a phone | Android may stop background work; arbitrary programs may not be resumable | Per-job owner, manual continuation path, bounded retry, checkpoint support, explicit cancellation |
| Medium | **Measured benchmark notebook** for CPU/GPU/NPU per workload | Enables comparisons without vague speed claims | Temperature, battery, OS, and background activity affect results | Record versions, provider, selected backend, correctness, warm/cold timing, memory, thermal state, repeatability |
| Medium | **Input and accessibility presets** for touch, keyboard, mouse, screen scaling, and larger text | Makes the desktop usable without one particular hardware setup | Desktop environments and Android accessibility settings have different owners | Change only Ternuxx user-level settings; provide preview and reset |
| Medium | **Bangla and English localization** for CLI/GUI labels, error guidance, and website help | Makes the workstation easier to operate in the owner's preferred language while keeping technical identifiers searchable | Font shaping, terminal width, translations, and untranslated package output need careful handling | Test Bangla shaping/line wrapping in Termux:X11 and terminal-only/SSH sessions; retain stable English finding IDs and JSON keys |
| Later | **Local network trust profiles** for SSH and remote access | Clarifies phone-as-server use across loopback, trusted LAN, and temporary access | Listener exposure, changing networks, key management, and Android background limits | Off by default; show bind/port/authentication, test only user-selected endpoints, offer owned-service shutdown |
| Later | **Workspace automation recipes** for repeatable build/render/inference jobs | Makes the device a repeatable workstation instead of a collection of commands | Recipes can execute arbitrary code and leak environment values | Show argv, paths, environment, provider, and side effects before first run |

## Suggested order

1. Add docked/input behavior and project-workspace boundaries to product design before polishing the GUI.
2. Deliver ownership, journaling, backup, and recovery before resumable queues or automation recipes.
3. Build offline catalog data and the benchmark notebook after provider, installer, and capability records have stable schemas.
4. Consider remote-access refinements after Native SSH services are safe and observable.

## Design rules

- The CLI remains useful without the GUI, optional APKs, Shizuku, root access, or network access.
- Android-owned behavior stays behind supported Termux APIs or explicit user actions. An X11 app must not be treated as a way around Android activity/background policy.
- Users see exact target paths, package/source, and workload backend before state-changing operations.
- A dependency fallback reduces capability visibly; it does not silently switch provider, backend, display, or security mode.
- Ternuxx keeps its own private state and never manages an external Linux root filesystem.
