# P4 runtime and legacy CLI follow-up — 2026-10-22

Phase: `P4`

## Preservation and legacy CLI retirement

The active Debian installation remains at `$PREFIX/var/lib/proot-distro/containers/debian/rootfs`, device 65086/inode 3240111. The Native read-only PRoot inventory continues to report Debian installed and a host PRoot candidate PID 15279 / parent 14530 with ownership `unverified`. No process was adopted, signaled, or stopped. Native desktop `:1` remains running.

The Ternuxx fixed Debian verifier ran before and after retiring the legacy guest companion. Both returned `status=complete`, with X11 and PulseAudio reachable, DRI3 available, and a verified GLX draw using Zink/Turnip Adreno 825. The post-retirement draw reported 406 frames. The verifier reports `guest_write_command_invoked=false`, no package or service changes, and no host lifecycle start/stop.

The old host and guest Ternux CLI command files and host modules were retired through exact hash-bound previews. On 2026-10-22, their private rollback snapshots and now-empty backup directories were purged after revalidating every file/hash and the Debian rootfs identity, per the owner request to leave no old CLI files behind. The Native `$PREFIX/bin/ternux`, `$PREFIX/lib/ternux`, guest `/usr/local/bin/ternux`, and guest `/usr/bin/ternux` paths are absent. Rollback copies no longer exist. The active Debian rootfs remained device 65086/inode 3240111.

The Ternuxx-supported `tx` source shim and canonical module tree remain present. The prior-name compatibility alias was outside the earlier host CLI retirement scope. No source commit or push was made at that checkpoint.

## Route check

The fixed verifier on Native display `:1` passed with Zink/Turnip Adreno 825, X11/audio reachable, DRI3 available, and GLX draw verified (558 frames before retirement; 406 after). This proves the selected-app `:1` guest route, not a fresh guest replay or an entire desktop workload.

A current read-only probe of standalone `:0` returned `status=partial`: PGUI status says standalone is stopped, X11 is unreachable, DRI3/GLES are unavailable, and GLX draw returned zero frames. The verifier's `observed_display=:0` is the requested environment value; it does not mean an X server answered. I did not stop Native `:1` to start standalone `:0`.

A bounded live nested `tx pgui start --mode nested` ran under Native `:1`. Calling `xfce4-session` directly removed the `startxfce4` warning that an X server was already running; the Xephyr window appeared in the Native `:1` X window tree. `es2_info` reported a Zink/Turnip GLES context. The verifier still reports DRI3 unavailable, no GLES draw verification, no usable GLX RGB visual/fbconfig, and zero GLX frames. Adding Xephyr `+iglx` did not change that result, so the flag was reverted. The current Xephyr backend does not meet the nested GLX draw gate; direct session startup is cleaner, but nested GPU drawing remains unqualified. Ctrl-C exited only the nested launch; afterward `tx pgui status` showed Native `:1` running, standalone `:0` stopped, and no `:2` socket. The existing Native desktop was left running.

Standalone `:0` was not tested because current Native `:1` was running and the documented standalone route requires Native desktop stopped. No `:1` lifecycle change was made. No separate disposable Debian rootfs exists in the PRoot container directory; the only installed distribution is the protected active Debian.

## Checks

- Guest CLI retirement fixture suite: 4/4 passed.
- Host CLI retirement fixture suite: 4/4 passed, including stale-plan refusal, symlink rejection, inode-preserving backup/rollback, and no-overwrite recovery.
- `bash scripts/repo_test.sh`: 685/685 passed in 98.573 seconds on Native Termux.
- `python3 -m py_compile` for retirement tools and `bash -n lib/proot.sh` passed; repository knowledge verification passed with 0 findings.
- After the runtime lifecycle refinement, `tests.test_terminal_broker`: 10/10 passed, including stale-plan refusal, bounded relay, lease release, and no-signal shutdown. No reboot, package mutation, rootfs replacement, active PRoot stop, or current desktop stop occurred.

P4 remains in progress. A fixture-tested `TerminalPTYRuntime` now owns the injected fixed-profile PTY master, relays bounded bytes, applies resize, and releases the writer lease on broker close. The production socket endpoint is not connected to this runtime, and interactive CLI/TUI/Web/GTK clients cannot attach yet. A disposable guest replay, a replacement nested X server that provides a usable GLX visual/draw, standalone `:0` acceptance, and production broker/client transports remain open.

## Evidence

- [P0–P4 phase audit](2026-10-22-p0-p4-phase-audit.md)
- [Interactive PRoot terminal design](../architecture/INTERACTIVE-PROOT-TERMINALS.md)
- Current source: `lib/proot_sessions.py`, `lib/terminal_broker.py`, and the two exact legacy CLI retirement tools.
