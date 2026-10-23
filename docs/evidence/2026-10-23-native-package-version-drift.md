# Native Termux package version drift — 2026-10-23

## Scope

Read-only comparison on the owner-authorized Native Termux runtime. The 16 direct
packages in `lib/phases.sh` are present. This check compares installed versions
with candidates from the currently signed Termux indexes; it does not change
package state. On the same runtime, `./tx install --preview` reported that the
base workstation packages were already installed.

## Result

| Package | Installed | Current candidate |
|---|---:|---:|
| `proot-distro` | 5.9.0 | 5.10.2 |
| `termux-x11-nightly` | 1.03.01-6 | 1.03.01-6 |
| `dbus` | 1.16.2-3 | 1.16.2-3 |
| `pulseaudio` | 17.0-4 | 17.0-5 |
| `python` | 3.14.6-1 | 3.14.8 |
| `xfce4-session` | 4.20.4-1 | 4.20.4-1 |
| `xfce4-panel` | 4.20.8 | 4.20.8 |
| `xfce4-settings` | 4.20.5 | 4.20.5 |
| `xfwm4` | 4.20.0-3 | 4.20.0-3 |
| `xfdesktop` | 4.20.2 | 4.20.2 |
| `xfconf` | 4.20.0 | 4.20.0 |
| `thunar` | 4.20.10 | 4.20.10 |
| `xfce4-terminal` | 1.2.0 | 1.2.0 |
| `glmark2` | 2023.01-3 | 2023.01-3 |
| `xorg-server-xvfb` | 21.1.25-1 | 21.1.25-1 |
| `xdotool` | 4.20260303.1 | 4.20260303.1 |

The exact read-only upgrade simulation for those three direct package changes
resolved one dependency update, `python-ensurepip-wheels` (3.14.6-1 → 3.14.8):
**4 upgraded, 0 newly installed, 0 removed**. No upgrade was applied.

## Interpretation

`tx install` is intentionally no-upgrade and reported all 16 direct packages
already installed. A new preview resolves and records exact versions for that
transaction, but the repository does not yet hold a durable Native package lock
or update lifecycle. Therefore a new installation is preview-bound and
transaction-reproducible, but not guaranteed to resolve the same package
versions on a later date. The current device also has the version drift listed
above.

Recheck the signed package indexes and review a fresh exact preview before any
future package mutation. See [the Native installer implementation](../../lib/phases.sh)
and [the full repository audit](../audit/REPOSITORY-AUDIT.md#continuation-order).

## Evidence

Phase: `P4`

P4 Native package reproducibility audit. The comparison and candidate output are read-only and dated to this runtime.

- [Native package transaction](../../lib/phases.sh)
- [Installation guide](../INSTALLATION.md)
- [Repository audit worklist](../audit/REPOSITORY-AUDIT.md)
