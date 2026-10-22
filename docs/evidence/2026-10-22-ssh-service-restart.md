# Managed SSH restart action and live path correction

## Change

Added `ssh.service.restart` as a shared typed operation for the fixed Ternuxx Runit unit. Restart always requires an exact preview plan and confirmation, journals `service.restart`, sends `down` then `up` to the exact service directory, and verifies the resulting running state. Recovery is observation-only and never repeats a restart. 8022 remains explicitly outside scope.

CLI (`tx ssh restart`), TUI, authenticated Web, GTK, catalog and authorization/session policy route through the same operation. The Web/GTK/TUI preview states that active port-8023 clients may disconnect.

## Live issue found and fixed

The first Native preview failed because Termux `sv status ternuxx-sshd` cannot resolve that short name from its service root. Read-only inspection showed `sv status "$PREFIX/var/service/ternuxx-sshd"` reports the full fixed path and the service is running. Lifecycle status/start/stop/restart now pass only `$PREFIX/var/service/ternuxx-sshd`; output parsing accepts that exact absolute path or the exact service ID and rejects sibling names.

## Verification

- Native focused suites: 156 tests passed (Runit lifecycle, service recovery, management API/catalog/session/HTTP authorization, TUI and GTK bridge).
- Native `python3 -m py_compile` passed for changed Python modules; `bash -n scripts/install-management-center.sh` passed.
- `git diff --check` passed.
- Native `./tx ssh inspect` observed managed `ternuxx-sshd` running, configuration valid, fixed source/installed definition hashes equal, loopback `127.0.0.1:8023`; authentication was not tested by this read.
- Native `./tx ssh restart` returned a read-only exact preview with `current_status=running`, `target_status=running`, and `requires_confirmation=true`. No `sv down/up` action was run.
- `scripts/install-management-center.sh` built and installed the GTK binary, launcher and application-menu entry. Installed identity records source C SHA-256 `347262bfc66fb04a58888adfe2ae0185cdf974018728131c43551e4c3fbd2554`, bridge SHA-256 `7879b0577714f21c075d60cf3eebfe5eb15dd92472f335706e3287fec48b93fc`, and binary SHA-256 `6b90740267099ae2ac91cb9ba9982a874652e2d54dba58a155e69f0ef37bb920`.

## Limits

No service restart was applied so the existing 8023 login and any clients remain undisturbed. SSH key enrollment/recovery and password lifecycle, service boot/Wake Lock policy controls, and fresh-boot qualification remain open. GTK artifact deployment is verified; this specific new restart button was not manually clicked or visually reviewed.
