# Repository and implementation audit

**Historical snapshot date:** 2026-10-17. This file preserves that audit as a dated record; its phase and implementation statuses are no longer current. See the [current repository and phase-scope audit](../evidence/2026-10-18-repository-phase-scope-audit.md) and [current state](../../CURRENT_STATE.md) before using any status below. At the time of the historical audit, the local checkout was clean before those documentation-only edits. The current worktree is substantially dirty; its exact Git-relative inventory is recorded in the new audit manifest.

## Repository facts

| Requirement or claim | Status | Evidence | Gap / risk | Recommended next action | Approval |
|---|---|---|---|---|---|
| Canonical repository identity | `VERIFIED` | After owner-authorized rename on 2026-10-17, `gh repo view` and `origin`: `https://github.com/soobujmiah/ternuxx.git`; public; default branch `main`; remote HEAD `1a891fa` | Repository slug is Ternuxx; executable, CLI, install paths, SKB project ID, and some historical/audit links retain prior identifiers | Update current-facing repository links and deterministic state; preserve historical evidence and plan a separate CLI/path compatibility migration | Repository rename authorized and completed; CLI/path migration remains separate |
| Repository visibility | `VERIFIED` | GitHub metadata: `visibility=PUBLIC`, `isPrivate=false` | `CURRENT_STATE.md` previously called it private | Corrected in this draft; keep future status sourced from GitHub | No |
| Releases and artifacts | `VERIFIED` | GitHub Releases API returned 0; no release workflow or installer artifact in tracked tree | No checksum, signature, versioned package, download or rollback artifact | Do not show a download/install button until a real release exists | Release approval later |
| License metadata | `VERIFIED` | GitHub `license=null`; no tracked `LICENSE`, `NOTICE`, or `COPYING` | Public source is not licensed for general reuse; historical terms conflict with missing files | Resolve historical assertion and provenance with counsel before selecting terms | Explicit owner + qualified legal review |
| Repository history | `VERIFIED` | Five commits at audit; three commits attributed to Sobuj Miah, two generated sync commits by `github-actions[bot]` | Git authorship is not a complete assignment/provenance record | Record contributor, contractor, generated-code, and asset provenance before release | Owner decision / legal review |
| Website/deployment | `VERIFIED` | No website source/config in repo; GitHub Pages API returned 404; repository `homepage` empty | CLI now links to repository Markdown because no project Pages site exists | Keep repository documentation links until a separately approved site is published | Website implementation approval |
| CI | `PARTIALLY_VERIFIED` | Two workflows validate repository-state metadata and README bridge, then sync `.repo/`; past Actions runs visible | Local state migration and subsequent sync/verify pass; renamed-repo Actions run remains unobserved until the worktree change is pushed. No product build, release, SBOM, signing, or security scan workflow exists. | Owner commits/pushes the reviewed migration change, then inspect both renamed-repo workflow results | No remote CI run triggered; product runtime remains unqualified |
| Test suite | `PARTIALLY_IMPLEMENTED` | CLI help contract, isolated mock-process lifecycle fixture, and Python rename-migration tests exist in the worktree | No package transaction, provider, GUI, or physical-device integration test suite; CI changes remain unverified remotely | Extend isolated tests for startup failure/rollback and keep physical-device acceptance separately gated | Local test/source work; device operation separately authorized |
| Dependencies | `PARTIALLY_VERIFIED` | `requirements-dev.txt`: `PyYAML>=6.0,<7`; workflow uses `actions/checkout@v5`, `actions/setup-python@v6` | No dependency lock/SBOM; Actions use mutable major tags | Add dependency provenance/update policy and pin actions to reviewed commit SHAs when source work is approved | Source/workflow approval |
| Security policy | `PARTIALLY_VERIFIED` | `SECURITY.md` exists and GitHub exposes a security-policy URL | Reporting instructions say “existing GitHub contact channel” without a dedicated response process or response commitment | Specify private report path, owner triage, disclosure boundaries and no SLA unless staffed | Owner approval |
| Product phase | `VERIFIED` | `project/phase-state.json`, README, `docs/ROADMAP.md` | P0 and P1 recorded complete; P2 active; P3–P10 planned | Preserve phase generator; don't call the full product ready | No |

## Implementation facts

