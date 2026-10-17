# tools/repo_knowledge

Deterministic, non-LLM repository state sync CLI. Implements
`governance/DETERMINISTIC_STATE_SYNC_POLICY.md` and `governance/REPO_STATE_PROTOCOL.md`.

## Usage

```bash
python3 -m tools.repo_knowledge init                       # create .repo/ skeleton
python3 -m tools.repo_knowledge collect \
  --build-status passed --build-run-id "$GITHUB_RUN_ID" \
  --test-status passed --test-summary "237/237 passed"
python3 -m tools.repo_knowledge sync --ci                  # writes .repo/project.yaml + STATUS.md
python3 -m tools.repo_knowledge verify                      # report-only schema check, exit 1 on findings
python3 -m tools.repo_knowledge status                       # human-readable summary
```

Run from the repository root (the module infers `--repository owner/repo` from `git remote get-url origin`
and `--project-id` from the repo name; override either flag if that inference is wrong).

## What it does not do

- It never writes `status`, `strategic_priority`, `maturity`, or `next_gate` — those stay
  human-authored in `projects/state/*.md` per `governance/PROJECT_STATE_SCHEMA.md`.
- It never calls an LLM.
- It never deletes an event or overwrites `last_successful_build`/`last_failed_build` with a
  run that didn't actually report that outcome (see the merge rules in
  `governance/DETERMINISTIC_STATE_SYNC_POLICY.md`).

## Tests

```bash
python3 -m unittest discover -s tools/repo_knowledge/tests -p 'test_*.py' -v
```

## Retry and publication contract (audit remediation)

- The persisted project ID is reused on later `collect`/`sync` calls; identity changes
  require an explicit migration, not a silent override.
- A result records its source commit, run ID and run attempt. Pass `--build-at` and
  `--test-at` for source CI timestamps. Otherwise `timestamp_source` explicitly
  distinguishes first observation time from a commit timestamp; neither is claimed
  to be the CI completion time. Existing historical blocks are not assigned a new SHA.
- Repeating identical Git/result identities preserves timestamps and event bytes.
  A changed result for the same run/attempt is a conflict, not a silent rewrite.
- Both `collect` and `sync` render STATUS.md. `sync` additionally records a state
  transition event, not another event for every unchanged poll.
- Candidate state and events are validated in a private staging directory under a
  Git-directory lock. Linux `renameat2(RENAME_EXCHANGE)` publishes the complete .repo
  directory atomically. Unsupported filesystems/platforms fail without replacing
  existing state. An initial Git commit is required; bootstrap must create it first.
- Readers must treat the `.repo` directory as one snapshot. Source/build/test data,
  event history and STATUS.md are published together. Optional human phases survive.
