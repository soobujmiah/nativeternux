# P3 Cron boot concurrency and serial roadmap review — 2026-10-21

Phase: `P3`

## Scope and phase order

Reviewed the current product vision, manifest/classification, security boundary, AI instructions, phase-state, roadmap exit gates, current handoff, and latest 2026-10-21 Cron/boot evidence.

The roadmap has eleven serial phases, P0–P10. P0–P2 are recorded complete; P3 is the sole active phase; P4–P10 remain planned. The dependencies are correctly ordered: P3 ownership/recovery → P4 existing Debian provider → P5 supported profile → P6 workload graphics/fallback → P7 software catalog → P8 end-to-end Hybrid workflows → optional P9 only for a demonstrated, owner-approved gap → P10 hardening/release. No later phase should be marked complete or implemented ahead of its prerequisites. P9 is the only optional phase and has a reviewed skip transition. P10 correctly keeps public release separate from internal completion and blocks distribution on license/provenance.

The plan already includes the required work. Remaining phase-sized gaps are accurately named: P3 ownership, concurrency/recovery, and an separately authorized boot window; P4 nested `:2` draw/presentation and disposable guest replay; P5 exact supported profile; P6 application-level API-aware selection, fallback and reproducibility; P7 package lifecycle; P8 accepted end-to-end workflows; P9 gap decision; P10 support, provenance, license, and release review. The roadmap does not promise general NPU support or arbitrary distro/device coverage.

## P3 implementation

The opt-in Termux:Boot Cron entrypoint manager did not share its existing `cron/boot/entry.lock` with the entrypoint process. Concurrent enable/disable and a boot-time Cron start could therefore inspect and mutate the exact script while the entrypoint was running.

The manager now acquires that same private lock before rechecking the exact preview and applying the file operation. The lock is created/validated beneath the resolved private Ternuxx state tree with no-follow open, same-user regular-file checks, and mode 0600. A non-confirmed apply still returns a preview without creating state or taking the lock. The boot script and manager now serialize against one lock file.

## Verification and limits

- Native focused Termux:Boot Cron suite: 16/16 passed, including a fixture that holds the entrypoint lock and verifies the manager waits without changing the target.
- The Termux:Boot entrypoint was exercised only by its existing isolated safe-test fixture; no live boot script or device startup was invoked for this increment.
- No live boot file, scheduler, service, SSH, GUI, Debian guest, or boot configuration was changed.
- No reboot or Termux/Codex session close occurred.
- Cold-boot delivery, Android background policy, and owner-gated device boot acceptance remain unverified and keep P3 open.

Next P3 action: continue the remaining ownership/recovery checks that do not require a reboot. Cold-boot qualification remains a separate owner-approved device window. P4 stays planned until P3 passes.

## Evidence

- Focused fixture test: `tests/test_termux_boot_cron.py` (16/16).
- Full Native Termux repository suite: 635/635 in 97.501 seconds.
- Source manager: `lib/termux_boot_cron.py`; boot runner source: `scripts/termux-boot/20-ternuxx-cron`.
