# Ternuxx name-migration inventory

**Inventory captured:** 2026-10-17, before applying any Ternuxx naming edits.
**Repository at capture:** `soobujmiah/nativeternux`, public, branch `main`, HEAD `1a891fa`; captured before owner-authorized rename.
**Target:** product/brand `Ternuxx`; preferred repository slug `ternuxx`.

This inventory includes tracked files and the readiness documents already drafted in this worktree. It distinguishes current product identity from the separate existing Ternux project, historical GitHub state, generated provenance, and compatibility identifiers. It is a baseline; repeat the search after approved migration.

## Old-name to canonical-name map

| Old/current identifier | Canonical target | Migration treatment |
|---|---|---|
| `NativeTernux` (product prose/title) | `Ternuxx` | Update current product labels. Preserve dated/historical quotes and explain prior naming where required for provenance. |
| `nativeternux` (CLI/path/URL/repository slug) | `ternuxx` | Update repo slug and current-facing command/URL only as a coordinated, compatibility-aware migration. Keep the stable internal project ID `nativeternux` until its SKB registry migration is approved and synchronized. |
| `Ternexx` (superseded spelling from the previous draft) | `Ternuxx` | Correct current planning documents; it is not the approved spelling. |
| `Ternux` / `soobujmiah/ternux` | unchanged | This is the separate existing Ternux Debian PRoot project and must not be renamed by this work. |
| `Native Termux` | unchanged | Describes the Termux host/runtime layer, not the previous product name. |

## Current-name references eligible for coordinated migration

The old current project/product name occurs in the following files. Counts are case-insensitive substring matches for `NativeTernux` and `nativeternux`; file paths themselves are listed separately.

| Area | Files |
|---|---|
| CLI and runtime source | `bin/nativeternux` (19/19); `nativeternux` (6/6); `lib/core.sh` (2/2); `lib/desktop-supervisor.sh` (2/2); `lib/desktop.sh` (17/17); `lib/doctor.sh` (1/1); `lib/help.sh` (19/19); `lib/info.sh` (2/2); `lib/phases.sh` (8/8) |
| Root project and governance | `AI_ASSISTANT.md` (4/4); `CURRENT_STATE.md` (2/2); `PROJECT_CLASSIFICATION.yaml` (1/0); `PROJECT_MANIFEST.yaml` (2/0); `README.md` (6/6); `SECURITY.md` (4/4); `SKB_KNOWLEDGE_SYNC.md` (3/3); `bn/README.md` (5/5) |
| Architecture, operations, and research docs | `docs/ARCHITECTURE.md` (13/13); `docs/HYBRID-INTEGRATION.md` (17/17); `docs/INSTALLATION.md` (6/6); `docs/KNOWLEDGE-SYNC.md` (9/9); `docs/OPERATIONS.md` (38/38); `docs/OPTIMIZATION.md` (7/7); `docs/PRODUCT-VISION.md` (2/2); `docs/PROOT-GPU.md` (10/10); `docs/RESEARCH.md` (20/20); `docs/ROADMAP.md` (18/18); `docs/WINE-NATIVE.md` (10/10) |
| ADRs and evidence records | `docs/architecture/decisions/ADR-0001-native-proot-providers.md` (4/4); `docs/architecture/decisions/ADR-0002-workload-verified-acceleration.md` (1/0); `docs/architecture/decisions/ADR-0003-deterministic-state-and-skb-return.md` (1/0); `docs/evidence/P0-foundation.md` (2/2); `docs/evidence/P2-lifecycle-progress.md` (3/3) |
| Readiness documents drafted before this inventory | `docs/readiness/DECISIONS-AND-PLAN.md` (3/3); `docs/readiness/PRODUCT-MARKET-COMMERCIAL.md` (1/1); `docs/readiness/README.md` (4/4); `docs/readiness/REPOSITORY-AUDIT.md` (6/6); `docs/readiness/WEBSITE-SEO-OPERATIONS.md` (1/1) |

Each pair is `(NativeTernux, nativeternux)` count. An absent pair, for example `PROJECT_MANIFEST.yaml`, has no exact lowercase CLI-name match. Paths, generated text, and URLs were searched case-insensitively. `.repo` generated/history files are listed separately below.

## References that must remain accurate

