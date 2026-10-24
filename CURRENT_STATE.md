<!-- deterministic-state-bridge: ternuxx -->

# Current Ternuxx state

**Reviewed:** 2026-10-24. Ternuxx is a Native Termux-only Android workstation manager. The owner authorized full PRoot retirement and confirmed a backup; the backup was not independently inspected. All six installed guest containers, both PRoot packages, PRoot implementation routes, guest launchers, PRoot-only cached setup artifacts, and the final PRoot setup archive have been removed. Dated PRoot reports remain clearly identified as historical evidence.

## Live Native state

The verified runtime is Native Termux on Android 16/aarch64, Termux 0.119.0-beta.3. The Native supervisor, X11/XFCE desktop on `:1`, and Ternuxx-owned audio remain running. The `proot` and `proot-distro` commands and guest rootfs are absent. Ternuxx-managed SSH on 8023 is configured loopback-only/key-only; the separate owner-managed development SSH configuration on 8022 currently reports wildcard bind and password authentication enabled, while its listener ownership and external reachability are unknown. Shared/external storage was not accessed. See the [PRoot retirement audit](docs/evidence/2026-10-24-native-only-proot-removal-audit.md) and [Native profile report](docs/testing/reports/2026-10-24-native-profile-25053RT47C.md).

Doctor's latest read-only report has one warning: the Native SSH configuration has wildcard bind scope and password authentication enabled; listener ownership and external reachability are unknown. Two historical reboot checkpoints remain `NOT_READY` with automatic resume disabled. Neither SSH state nor reboot records were modified. Current graphics evidence proves OpenGL status, GLES context only, and Vulkan enumeration; it does not establish application presentation or GPU/NPU inference. See [P10 review](docs/evidence/2026-10-24-p10-internal-hardening-review.md).

## Project status

All required internal roadmap phases are resolved: ten completed and optional P9 skipped under the selected Native-only scope. The latest full Native Termux test harness passed 730 tests (including the Cron and read-only recovery inspection client-parity follow-ups). Repo-knowledge validation reports zero findings and the generated document inventory has zero broken local links. CLI, TUI, Web, and GTK expose the reviewed Native workflows through the shared service; the interactive `tx guides` path remains available. See [phase status](docs/PHASE-STATUS.md), [capability matrix](docs/architecture/CAPABILITY-MATRIX.md), and [repository audit](docs/audit/REPOSITORY-AUDIT.md).

## Release boundary

Internal phase completion does not mean public-release readiness. The repository has no selected LICENSE file, historical license statements need legal/provenance review, the one observed device is not a clean-install reproduction, boot delivery remains unqualified, and the SSH warning needs an owner-reviewed security decision. Do not publish a release artifact until these gates are resolved. See [legal/IP readiness](docs/readiness/LEGAL-IP.md), [security policy](SECURITY.md), and [known limitations](docs/testing/KNOWN-LIMITATIONS.md).

The checkout had a pre-existing Web reload/reconnect implementation before the Native-only migration; it was preserved and its evidence remains in [the Web session report](docs/evidence/2026-10-24-web-session-reload-reconnect.md).
