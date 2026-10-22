# P4: Replay download throughput and bounded setup timeout

Date: 2026-10-22

Phase: `P4`
Phase: 

## Scope

Diagnosed the failed, exact-plan replay guest `ternuxx-replay-repro` (plan
`df36c23c6dbdcefb749518e55c78a3965cc280db3c3d5896f105ec02856e47c9`). The
failure affected only that replay alias. The existing `debian` rootfs remained
at device 65086, inode 3240111.

## Evidence

- The reviewed 54-package Debian workstation profile resolved to **761 MB of
  archives** and about **3,017 MB installed** in the replay guest.
- The prior full package transaction was bounded by a 3,600-second subprocess
  timeout. Its journal is `failed`; it showed repeated APT
  `Select has failed - select (38: Function not implemented)` acquisition
  errors before the timeout. No requested package was unpacked by that attempt.
- A single `ninja-build` APT install from the same pinned snapshot succeeded:
  130 kB fetched in 1 second (APT reported 238 kB/s), then unpacked and
  configured.
- A ten-package `apt-get download` probe completed under normal PRoot/seccomp.
  Therefore the select failure was not reproduced by small or bounded
  multi-package acquisition; its exact trigger remains unresolved.
- Repeated range probes showed highly variable throughput. On the same 130,056
  byte package, the configured snapshot endpoint returned about 140 kB/s and
  the Cloudflare-backed snapshot endpoint about 52 kB/s. A 1 MiB range of
  `libperl5.40` returned about 150 kB/s from the configured endpoint and 105
  kB/s from Cloudflare. Earlier measurements were lower still. The alternate
  endpoint was not adopted because these samples did not show an improvement.
- Debian describes Snapshot as its date/version-based archive. Its official
  status page says HTTP-layer rate limiting was planned; this observation alone
  does not prove that current device throughput is caused by that policy:
  [Debian Snapshot](https://snapshot.debian.org/).

## Change and verification

Raised the whole fresh-guest configuration subprocess timeout from one hour to
six hours, matching the measured archive volume and slow mobile-link samples
while keeping a finite upper bound. Added a regression assertion that the
fresh setup runner receives the configured bound.

- Focused suite: `python3 -m unittest tests.test_proot_fresh_setup -v` —
  **14/14 passed**.
- Native full suite: `bash scripts/repo_test.sh` — **849 passed, 1 skipped**,
  exit 0.
- `git diff --check` passed before evidence generation.
- This change does not claim to fix the unresolved APT `select (38)` error.
  The exact same-plan replay resume remains the runtime acceptance step.
