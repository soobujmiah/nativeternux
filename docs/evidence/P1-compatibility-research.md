# P1 compatibility research evidence

- Phase: `P1`
- Date: `2026-10-17`
- Commit: `2a06523a40acbaa451f97a44630646ef6ef0d430` (worktree includes the reviewed uncommitted documentation changes)
- Device/runtime: Termux 0.119.0-beta.3, Android 16, `aarch64`; Termux:X11 companion package installed. Inspection was read-only over SSH.
- Gate: PASS

## Acceptance criteria

- [x] Official Termux:X11 setup, Android minimum, app-plus-package requirement, XFCE recommendation, and display launch examples were checked against its upstream guide.
- [x] Current official Termux main and X11 repository indexes were read without refreshing them. Their signed `InRelease` dates and package candidates are recorded in `docs/RESEARCH.md`.
- [x] Candidate native XFCE, terminal, file-manager, and browser packages were checked for package name, version, repository, and architecture using `apt-cache policy`.
- [x] XFCE metapackage and explicit desktop-component dependency closures were reviewed using `apt-cache` and read-only `apt-get -s` simulations. The larger metapackage transaction and its related/recommended packages are documented; no size promise is made.
- [x] Native X11, DBus, PulseAudio, Termux:API, and file-sharing command presence/version were observed. Android add-on installation, API permissions, and a live native XFCE session are clearly marked unverified.
- [x] CPU/GPU/NPU research distinguishes physical silicon capability, supported SDK target, and process-level access. Android NNAPI deprecation and the unresolved SM8735/QAIRT mapping are recorded; NPU access is not claimed.
- [x] Native Wine/Hangover package candidates were checked read-only in the configured indexes: Termux:X11 candidate 11.16 for the umbrella/runtime/emulator packages; older TUR candidates are explicitly distinguished. No packages were installed.
- [x] Hangover upstream architecture and DXVK Vulkan 1.3 requirements were checked. Version-specific Termux issue reports were treated only as smoke-test risk evidence. Native Vulkan failure keeps native DXVK unverified; PRoot GPU evidence remains separate.
- [x] The device work was no-install research: package indexes were not refreshed, no package install/remove/upgrade or Termux setting change occurred, and no desktop lifecycle command was run.

## Evidence

- `docs/RESEARCH.md` §§8–13: recorded native GPU result, Ternux PRoot evidence boundary, current package index provenance/candidates, dependency simulations, Termux:X11 requirements, Android API boundary, and NPU runtime research.
- `docs/WINE-NATIVE.md`: per-app Wine/Hangover compatibility, CPU, graphics, NPU, prefix, and fallback gates.
- `docs/KNOWLEDGE-SYNC.md`: phase docs, generated state, and SKB knowledge return are separate; the status runtime and workflows were added after P1 completion, but CI and registry sync have not run.
- `docs/INSTALLATION.md`: installation remains unimplemented; exact transaction must be previewed again before consent.
- Device read-only commands: `apt-cache policy`, `apt-cache show`, `apt-cache depends`, `apt-get -s`, package command lookup, installed package query, and signed local index date inspection.
- Official primary references recorded in the research file: Termux:X11 guide, Termux:API project and filesystem guidance, Android NNAPI migration guide, Google LiteRT NPU docs, Qualcomm platform and QAIRT docs. WineHQ and Hangover upstream docs plus official Termux package metadata/issues were reviewed for the Windows runtime gate.
- No test suite was run. No device mutation was performed.

## Known limitations

- The Termux:X11 Android app package/signing source and Termux:API Android add-on/permissions were not inspected in this phase.
- Native XFCE has not been installed or launched. Dependency simulations do not prove UI behavior or final installed storage size.
- QAIRT's current public target table did not show an explicit SM8735/8s Gen 4 entry in this review. An NPU runtime callable from Termux or PRoot is not established.
- Hangover packages are only indexed, not installed. No Windows application, translated architecture, graphics backend, audio/input path, or NPU bridge has been qualified.
- Existing Ternux PRoot live renderer was not rerun; its setup remains separately documented and owner-reported/source-reviewed.
