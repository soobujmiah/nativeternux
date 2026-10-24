# P10 internal hardening and support review — 2026-10-24

Phase: `P10`

Gate: PASS

## Acceptance criteria

- The selected Native-only implementation has a complete repository test and contract run, with current limitations written down.
- Native app actions and management clients use the shared service, authorization and safe HOME-only handoff boundaries.
- Current project/runtime state is refreshed without disturbing live Termux services or unresolved recovery records.
- Public release is clearly separated from internal completion and remains blocked while legal, provenance, reproducibility and security issues remain open.

## Evidence

The complete `bash scripts/repo_test.sh` run passed 714 tests in 100.844 seconds. The CLI help contract passes, shell syntax passes, strict README state-bridge validation passes, and `python3 -m tools.repo_knowledge verify` reports zero findings. The document inventory reports zero broken local links and current path/hash coverage. GTK C syntax and Web JavaScript syntax checks passed during P8 implementation validation.

Live Native checks show Ternuxx-owned XFCE/X11 running on display `:1`; Native audio is running with matched ownership. Graphics evidence remains bounded: OpenGL verified, GLES context verified without draw/presentation, Vulkan enumeration only. Doctor is read-only and returned `warning` with one warning: Native SSH is wildcard-bound with password authentication enabled, while listener owner and external reachability are unknown. No SSH settings or service state were changed. Two older reboot checkpoints remain `NOT_READY`, with automatic resume disabled; no reboot or recovery mutation occurred. PRoot packages, executables, guest rootfs, implementation routes and management operations remain removed or fail closed. The three curated Native apps are installed at their indexed versions, and `dpkg --audit` / `apt-get check` are clean.

Git object-store review found 113 dangling object symlinks pointing into the removed Debian guest rootfs; the target files were already absent. The symlink entries were quarantined, reachable objects were restored from GitHub, and final `git fsck --full --no-reflogs` reported only dangling historical objects, with no missing/corrupt objects or garbage. No branch ref changed during repair.

The installed-device verification is not a clean-device reproduction. Android boot delivery remains unqualified, broad device support is unverified, graphics/NPU workload acceleration is not established, and network exposure of the separate 8022 development SSH channel is not rechecked here. No release SBOM exists. The repository has no selected LICENSE file, historic licensing statements are ambiguous, and source/provenance review is incomplete. These are explicit public-release blockers in [legal/IP readiness](../readiness/LEGAL-IP.md), [third-party notices](../readiness/THIRD-PARTY-NOTICES.md), and [security limits](../../SECURITY.md).

This gate closes internal Native-only hardening and support documentation. It does not authorize or claim a public release. Resolve the license/provenance decision, security posture, clean-device reproduction and supported-profile acceptance before publishing a release artifact.