| Files/references | Treatment |
|---|---|
| `docs/ROADMAP.md`, `docs/architecture/decisions/ADR-0001-native-proot-providers.md`, `docs/RESEARCH.md`, `docs/PROOT-GPU.md`, `docs/OPERATIONS.md`, `docs/HYBRID-INTEGRATION.md`, `docs/WINE-NATIVE.md`, and evidence records referring to **Ternux** or `soobujmiah/ternux` | Preserve as the name of the separate existing Ternux project/provider. Do not replace it with Ternuxx. Update only wording that labels this project itself. |
| First-commit README/header license claim: “PolyForm Noncommercial 1.0.0 plus the Ternux commercial-use addendum” | Preserve as historical wording in legal research. Do not normalize the quoted name or imply that the absent addendum exists. |
| `.repo/STATUS.md` and `.repo/events/*` | Generated commit/build/test evidence and historical project identity; do not hand-edit or rewrite. Regenerate only through the existing deterministic workflow after an approved identity migration, preserving event history. |
| Git commit history and existing published GitHub URLs | Immutable history/provenance. A repository rename may redirect ordinary repo URLs, but does not rewrite commits or every external reference. |
| `tools/repo_knowledge/` and `SKB_KNOWLEDGE_SYNC.md` registry identity | Keep synchronization semantics intact. Update project registry/slug only through the documented owner-controlled SKB synchronization process; do not publish private runtime or personal device state. |

## Rename-sensitive integration inventory

- GitHub repository: `soobujmiah/nativeternux` → `soobujmiah/ternuxx`; target slug was checked before rename and the owner-authorized rename completed on 2026-10-17. Current GitHub metadata verifies public visibility and the new slug.
- The `nativeternux` project ID passed to `tools/doc_bridge.py` and used as the deterministic/SKB synchronization key is an internal registry identifier, not a marketing label. Do not change it until the owner-controlled registry migration and compatibility procedure are defined.
- Local clone remote: updated to `origin=https://github.com/soobujmiah/ternuxx.git` after rename; `git ls-remote origin HEAD` verified the remote is reachable.
- CLI executable, dispatch name, install/library paths, environment variables, state/log paths, and JSON `owner` value: identifiers in `bin/nativeternux`, `nativeternux`, and `lib/*.sh`. Renaming user-state directories or environment variables can break existing installs; migration needs backward-compatible reads and explicit state migration design.
- Project manifest, classification, `.repo/project.yaml`, generated-state registry, phase tooling, CI workflows, README badges/links, help URLs, and SKB project registration. The manifest, current-facing links, and generated current-state now use Ternuxx. The deterministic migration command preserves the internal project ID and historical event records; remote CI awaits owner commit/push.
- Existing personal portfolio `https://soobujmiah.github.io/` and existing project links. No portfolio file is part of this repository; do not edit it as part of a local repository migration.
- Project website: none configured for this repository at capture. Do not assume a Pages URL or custom domain exists.
- External links, forks, package caches, installed CLI copies, shell aliases, and user scripts cannot be fully inventoried from the repository. Publish a migration note and retain compatibility where practical.

## Rename preflight and constraints

The rename is complete. GitHub now reports the new public repository identity and the local remote fetches successfully. Ordinary repository pages and Git operations resolve through GitHub's rename behavior; project Pages URLs and workflows that consume this repo as a GitHub Action still need separate review. The repository contains no action metadata (`action.yml`/`action.yaml`) at inventory time.

This inventory is a documentation baseline. The owner separately authorized and completed the repository rename. It does not authorize a CLI compatibility break, license change, release, website deployment, or SKB registry write.

## 2026-10-17 implementation addendum

The canonical `ternuxx` entry point now delegates to the same CLI implementation
as `nativeternux`. The source-checkout command is `./ternuxx` or `bin/ternuxx`;
the old command remains a compatibility entry point. Help and version output
use the Ternuxx brand. Newly written desktop session records identify owner
`ternuxx`; old state paths and internal environment-variable names are retained
for compatibility and have not been migrated. Current product prose in
`docs/RESEARCH.md` and active command examples now use Ternuxx/`ternuxx`.

Still intentionally unchanged: this inventory's capture data, immutable Git
and `.repo/events/*` history, stable SKB project ID, old installed-path/state
identifiers, and the separate existing Ternux project name. A complete runtime
installation-path migration and SKB registry migration remain open decisions.