| Capability | Status | Source evidence | What is actually established |
|---|---|---|---|
| CLI scaffold and device info | `PARTIALLY_VERIFIED` | `bin/nativeternux`, `lib/core.sh`, `lib/info.sh` | Source exists. No current audit runtime execution was performed. |
| Native package installer | `PARTIALLY_VERIFIED` | `lib/phases.sh` | `install --yes` contains an APT transaction path; docs say not run or device-qualified. It is a real mutating code path, not a release-ready installer. |
| Native desktop lifecycle | `PARTIALLY_VERIFIED` | `lib/desktop.sh`, `lib/desktop-supervisor.sh`, `tests/test_desktop_lifecycle_fixture.py`, P2 evidence | Isolated mock-process start/idempotency/status/stop tests pass locally; actual Termux:X11/XFCE and process-tree behavior remain untested on device. |
| CLI help accuracy | `CORRECTED LOCALLY` | `lib/help.sh` now describes the implemented start/stop/restart/status and package-apply paths; `tests/test_cli_help.sh` checks these disclosures | The desktop lifecycle and package transaction themselves remain unqualified on a physical device | Keep the help-contract test in CI and qualify lifecycle separately before release |
| Doctor | `PARTIALLY_VERIFIED` | `lib/doctor.sh` | A command path exists, but current implementation/evidence is not a complete operational Doctor/recovery product. No release qualification. |
| Existing Ternux Debian PRoot adapter | `NOT_IMPLEMENTED` | No provider adapter or hybrid dispatcher in tracked `lib/` | Ternux remains independent. Ternuxx cannot manage/recover its processes or claim automatic reuse. |
| Hybrid routing | `PLANNED` | `docs/HYBRID-INTEGRATION.md`, P8 roadmap | Architecture/requirements only. |
| Existing PRoot graphics and AI routes | `PARTIALLY_VERIFIED` (external) | `docs/PROOT-GPU.md`; Ternux `main` accelerator plan and benchmark records | Ternux documents Zink/Turnip graphics and separate CPU/Vulkan inference plus experimental HTP/QNN work. This audit did not rerun them; Ternuxx has no adapter. Keep external PRoot evidence separate from native Termux and Ternuxx release qualification. |
| Native GPU | `PARTIALLY_VERIFIED` negative evidence | `docs/RESEARCH.md` records native Vulkan `VK_ERROR_INCOMPATIBLE_DRIVER` for the tested package/process | No broad native GPU acceleration claim. |
| NPU | `NOT_IMPLEMENTED` / `UNKNOWN` access | No NPU bridge in source; research says no Termux/PRoot workload proof | Hardware specification alone is not a product feature. |
| Boot, Termux:API, SSH, recovery, backups | `PLANNED` | `docs/OPERATIONS.md`, P3 roadmap | Requirements only; no control plane or tested service implementation. |
| Wine/Hangover | `PLANNED` | `docs/WINE-NATIVE.md` | Candidate research only; no application is qualified. |
| Software catalog/editions | `PLANNED` | No current catalog source file or site | No supported apps catalogue, package edition, or commercial module exists. |

## Documentation inconsistencies identified

1. `CURRENT_STATE.md` described the repository as owner-reported private. GitHub says public.
2. The current README said the license had to be chosen before “public release,” although the source repository is already public. It also did not explain the exact historical noncommercial assertion.
3. `lib/help.sh` previously called `start` a readiness stub and `install` a preview stub, while `lib/desktop.sh` starts/stops processes and `lib/phases.sh` has `apt-get install` behind `--yes`. Help has now been corrected and contract-tested; lifecycle has an isolated mock-process fixture but remains unqualified on Android.
4. CLI `guides` references a GitHub Pages path; Pages is not configured for this repo.
5. `CURRENT_STATE.md` referred to an early sync commit as if it were the current CI record. Generated `.repo/STATUS.md` is the mechanical record and should remain the authority.
6. The GitHub repository rename is complete and verified. Current-facing links and some labels are updated; executable, state paths, internal project ID, historical records, and remaining name occurrences still require context-aware compatibility review.

Items 1, 2 and 5 were clarified in the documentation draft. CLI help was corrected locally; mutating command behavior remains unqualified pending isolated and device tests.

## Repository test/verification status

- A narrow CLI help contract test, isolated native lifecycle fixture, and deterministic repository-rename tests now exist in this worktree; provider, GUI, package transaction and physical-device test suites are still absent.
- CI validates repository-state schemas and the README bridge; those are not product tests.
- Local help-contract, isolated mock-process lifecycle, Bash syntax, rename-migration unit, state-integrity, documentation-bridge, workflow-YAML, and whitespace checks have been run; no shellcheck or physical-device lifecycle test was run.
- These local checks do not qualify desktop or package-transaction behavior on Android.
