# Documentation, status, and SKB knowledge return

NativeTernux uses three related records, each with one owner. This keeps product decisions, phase progress, and Git/CI facts from drifting or overwriting one another.

## Sources of truth

| Record | Authority | Update method |
|---|---|---|
| Architecture, product decisions, evidence, operating guidance | Human-authored project docs and evidence under `docs/` | Reviewed edits; preserve source links, date, evidence class, and limitations |
| Phase order and gate progress | `project/phase-state.json` | `python3 tools/phase_docs.py`; generated README/roadmap/status blocks are never edited directly |
| Commit, branch, version, CI build/test results, synchronization events | `.repo/project.yaml`, `.repo/events/`, `.repo/STATUS.md` | SKB `tools/repo_knowledge` only; never hand-write these facts |
| Cross-project durable owner knowledge | Canonical SKB topic/project files | Session-level knowledge return under SKB's [knowledge-return protocol](https://github.com/soobujmiah/skb/blob/main/governance/KNOWLEDGE_RETURN_PROTOCOL.md); never copy ordinary commits or transient logs |

`docs/PHASE-STATUS.md` is the human-readable milestone view. `.repo/STATUS.md` is deterministic repository state. They answer different questions and must not be merged into a second generated status document. `docs/HANDOFF.md` (when introduced) is the concise narrative about decisions, evidence, known defects, and next work; it must link to generated status instead of copying its SHAs or CI result.

## Automatic repository status

The phase tool updates only phase status blocks. The runtime of SKB `tools/repo_knowledge` is now vendored under `tools/`, and `.repo/STATUS.md` was initialized locally. The GitHub workflows are present but have not run; current build/test status is honestly `unknown`, and the local sync source is not CI evidence. Onboarding and registration remain gated. The repository setup follows SKB's current `governance/DETERMINISTIC_STATE_SYNC_POLICY.md`, `governance/REPO_STATE_PROTOCOL.md`, `governance/KNOWLEDGE_RETURN_PROTOCOL.md`, and `standards/new-repository-standard.md`:

1. Vendor the current `tools/repo_knowledge/` runtime, schemas, bridge helper, and workflow contract from the verified canonical SKB checkout. Its internal unit tests remain in SKB and are not copied or run in NativeTernux.
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

The project has local `.repo/` state and workflow source but no CI execution yet; the current generated state is local and reports build/test as `unknown`. SKB registry registration remains pending readiness and explicit pull verification. The SKB checkout remote was verified as `soobujmiah/skb` on 2026-10-17. No automatic GitHub or SKB registry update is claimed until the workflow runs and the repository is registered.

### Required GitHub App step for SKB's central pull

There is no SKB App package, secret, or cross-repository credential to install in NativeTernux. Its project-side Actions workflow does **not** need the SKB GitHub App: it writes only to NativeTernux with its same-repository `GITHUB_TOKEN`. The separate SKB registry pull needs the account-installed, read-only **SKB Registry Reader** App to include this private repository in its selected-repository list. The latest local authorization receipt is dated 2026-10-14; it includes `ternux` but not `nativeternux`. Treat that as a dated observation, not a live guarantee.

After the readiness gate passes, the owner must open GitHub **Settings → Applications → Installed GitHub Apps → SKB Registry Reader → Configure**, select only `soobujmiah/nativeternux` as an added repository, and save. Keep the App's repository selection limited to approved participants and `Contents: read` (Metadata is implicit). Do not broaden it to all repositories or add an SKB credential to NativeTernux. Then register the repository through SKB's prescribed registry command and verify a real pull. App installation changes are owner-side actions under SKB policy; project code or an agent cannot perform them.

The inspected local Ternux checkout (`38a5217`, branch `codex/license-terms-review-20261016`) has an optional `SKB_DISPATCH_TOKEN` path in its repository workflow. That older project-side dispatch pattern is not copied here: the current SKB policy says participant repos must not hold an SKB write/dispatch credential. SKB's registry workflow already has a daily schedule and a manual run option, so central status can be pulled without adding cross-repository secrets to NativeTernux.

## Session close

For each substantial session:

1. Inspect project diffs and preserve unrelated edits.
2. Record what was researched, implemented, and actually checked; separate live device evidence from design proposals.
3. Refresh phase-generated docs after a documented phase-state change.
4. Run `repo_knowledge status` and `verify` after onboarding; resolve sync failures rather than hand-editing `.repo/`.
5. Perform an SKB knowledge-return pass and report whether it was synchronized, queued, or blocked.
6. Keep commits, tests, device checks, and publication claims tied to actual output. Do not commit/push unless project instructions and the user authorize it.
