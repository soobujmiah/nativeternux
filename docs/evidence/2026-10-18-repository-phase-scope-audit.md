# Ternuxx repository and phase scope audit — 2026-10-18

## Result

The correct active phase is **P3 — Doctor, management, and recovery**. P2 is
recorded complete and its latest native package closure still matches all 77
exact recorded versions. The unrecoverable original pre-consent APT capture is
a historical evidence limitation, not an unclosed P2 implementation gate.
Do not jump to P4 yet: its named prerequisite is the P3 ownership contract,
and ADR-0006 is still marked proposed / owner review required.

The current Git worktree contains a large, uncommitted Ternuxx implementation
and evidence set. This audit preserves it. It does not treat untracked status
as proof a file is new to the current agent: Git has no creation time or author
for uncommitted files, and the worktree was already broadly dirty before this
audit.

## Git and worktree snapshot

- Repository root: `/data/data/com.termux/files/home/ternuxx`
- Branch: `main`; HEAD: `1a891faabc925136c1801f40194b0969d28041df`
- `origin`: `https://github.com/soobujmiah/ternuxx.git`
- Read-only `git ls-remote origin refs/heads/main` returned the same commit as
  local HEAD. There are no staged changes or committed local commits ahead of
  that observed remote ref.
- The dirty manifest captured **313 paths**: 42 tracked modifications and
  271 untracked files. It is a pre-self-reference snapshot and excludes the
  manifest file itself and this narrative report. The inventory is exact in
  [the dirty manifest](2026-10-18-repository-dirty-manifest-0801.json).
- After adding those two audit records, the handoff worktree has **315 paths**:
  42 tracked modifications and 273 untracked files, with no staged changes.
- No file was reset, removed, staged, committed, or pushed. No repository file
  outside Ternuxx was modified. Temporary diagnostic captures created in the
  PRoot `/tmp` during this audit were removed by exact filename.

### Dirty tree by area

| Area | Audit inventory | Scope assessment |
|---|---:|---|
| `.github`, `.repo`, `tools/repo_knowledge` | 8 files | Project identity, CI contract, and deterministic state tooling. The 21 `.repo/events` are generated sync/test/build/commit history; retain them and do not mistake `unknown` push/build observations for product releases. |
| CLI, lifecycle, diagnostics, recovery, SSH, ADB, management | 116 source/test/schema files | Product source and tests spanning P2/P3 and shared contracts. P3 is active; source presence is not device qualification. |
| `docs/evidence/` | 104 evidence records | Dated native, PRoot, source, and fixture observations. Preserve timestamps and scope; do not promote old snapshots to current facts. |
| Architecture and ADRs | 18 files | P3/P4/cross-phase designs. ADR-0006 remains proposed and owner review is still a prerequisite. |
| Product docs and generated phase status | 16 files | Cross-phase requirements and human-facing docs. `README.md`, `docs/ROADMAP.md`, and `docs/PHASE-STATUS.md` phase blocks are generated from `project/phase-state.json`. |
| `docs/readiness/` | 9 files | Legal, commercial, website, and governance planning. These are outside the active P3 implementation scope and do not authorize a site, offer, payment, license, or external repo edit. The repository audit in this folder is explicitly marked historical and superseded. |
| `docs/testing/` | 11 files | Test methods and future compatibility/acceleration/release plans. They are project planning; no GPU/NPU claim or hardware gate closes from these documents. |
| Other project contracts/state | 10 files | Root entrypoints, bilingual guide, phase state, schemas/docs that span phases; all remain in the Ternuxx repository boundary. |

The grouping above is a scope index, not an ownership history. The exact
path-by-path status and scope note is in the JSON manifest. No obviously
foreign project file was found in that inventory; the independent Ternux
repository/rootfs and `~/x.sh` were not edited.

## Phase audit and correct next phase

