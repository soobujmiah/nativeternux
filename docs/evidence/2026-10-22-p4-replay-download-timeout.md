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

## Corrected conclusion after clean replay

A clean, separately previewed alias (`ternuxx-replay-p4-retry`) completed the
same 54-package setup against the same pinned Snapshot under the original
one-hour bound. APT reported **761 MB fetched in 4 minutes 7 seconds at
3,081 kB/s aggregate**; the full setup, locale/user creation, Turnip installation
and package-version recording all completed in under one hour. The earlier
six-hour timeout change was therefore reverted. The earlier failure's
`select (38)` trigger remains unexplained and was not reproduced in this clean
run; the larger archive size alone did not explain that failure.

The Cloudflare-backed Snapshot endpoint was not adopted. It served identical
range samples more slowly than the configured endpoint in this session.

## Clean replay and rollback evidence

- Plan: `d597a873f05cfb10feb60f1ded175c3c405fa7e730e283308f98016f97905b62`
- Journal/receipt: alias `ternuxx-replay-p4-retry`, Ternuxx install receipt
  recorded all requested packages, the package version inventory SHA-256 is
  `5835f69ca5f67f2d3e98e2e1a8237edb0c4447c4dece3b9423a44be79ba0c234`.
- Rootfs identity: device 65086, inode 4048696. The protected default Debian
  rootfs stayed device 65086, inode 3240111.
- `dpkg --audit` returned no findings; `apt-get check` passed; `en_US.utf8`
  exists and account `sbj` resolves as UID 10491.
- Zink/Turnip driver SHA-256 matches the manifest. A live
  `tx proot verify --distro ternuxx-replay-p4-retry --guest-user sbj --display :1 --backend zink`
  returned `complete`: X11/audio reachable, renderer
  `zink Vulkan 1.4(Adreno TM 825, MESA_TURNIP)`, GLX draw verified at 396 frames.
- Exact preview-bound retire and restore passed for the same alias and directory
  identity. Retirement reported `files_deleted=false`; restore returned the
  same container inode 4167750 and rootfs inode 4048696.
- The fresh-guest diagnostic path now accepts only `debian` or an exact
  receipt-verified `ternuxx-replay-*` alias. It verifies the private install
  receipt and device/inode before entering the guest. GUI/CLI diagnostic tests
  cover acceptance and fail-closed receipt checks.

## Tests and remaining status

- `python3 -m unittest tests.test_proot_diagnostics tests.test_management_service -v` —
  **71/71 passed**.
- Latest Native full suite: `bash scripts/repo_test.sh` — **852 passed,
  1 skipped**, exit 0.
- Document inventory and repo-knowledge checks remain to be rerun after this
  evidence correction.
- P4 is still in progress: broader provider/route configuration, Web
  mutation/client parity, Native-independence injection and full
  source/installed audit remain open. The first failed attempt's exact APT
  `select (38)` trigger remains unresolved.
