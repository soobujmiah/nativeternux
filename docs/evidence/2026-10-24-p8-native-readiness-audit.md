# P8 Native workflow readiness audit — 2026-10-24

Phase: `P8`

Gate: PASS

## Acceptance criteria

- Selected Native Termux workloads run through Native-owned runtime paths with explicit capability limits.
- Curated software actions and HOME-scoped name handoff share authorization and validation across CLI, TUI, Web, and GTK.
- PRoot remains removed and unavailable through supported routes.
- Recovery checkpoints remain preserved unless separately owner-authorized; no unsupported cold-boot or graphics claim is made.

## Evidence

The live Native Termux session remains running on display `:1`, owned by the `ternuxx-native` supervisor. `tx status --json` confirms XFCE/X11 live and reports GUI visibility unknown; no service was started, stopped, or restarted. `tx audio status` reports the Native PulseAudio server at `127.0.0.1:4713`, default `OpenSL_ES_sink`, and ownership matched. `tx mng graphics status` reports an OpenGL renderer and GLES context; GLES draw/presentation is explicitly unverified, and Vulkan is device-enumeration-only. These observations do not prove application-level display/audio output.

The owner authorized the project-completion work after reviewing the exact plans. The exact saved APT previews installed `htop` 3.5.3, `tmux` 3.8 with `utf8proc` 2.12.0, and `tree` 2.3.2 from the configured official `termux-main` mirror; each transaction matched its simulation, with zero upgrades/removals. `dpkg --audit` and `apt-get check` returned clean. `tx app list` now reports all three as installed at the indexed versions. `htop --version` returned 3.5.3; a disposable PTY launch exited cleanly after `q`. A tmux session was created/listed/stopped using a unique temporary socket, and `tree` listed a temporary nested file fixture under `$HOME`; fixture state was cleaned. No live package processes or test sessions remain.

The CPU inference runtime and pinned model are present; an earlier P6 direct Native CPU workload returned `NATIVE_CPU_OK`. This P8 pass relies on that dated evidence rather than repeating the model run. The curated `directory-tree` app now offers a bounded, read-only HOME path handoff through the shared service, CLI, TUI, Web, and GTK. It lists directory entries or a single file name only; it never reads file contents, follows symlinks, or accesses Android shared storage. Live CLI checks listed a disposable file fixture and rejected an outside-HOME path, a parent traversal, and a symlink. The operation is covered by the full suite; Web JavaScript syntax and GTK C syntax checks also pass. No GUI visual click-through is claimed.

Read-only log inventory reports the Native desktop, Cron scheduler, and management API audit log sources available. `tx reboot status --json` exposed two preserved pre-existing reboot checkpoints (`TERN-20261021-RB07` and `TERN-20261021-RB08`) in `boot_observed` / `NOT_READY`; `automatic_resume` is false. Their historical baseline includes the retired `proot_independent` check, which made the current status parser reject the records. The parser now accepts that check only while reading existing checkpoints; newly prepared checkpoints still reject it. A fixture test proves the compatibility boundary, and live status now reads both records without rewriting or resolving them. No reboot or recovery mutation was performed.

## Scope and limits

The full repository suite passes: 714 tests in 100.844 seconds. `python3 -m tools.repo_knowledge verify` reports zero findings. Live Native status confirms XFCE/X11 remains running on `:1`, audio ownership matches, OpenGL is verified, GLES is context-only, and Vulkan is enumeration-only. `htop` 3.5.3, `tmux` 3.8, and `tree` 2.3.2 are installed at their indexed candidates; `dpkg --audit` and `apt-get check` are clean. The `proot` and `proot-distro` commands and PRoot-Distro rootfs are absent. PRoot routes fail closed with `feature_removed`.

P8 is complete for the selected Native-only product. The two historical reboot checkpoints remain `NOT_READY` with automatic resume disabled and were preserved; this gate does not claim a new cold-boot test or authorize recovery mutation. Shared-storage access remains outside scope. Do not infer graphics rendering or application presentation from status metadata alone.
