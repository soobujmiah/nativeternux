# Management Center managed SSH parity — 2026-10-19

## Scope and preservation

Implementation ran in Native Termux at `/data/data/com.termux/files/home/ternuxx`, on branch `main`, HEAD `69e378eb33247678437bda4b2de9ab25f6bcb91d`, with the pre-existing dirty worktree preserved. No process/service was restarted; port 8022 and the existing GUI, audio, Debian PRoot, and user state were not mutated.

## Behavior added

- Added the exact capability `ssh.managed.lifecycle` to `ssh.service.start` and `ssh.service.stop`. Existing `services.manage` alone does not authorize those operations. SSH deployment/rollback remains out of Web scope.
- Web Console exposes start/stop only on catalog resource `network.ssh.managed-8023`. It first requests a state/ownership-checked preview, shows impact, and then applies with a fresh plan ID after confirmation. Each request uses the authenticated loopback API, CSRF, and durable idempotency. The manual `network.ssh.manual-8022` resource remains inspect-only.
- TUI guides the user through start/stop, previews impact and requires typing `yes`, then applies only the exact plan returned by the shared service.
- GTK app shows managed SSH 8023 start/stop controls only for that resource, obtains the preview through a fixed typed bridge command, displays the stop/start impact, and sends the exact plan only after explicit dialog confirmation. The bridge rejects malformed plan IDs and arbitrary commands.
- All interfaces continue using the same service operations and catalog. No CLI/API lifecycle engine was duplicated.

## Tests and validation

All commands were executed in Native Termux. Exit statuses are recorded as observed.

- `python3 -u -m unittest discover -s tests -p 'test_management_http_runtime.py' -v` — 7/7, exit 0.
- `python3 -u -m unittest discover -s tests -p 'test_management_http_adapter.py' -v` — 10/10, exit 0.
- `python3 -u -m unittest discover -s tests -p 'test_management_authorization.py' -v` — 5/5, exit 0.
- `python3 -u -m unittest discover -s tests -p 'test_management_sessions.py' -v` — 9/9, exit 0.
- `python3 -u -m unittest discover -s tests -p 'test_terminal_ui.py' -v` — 12/12, exit 0.
- `python3 -u -m unittest discover -s tests -p 'test_management_desktop_bridge.py' -v` — 7/7, exit 0.
- GTK source compiled with `clang -Wall -Wextra -Werror=implicit-function-declaration ... $(pkg-config --cflags --libs gtk4)` — exit 0.
- `./tx management center install` — exit 0; Native Termux GTK artifact and launcher installed from repository source.
- Installed binary `--self-check` — exit 0; GTK 4.24.1. Installed launcher `--version` — exit 0.
- Complete `unittest` discovery using a 240-second timeout and explicit worker-thread check — **402/402 passed in 125.064 seconds**, no worker threads remained, wrapper exit 0.

## Installed artifact identity

The installer identity file at `$PREFIX/libexec/ternuxx/management-center.identity` matched these hashes:

- GTK source C: `9432b31b4073c7c8fa648f5894de1e3b90d4977b17e9a93180eaf8db660ddd82`
- Typed bridge source: `c5853e07f30fa7adc3d7c7000db9abe5e02eebc2c7d8a5b8e5543f5f98a4076b`
- Installed binary: `81c7bcebf9e4da54708940177df10f78b6d16dac84c22e744f9834e6fb3d16bc`
- Installed launcher: `e6bd1ffb7f001d557202fd66925bb993dd282d488814997a49c3022c0fc6efbd`

## Native live read-only check

- `ssh-preview-start` through the Native Termux bridge — exit 0; returned no plan because the service is already running and starting it would make no change.
- `ssh-preview-stop` through the Native Termux bridge — exit 0; returned a fresh plan for only `ternuxx-sshd`, warning that connected clients may disconnect.
- No `confirmed: true` apply request was issued. Therefore actual live stop/start behavior was not exercised.
- The GTK window was not opened to preserve current X11 focus. Installed binary/self-check proves build/runtime availability, not visual interaction qualification.

## Evidence and remaining scope

Web, TUI, GTK build/install, authorization, bridge contract, and full-suite behavior are verified; Native live preview works. End-to-end browser and GTK GUI interactions are not visually qualified. Managed SSH apply behavior remains fixture-tested only. Service deployment/rollback UI, boot changes, PRoot shortcut management, logs/history, operation progress, and broad deployment/AI categories remain open. P3 is not qualified; P4 remains gated.

## Evidence

Phase: `P3`

This record documents an incremental P3 management-interface capability. It does not claim P3 completion or authorize reboot/service mutation testing.

## Final checks and test iteration

- Repository knowledge validation: `python3 -m tools.repo_knowledge verify` — `VERIFY: 0 findings`, exit 0.
- `git diff --check` — exit 0.
- Python compilation of changed API, TUI, bridge, and focused test modules — exit 0.
- `bash -n lib/management.sh lib/help.sh scripts/install-management-center.sh` — exit 0.
- Python HTML parser accepted the Web Console document — exit 0. No JavaScript runtime/parser was available in this Native Termux environment; browser-side interaction is not claimed verified.
- A prior full-suite run after assigning the dedicated capability reported 4 failures in legacy HTTP/session fixtures still granting `services.manage`. The runtime correctly denied those stale grants. Fixtures were updated to use `ssh.managed.lifecycle`, and a regression now verifies `services.manage` alone is denied. The final full run then passed 402/402.
