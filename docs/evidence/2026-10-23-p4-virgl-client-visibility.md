# P4 VirGL client visibility and CLI JSON - 2026-10-23

Phase: `P4`

## Change

VirGL status now distinguishes verified idle sockets, attached clients, and unknown client visibility. Unknown or external ownership sets `stop_allowed=false`; stop remains fail-closed. Human CLI output includes the client visibility and stop decision, while `--json` emits the stable status object.

The Native CLI parses `--json` as a global option before dispatch. Both VirGL command wrappers now forward that parsed state to `virgl_lifecycle.py`; this fixes `tx virgl status --json` silently returning human text. A regression test covers the VirGL and launch wrappers plus the direct operation flag.

## Evidence

- Native Termux full suite: `bash scripts/repo_test.sh` — 887 tests passed, 1 skipped (129.919 seconds).
- Focused lifecycle: `python3 -m unittest discover -s tests -p test_virgl_lifecycle.py -q` — 10 passed.
- Focused command routing: `python3 -m unittest discover -s tests -p test_launch_commands.py -q` — 13 passed after wrapper coverage was extended.
- `bash -n lib/launch.sh lib/virgl.sh` and `git diff --check` passed.
- Live `tx virgl status --display :1` reported a running, identity-verified Ternuxx server; Android `lsof` could not map the Unix socket owner, so clients are `unknown` and stopping is refused.
- Live `tx virgl status --display :1 --json` returned valid JSON with `client_visibility=unknown` and `stop_allowed=false`.

## Limits and preservation

No VirGL process was stopped, no socket or rootfs was modified, and no GUI/session was restarted. Socket client ownership cannot be proven on this Android build, so idle status and cleanup remain unverified. `/usr/bin/tx` is a thin shim to `$HOME/ternuxx/tx`; the live command therefore exercises the checked-out source. A separate copied install under `$PREFIX/lib/ternuxx` is absent, so independent installed-module parity is not claimed.

P4 remains in progress. Continue isolated broken-rootfs recovery and cold-boot qualification, then reconcile installed/runtime state and complete the full audit and owner-operated GTK review. Keep VirGL stop blocked until socket-owner visibility can be proven.