| Phase | State | Evidence-based disposition |
|---|---|---|
| P0 | Complete | Foundation and identity records exist; the same-owner rename tooling and state verifier are present. |
| P1 | Complete | Compatibility research is recorded; it remains dated evidence, not a promise of universal device support. |
| P2 | Complete | Native desktop transaction and lifecycle were accepted under the completion record. Fresh read-only `dpkg-query` matched 77/77 exact versions. The original full pre-consent APT transcript is unrecoverable and remains stated as such. |
| P3 | **In progress — continue here** | Current phase-state, source, tests, and exit audit agree. Doctor/recovery fixtures pass; boot causality, guest ownership/workload routing, listener ownership, Shizuku health, and remote transport remain open or partial. See [P3 exit-gate audit](2026-10-18-p3-exit-gate-audit.md). |
| P4 | Planned | Ternux source capability baseline exists, but its installed interface exposes no generic workload route; ownership/parity is not qualified. ADR-0006 requires owner review. |
| P5–P10 | Planned | Distro/display matrix, acceleration, app catalog, hybrid routing, optional isolated guest, and release hardening remain future work. No active-phase license/business/site work is implied. |

### P3 exit gates at the latest native check

- Doctor is read-only and distinguishes known, unknown, and warning states.
  Latest report: 14 pass / 15 info / 1 warning / 0 errors. The warning is
  native SSH `8022` configured for wildcard bind plus password authentication;
  listener ownership and external reachability remain unknown.
- Missing provider adapters fail closed rather than switching providers.
- Fixture tests cover stale identity, interrupted recovery, corrupt/path
  traversal inputs, and display conflicts.
- Existing Ternux guest ownership and an ownership-aware workload launch remain
  open. Read-only X11/Zink/Turnip guest checks do not establish managed launch
  or parity.
- Termux:Boot and its receiver are enabled; boot delivery causality, visible
  GUI delivery, and PRoot/hybrid boot qualification remain unknown. RB03 stays
  `NOT_READY`.
- Local ADB `host:version` answers `0x0029`, but that does not establish device
  transport or authorization. Shizuku versionCode 1318 is present; `rish` is
  absent from PATH; signer, service, permission, and watchdog health are
  unknown. ADT's dated analysis says the local PRoot ADB relay does not replace
  the custom Shizuku boot bridge for that workflow. No ADB/Wireless Debugging
  or Shizuku action was enabled.
- Recovery restore/rollback paths are fixture-tested; no live restore was run.

Fresh native evidence is in [the 07:57 P2/P3 recheck](2026-10-18-p3-p2-native-recheck-0757.json).
The full Native Termux fixture suite passed **272/272** in 39.629 seconds at
the 08:00 UTC continuation; the test result is recorded
[here](2026-10-18-p3-repo-test-recheck-0800.json). These tests do not close
device-only gates.

## Scope boundaries

**In scope now:** P3 Doctor, management, recovery, bounded SSH/ADB status,
native/PRoot ownership diagnostics, source/fixture work, and evidence needed
by the P3 gates. Keep P2 package state and the running desktop untouched.

**Design/evidence only until dependencies are met:** P4's existing-Ternux
adapter and workload parity, P8 hybrid routing, off-home transport selection,
Shizuku client integration, GPU/NPU runtime claims, P7 catalog entries, site,
and release paths. The P3/P4 seam needs care: P3 exit gate 4 asks for a guest
workload route, while P4 delivers feature parity and depends on the P3
ownership contract. Complete/review the P3 ownership contract first, then
advance the P4 adapter without changing the existing Ternux lifecycle.

**Outside this active implementation pass:** legal/license decisions, company
or payment setup, public website/hosting, portfolio changes, external account
configuration, package installs, Android settings, public listeners, router
changes, and modification of the independent Ternux rootfs or launcher. Their
presence in `docs/readiness/` or later roadmap phases is not authorization.

## Audit checks

- Native Termux full suite: `bash scripts/repo_test.sh` — **272/272 passed**.
- `python3 -m tools.repo_knowledge.cli verify` — **0 findings**.
- `python3 tools/phase_docs.py refresh` — generated README, roadmap status,
  and `docs/PHASE-STATUS.md` from phase state.
