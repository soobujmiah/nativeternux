# Native source-checkout CLI entrypoint — 2026-10-19

## Scope and baseline

- Repository: `soobujmiah/ternuxx`, branch `main`, base HEAD `69e378eb33247678437bda4b2de9ab25f6bcb91d`.
- Implementation ran in native Termux through the owner-started SSH 8022 development channel. At the time, the initial full suite was mistakenly routed through managed SSH 8023; owner clarification establishes 8022 as the repo development/test shell and 8023 as the Ternuxx-managed CLI endpoint.
- The working tree was already dirty with ongoing implementation. Existing changes were preserved; no commit or push was made.

## Change

- The source `tx` wrapper now uses Android's `/system/bin/sh`, resolves its checkout directory from `$0`, and invokes `bin/tx` through `$PREFIX/bin/bash` when available, falling back to `bash` from `PATH` when a fixture or alternate environment supplies a different `PREFIX`.
- `AI_ASSISTANT.md` now identifies `./tx` as the source-checkout command and the installed shim's `$HOME/ternuxx` checkout target.
- Added a regression test that executes the source-checkout `./tx --version` directly in native Termux.

## Verification

- Direct native invocation: `./tx --version` returned `Ternuxx v0.1.0`.
- Focused launch-command tests: 8/8 passed.
- Focused CLI-entrypoint tests: 8/8 passed.
- Full Native Termux suite: `bash scripts/repo_test.sh` via SSH 8023 passed 347/347 in 64.557 seconds.
- The first full run on this change set also ran 347 tests and failed 8/8 launch-command fixtures because the source wrapper treated their temporary `PREFIX` as the only Bash location. The fallback was added; the focused and final full reruns passed.

## Limits and preservation

- The test suite uses repository fixtures; it does not qualify Android UI, desktop visibility, PRoot ownership, boot delivery, or SSH listener reachability.
- No package, service, boot, desktop, Android setting, or Debian PRoot/rootfs state was changed.
- No commit or push was made.

## Route clarification and latest qualification

The owner clarified that SSH 8022 is the repo development shell and SSH 8023 is the Ternuxx-managed CLI endpoint under development. A fresh full suite run through 8022 passed 347/347 in 70.217 seconds. Earlier 8023 suite results remain historical test runs, but 8022 is the accepted route for repo development qualification.
