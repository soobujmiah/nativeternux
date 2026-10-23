# Documentation, status, and SKB knowledge return

Ternuxx uses related records, each with one owner. This keeps product decisions, phase progress, and Git/CI facts from drifting or overwriting one another.

## Sources of truth

| Record | Authority | Update method |
|---|---|---|
| Architecture, product decisions, evidence, operating guidance | Human-authored project docs and evidence under `docs/` | Reviewed edits; preserve source links, date, evidence class, and limitations |
| Phase order and gate progress | `project/phase-state.json` | `python3 tools/phase_docs.py update` for active-phase progress, `annotate` for planned-phase preparation and optional metadata, `complete` for reviewed gate transitions, `skip` for an evidence-backed active optional-phase skip, or `refresh`; generated README/roadmap/status blocks are never edited directly |
| Commit, branch, version, CI build/test results, synchronization events | `.repo/project.yaml`, `.repo/events/`, `.repo/STATUS.md` | SKB `tools/repo_knowledge` only; never hand-write these facts |
| Cross-project durable owner knowledge | Canonical SKB topic/project files | Session-level knowledge return under SKB's [knowledge-return protocol](https://github.com/soobujmiah/skb/blob/main/governance/KNOWLEDGE_RETURN_PROTOCOL.md); never copy ordinary commits or transient logs |

`docs/PHASE-STATUS.md` is the human-readable milestone view. `.repo/STATUS.md` is deterministic repository state. They answer different questions and must not be merged into a second generated status document. `CURRENT_STATE.md` is the concise narrative about decisions, evidence, known defects, and next work; it must link to generated status instead of copying its SHAs or CI result.

## Workflow event ownership

The two GitHub Actions workflows each own one event class so they do not run the full suite twice for the same event:

| Event | Workflow | Work |
|---|---|---|
| Pull request targeting `main` | `Repository State Contract` | Shell/help contract, full repository suite, deterministic-state and README bridge validation, project classification, and required-document checks |
| Push to `main` outside `.repo/**` | `Repository Knowledge Sync` | Deterministic-state and README bridge validation, full repository suite, then honest `.repo/` state synchronization |
| Manual dispatch | `Repository Knowledge Sync` | Explicit validation and repository-state synchronization |

Keep pull-request validation in the contract workflow. The state-sync workflow must not add a pull-request trigger: its pull-request job duplicated the full suite and schema checks while the contract workflow already performed them. CI concurrency is repository-event scoped; the GitHub Actions token writes only generated state in this repository. A live GitHub settings check on 2026-10-24 found no `main` branch protection and no repository rulesets, so these checks currently report validation but do not enforce merge blocking.

## Automatic repository status

The repository slug is persisted separately from the stable internal project ID. After an owner-authorized same-owner GitHub rename, update `origin` and run `python3 -m tools.repo_knowledge migrate-repository --from-repository OLD --to-repository NEW`. This explicit transaction updates current `.repo/project.yaml` identity, regenerates `STATUS.md`, preserves prior build/test facts and event bytes, and appends one migration event. It refuses owner transfers, an origin mismatch, or a stale source identity. Never edit generated `.repo/project.yaml`, `.repo/STATUS.md`, or historical event files by hand. `verify`, `collect`, and `sync` report an origin/persisted-identity mismatch until migration is performed.

The phase tool updates only phase status blocks. SKB's `tools/repo_knowledge` runtime is vendored under `tools/`; the first Ternuxx validation and state-sync workflows passed on commit `735c1aa`. The workflow accurately recorded build/test as `unknown` because no build or test suite was run. SKB central registration and pull verification remain separate. The repository setup follows SKB's current `governance/DETERMINISTIC_STATE_SYNC_POLICY.md`, `governance/REPO_STATE_PROTOCOL.md`, `governance/KNOWLEDGE_RETURN_PROTOCOL.md`, and `standards/new-repository-standard.md`:

1. Vendor the current `tools/repo_knowledge/` runtime, schemas, bridge helper, and workflow contract from the verified canonical SKB checkout. Its internal unit tests remain in SKB and are not copied or run in Ternuxx.
2. Configure this repository's actual build/check and test evidence. A missing or not-yet-defined check is `unknown`, never a fake pass. Keep physical-device evidence as its own gate; CI cannot claim a GPU/NPU/device result it did not observe.
3. Initialize `.repo/`, add the repo's own CI workflow to run relevant checks and `repo_knowledge sync --ci`, then verify generated state and provenance.
4. Give the workflow only the permissions it needs to commit generated files to this repository. It receives no SKB write token and has no cross-repository write path.
5. SKB's separately authorized registry reader pulls `.repo/project.yaml` only after explicit membership approval and registration. A private repository's state is not projected to public surfaces.

The exact workflow must observe an existing authoritative CI when repeating a costly or device-bound build would be harmful. Do not create placeholder build/test scripts just to report `passed`.

## SKB knowledge return

Mechanical synchronization and human knowledge return are separate:

- The participant repository's CI updates only its own `.repo/` state.
- SKB pulls only the state of repositories in its explicit registry; the participant never writes to SKB and stores no cross-repository credential.
- The agent returns durable, evidence-backed discoveries to the canonical SKB location: current project state under `projects/state/`, a technical summary under `repositories/`, or another topical file when that is the proper authority.
- If an item is uncertain or conflicts with existing SKB knowledge, record it for review instead of replacing canonical facts. Never sync credentials, personal payloads, transient logs, source mirrors, or ordinary implementation details.
- Membership eligibility, data classification, owner approval, readiness validation, and explicit registry registration must happen before deterministic registry participation. A request to return useful knowledge does not authorize publishing a private repo's contents publicly.

Current CI results are linked from generated repository status. Central registry membership and App-backed pull success must be checked against SKB's current registry and receipts; older onboarding observations are not current access proof. GitHub metadata reports Ternuxx public, but secrets and private runtime/personal payloads are excluded from all returns.

### Central pull boundary

No SKB credential is installed in Ternuxx. Project Actions writes only this repository using its same-repository token. A separately authorized read-only SKB Registry Reader App performs central pulls for explicitly registered participants. Verify membership, effective access and the resulting receipt in SKB. Never add a participant-held cross-repository write/dispatch credential or broaden App selection as an implementation shortcut.

## Session close

For each substantial session:

1. Inspect project diffs and preserve unrelated edits.
2. Record what was researched, implemented, and actually checked; separate live device evidence from design proposals.
3. Refresh phase-generated docs after a documented phase-state change.
4. Run `repo_knowledge status` and `verify` after onboarding; resolve sync failures rather than hand-editing `.repo/`.
5. Perform an SKB knowledge-return pass and report whether it was synchronized, queued, or blocked.
6. Keep commits, tests, device checks, and publication claims tied to actual output. Do not commit/push unless project instructions and the user authorize it.
