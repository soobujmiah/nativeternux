# Full repository audit and implementation worklist

Status: IN_PROGRESS. This tracks the complete owner request, not just the first successful increment. Canonical phase state remains [project/phase-state.json](../../project/phase-state.json). File coverage is recorded in [document inventory](document-inventory.json); indexing/hashing a file is not a human or source review.

## Required end state

| Requirement | Evidence needed | Current result |
|---|---|---|
| Approved UI and all earlier requested management functions | Real controls backed by shared service; source and live checks in CLI/TUI/Web/GTK | Web stable-action layout implemented; shared category order and GTK deployment verified; other action/interaction gaps remain |
| Every document read and reconciled | Per-file reviewed hash plus claim/source/evidence cross-check; current authority and historical snapshots distinguished | Inventory underway; full coverage not achieved |
| Full source/dirty/untracked audit | Reviewed tracked source/tests/config/assets, explained dirty work, syntax/tests/security/provider-boundary review | Clean baseline inspected; current changes are audit-owned; complete module review pending |
| P1–P3 completion is accurate | Every exit criterion mapped to dated evidence and current regression/preservation scope | Completion evidence re-read in part; no new physical reboot/no-PRoot test; full gate-by-gate revalidation pending |
| Native installed/runtime matches repository | Installer/module/service/menu/source identity inventory and exact comparisons | All source Runit/boot definitions, tx shim, GTK source/bridge/binary and currently installed canonical recovery modules verified; profiles/config/package/driver and fresh setup inventory pending |
| Fully reproducible supported workstation | Fresh isolated setup from checked-in manifests; exact package/driver/config provenance; rollback and preservation proof | Fixture-only fresh Debian path; disposable live replay and experimental Native driver reproduction open |
| All-client interactive terminals | Disposable guest start/attach/I/O/resize/detach/exact close through four clients | Source paths exist; full live acceptance pending |
| Current docs without conflicting duplicate status | One source for phase, CI, coverage and handoff; historical evidence dated; links checked | Root handoff/architecture/testing/manifest reconciled; remaining docs/ADRs/structured matrices pending |
| Stable tested and synchronized implementation | Relevant Native tests/browser/GUI evidence, installed parity, reviewed commit and push/CI | First remediation verified; whole objective not complete |

## Preservation contract

Implement over Native SSH 8022. Preserve Native Termux, managed 8023 access and the owner's current Codex PRoot session. Required bounded installs, GUI use and reversible PRoot configuration are authorized within this task. Never stop the working guest, reset/replace/prune its rootfs, delete user data, or broaden to unrelated shared/personal storage. Disposable test targets must be distinct and positively guarded.

## Findings and disposition

| ID | Finding | Disposition |
|---|---|---|
| A01 | Terminal service test file ended with a literal escape and did not load | Fixed; its three tests execute |
| A02 | Clipboard fixture exercised automatic browser choice instead of Android failure; interactive numbered Auto returned a non-launchable literal | Fixed and covered by deterministic chooser/fallback tests |
| A03 | Failed browser/clipboard handoffs could leave an inaccessible server; explicit fallback did not cover launch failure | Fixed; default stops, explicit fallback reveals code only when requested |
| A04 | CSS display rules could override hidden app/policy sections; details displaced action positions; old results could appear under a different resource | Hidden rule, action/inspection separation and response binding implemented; real-browser checks |
| A05 | Guest app helper implicitly requested Android Activity despite an existing verified display | Removed the implicit Activity request |
| A06 | Categories differed/alphabetized per client | Shared purpose order consumed by Web/TUI/GTK; GTK artifact reconciled |
| A07 | Manifest, README, testing guide, architecture and handoff contained conflicting old status | Current authorities simplified; old handoff/matrix preserved as history |
| A08 | SKB pointer said private while actual GitHub metadata is public | Corrected after authenticated metadata read; private runtime payloads remain excluded |
| A09 | Full all-document/source review and installed inventory not yet proven | Open; use inventory and explicit evidence per item |
| A10 | SSH key/enrollment/removal, password/recovery, per-service boot/Wake Lock policy incomplete | Open; implement shared contract before client controls |
| A11 | Fresh installer had no separate target beside the existing Debian alias | Explicit guarded replay aliases implemented; live pinned-image/package replay under qualification. Removal/rollback and four-client setup/terminal acceptance remain open |
| A12 | Experimental Native driver setup and customized guest config not fully reproducible | Open; inventory provenance and build a checked-in replay path |
| A13 | X11 secret entry depends on identifying/focusing a browser window | Open audit of exact target/focus/fallback behavior, especially existing Native browser windows |
| A14 | Historical ADR/architecture implementation paragraphs and structured feature matrices can read as current | SSH/continuity architecture corrected; old narratives preserved losslessly as history. Remaining full ADR/matrix review open |

| A15 | Phase date basis is implicit: tool records UTC dates while some historical local-date corrections exist | Open reconciliation; date mismatch alone is not a new gate failure |
| A16 | Two GitHub workflows independently run the full suite | Open CI efficiency/authority review |

| A17 | GUI monitor scheduler existed only in source | Native CLI registration and idle live deployment now verified; private fresh Runit replay delivered two 30-second Linux-only ticks. Shared-client service registration controls remain open |

| A18 | Browser reload loses the in-memory session and cannot reuse its consumed bootstrap code | Open reconnect/session-continuity design; historical reload failure is not counted as successful authentication |

| A19 | Service rollback could stop/remove a competing identical registration | Reproduced before fix; serialized install and exclusive inode ownership now preserve competitors; failed stop retains owned definition |
| A20 | New Runit directories may not be discovered before the first start request | Observed during initial live apply; bounded discovery retry added and verified by fixture plus fresh isolated live replay |

| A21 | Human formatting changed punctuation inside file paths/URLs and omitted list headings | Paths/URLs now remain exact in shared/Web formatting; shared reports label lists and translate operation names; regression added |

| A22 | 8022 and 8023 share the Termux account; credential edits can affect both | Credential contract now requires explicit shared-account impact and preservation; implementation remains open |
| A23 | P2 original full pre-consent transaction preview is unrecoverable, despite later current-state checks | Historical limitation retained; do not count later installed-state/fixture checks as proof of that original approval. Full P1–P3 claim/evidence mapping remains open |

| A24 | Refused unowned fresh destination could become resumable after the failure handler wrote an ownership-like journal | Reproduced, fixed and regression-covered; failed-stage resume now requires exact verified rootfs/container identity |
| A25 | Fresh setup shell AND/OR list could hide an APT failure by falling through to user creation | Reproduced with host-safe command stubs; independent fail-fast commands and conditional user creation now verified |
| A26 | Graphics artifact staging followed member symlinks and reused a PID-named download target | Private no-follow/exclusive artifact I/O, bounded downloads and staging serialization implemented; foreign-byte/symlink preservation tested |

## Continuation order

1. Finish reviewing/pushing this Native UI/runtime remediation and capture CI.
2. Complete remaining installed/service/boot/profile parity inventory and P1–P3 requirement evidence matrix.
3. Implement the shared SSH credential/recovery and service policy gaps with preservation/preview/rollback tests; connect all clients.
4. Support and replay a distinct disposable guest, then qualify terminal and provider routes without touching Codex's working guest.
5. Continue the full source and all-document review, updating reviewed hashes after fixes; audit the remaining roadmap, software/graphics/inference and release/reproducibility gates.
6. Run final requirement-by-requirement completion audit. Keep the overarching goal active until every explicit requirement is proven.

Historical phase completion does not waive the current reproducibility objective. A green suite or inventory alone cannot close this audit.
