# Guarded separate Debian setup replay — 2026-10-22

Phase: `P4`
Gate: IN_PROGRESS

## Implementation and failures

Implementation runs in Native Termux through SSH 8022. Before changes, two regressions reproduced real defects: repeating apply after an unowned-destination refusal reached a guest mutation, and an APT failure could return success through shell AND/OR precedence. Test commands use private temporary fixtures and do not run guest APT/source edits on the host.

Fresh preview schema 2 accepts the absent default Debian target or an explicit `ternuxx-replay-NAME` alias. It refuses occupied containers and symlinked paths. State stays private under HOME. Per-alias locks serialize different previews. A refusal never writes an ownership receipt; resume requires the exact verified container/rootfs identity and same preview.

Independent fail-fast guest commands prevent package errors reaching account creation. Final dpkg inventory must report every requested package actually installed, including held packages; removed/config-only records do not count. Version evidence and provider receipts are alias-specific.

Graphics archive/member hashes remain pinned. Staging uses private no-follow/exclusive I/O, a bounded archive size and its own lock, and refuses foreign existing bytes instead of following member symlinks or overwriting artifacts.

## Evidence

- Focused fresh setup tests: 14/14; existing guest adoption tests: 4/4.
- Full Native source suite: 722/722 passed in 103.215 seconds. [Regression identity record](2026-10-22-fresh-guard-regression.json) binds the result to source hashes.
- CLI help contract, shell syntax and diff checks passed.
- Native PRoot-Distro 5.9.0 supports the explicit --name container target. Approximately 80 GiB was available before replay.
- Live `ternuxx-replay-p4` replay started from the pinned Debian image; image verification and repository update passed, and package archive retrieval is progressing (366 requests observed). The package stage is still under observation. This is not recorded as a completed setup.
- The installer command is directed only at the new alias. It records the working Debian identity and selected protected-file hashes in memory for a post-run preservation check; private values are not published.

## Remaining acceptance

Record the actual live installer outcome, verify new guest account/package/driver identities and working-guest preservation, then qualify supported GUI/terminal workloads on this separate target. This increment does not claim four-client terminal acceptance, fresh Native Termux setup, rootfs rollback, working-guest config replay, rendering, inference/NPU or cold boot. The overarching [audit](../audit/REPOSITORY-AUDIT.md) remains active.