- Structured phase and evidence JSON parsed successfully; `git diff --check`
  passed.
- Full tree syntax/data checks passed: Bash syntax for the entrypoints and
  service scripts, the CLI help contract, Python AST parsing for 70 files, and
  JSON parsing for 133 files.
- A broader text scan found 9 Markdown lines with trailing spaces in existing
  architecture, reboot-guide, and readiness files. They are kept intact because
  the lines use Markdown hard-break formatting; they are not hidden source-code
  whitespace errors. `git diff --check` still passes for tracked changes.
- A credential-shaped text scan found no private-key marker or `sshpass`
  command. Matches were source identifiers, synthetic test values, SSH policy
  fields, and the package name `libsecret`; this heuristic is not a secret
  scanner or a substitute for release review.
- No commit/push, device service action, package mutation, desktop lifecycle,
  boot-profile change, Android setting change, PRoot command execution, or
  network exposure was performed. Read-only native status was gathered over
  the already authorized SSH connection.

## Next action

Continue **P3** by resolving its ownership-contract and device-evidence gates
one at a time. Preserve the current native `:1` desktop and existing Ternux
guest. P4 remains planned until the contract is owner-reviewed and the P3
dependency is recorded. Keep the dirty manifest and this audit as evidence;
do not clean or commit the existing broad worktree without the owner's
instruction.


## P3 continuation after this audit — 2026-10-18 08:09 UTC

Added an explicit loopback `GET /ready` response distinct from `GET /health`, backed by the owning listener lifecycle and the same Host/Origin policy. Focused HTTP tests passed 22/22 and the full Native Termux suite passed 273/273 in 41.756 seconds. The earlier dirty manifest remains the 08:00 snapshot; current Git status is authoritative for later changes. P3 stays active; no device-only gate or P4 dependency was waived. See [management readiness evidence](2026-10-18-p3-management-readiness-0809.json).

## Repository rescan — 2026-10-18 08:14 UTC

Rechecked the live worktree against `main` / `1a891faabc925136c1801f40194b0969d28041df` and verified `origin` still points to `soobujmiah/ternuxx`. The census expands untracked directories into individual paths (`git status --untracked-files=all`) and excludes the refreshed manifest itself. It contains 316 dirty paths: 42 tracked modifications and 274 untracked files; no staged paths were found. This supersedes the 08:00 counts for current status. Git cannot identify who created each pre-existing uncommitted change, so attribution is intentionally unknown. The refreshed [dirty-path manifest](2026-10-18-repository-dirty-manifest-0814.json) carries forward earlier path classifications where available and assigns active review labels to newly observed paths. The manifest and the separately recorded verification evidence add two untracked files after the census.

The phase source remains P3 `in_progress`; P0–P2 are complete and P4 remains planned. Review of the P3 gate audit, current phase state, management API contract, and ADR-0006 confirms the workload-provider contract is deliberately not implemented: installed Ternux v1.4.0 has no supported generic workload dispatch, and existing Ternux lifecycle helpers are unsafe as implicit controls. Therefore the correct next implementation boundary remains Ternuxx-owned management/readiness; no guest launcher or P4 parity work is authorized by this audit. The P3 exit audit remains authoritative for device-only blockers. No dirty path was staged, removed, reset, committed, or pushed.


## Runtime attribution correction and native verification — 2026-10-18 08:18 UTC

The 08:14 repository audit suite record was initially labeled as native, but a later `uname` check proved that command shell was Debian PRoot. Its evidence has been corrected to PRoot fixture evidence. The same 273-test suite was then run over the authorized native Termux SSH session and passed 273/273 in 41.229 seconds. Native P2 read-only state separately reports display `:1` running and 77/77 exact installed XFCE package versions. The original incomplete pre-consent preview remains unrecoverable and is not reconstructed by either test run or package query. See [native test evidence](2026-10-18-p3-native-suite-recheck-0817.json) and [P2 closure evidence](2026-10-18-p2-native-closure-recheck-0816.json).
