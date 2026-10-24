# Current repository audit

**Reviewed:** 2026-10-24 after Native-only implementation and P0–P10 phase resolution. The former multi-provider audit and its dated claims are preserved in [historical audit](../history/REPOSITORY-AUDIT-pre-native-only-2026-10-24.md).

## Product and implementation

The accepted product is Native Termux-only. Six guest containers, PRoot packages, guest lifecycle modules, guest management routes, PRoot schemas, terminal broker, guest graphics handoff, client controls, and feature-specific tools/tests are retired. Current Native behavior is implemented through the shared typed management service and authorized CLI, TUI, authenticated loopback Web, and GTK bridge. Historical PRoot text is indexed as history and does not define supported behavior. See the [retirement evidence](../evidence/2026-10-24-native-only-proot-removal-audit.md), [ADR-0017](../architecture/decisions/ADR-0017-native-only-product-and-proot-retirement.md), and [capability matrix](../architecture/CAPABILITY-MATRIX.md).

The Native optional catalog provides htop, tmux, and tree through exact package plans. The bounded tree handoff accepts a HOME-relative regular file or directory and lists names only; it rejects traversal, symlinks, special files, and paths outside HOME. The CPU workflow uses one pinned model and a Termux-owned runtime; it is bounded to CPU and does not provide multi-turn sessions, broad model support, or verified offline operation. These are implemented features with distinct limits, not release claims. See the [software catalog](../SOFTWARE-CATALOG.md) and [CPU workflow evidence](../evidence/2026-10-24-native-cpu-inference-workflow.md).

## Verification evidence

- `bash scripts/repo_test.sh`: 724 tests passed in 91.761 seconds on Native Termux. The suite validates repository behavior through fixtures and mocks; it does not prove Android window visibility, physical audio output, clean-device installation, or cold boot.
- `python3 -m tools.repo_knowledge verify`: zero findings.
- `python3 tools/audit_documents.py --check`: current document path/hash coverage; latest inventory has zero broken local links. The read count is not a claim that every historical document was reviewed.
- Strict README state-bridge validation and `git diff --check` passed.
- Live read-only checks confirmed Native XFCE/X11 on `:1`, matched Native audio ownership, absence of PRoot commands/rootfs, and clean APT package state at the recorded check. The active Termux app and Native services were not stopped.

The package-specific and workload-specific observations are dated evidence; use [P8 readiness](../evidence/2026-10-24-p8-native-readiness-audit.md) and [P10 internal review](../evidence/2026-10-24-p10-internal-hardening-review.md) for their precise scope.

## Open release gates

Internal roadmap work is resolved: ten phases completed and optional P9 skipped because the owner selected Native-only scope. Public release remains blocked. The repo has no selected project license, old licensing statements are ambiguous, complete source provenance/SBOM review is open, clean-device reproduction is absent, and Doctor reports wildcard/password-enabled Native SSH configuration with listener ownership and external reachability unknown. Android boot delivery and broad device compatibility are also unqualified. These are explicit release limits, not undocumented implementation claims. The owner must choose a license direction after legal review; no license was inferred or added.

The owner-reported backup was not inspected. No shared/external storage was accessed. Read [CURRENT_STATE.md](../../CURRENT_STATE.md) for the concise live project summary, [phase status](../PHASE-STATUS.md) for gate records, and [known limitations](../testing/KNOWN-LIMITATIONS.md) for support boundaries.
