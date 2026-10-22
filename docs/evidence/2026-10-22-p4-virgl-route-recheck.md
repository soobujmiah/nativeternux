# P4 VirGL replay route and cleanup recheck

Phase: `P4`
Gate: PARTIAL — rendering qualified; service cleanup remains blocked by socket-client visibility.

## Evidence

## Scope

I completed the receipt-bound VirGL route in the isolated replay guest
ternuxx-replay-p4-retry on Native display :1. The default Debian rootfs
was not selected. The Native Ternuxx VirGL lifecycle recovered only its exact
stale owner record/socket before starting a matching server. No process was
signaled outside that manager. The owner's existing PRoot session was not
stopped or adopted.

## Implementation

- lib/proot_diagnostics.py now exposes one exact replay receipt/rootfs
  verifier used both by guest verification and the launcher. Non-Debian names
  must match ternuxx-replay-*, their private receipt must attest package
  verification and recorded versions, and the live rootfs identity must match.
- lib/launch.sh permits a verified replay alias through tx db using
  proot-distro's isolated mode and shared TMP only. Replay aliases receive
  graphics environment only in the selected child process; no
  persistent proot-distro --env profile entries are written. The existing
  default Debian profile baseline and device binds remain unchanged.
- VirGL child commands now use LIBGL_ALWAYS_SOFTWARE=true,
  GALLIUM_DRIVER=virpipe, and the display-specific shared-TMP
  VTEST_SOCKET_NAME. The verification probe uses the same variables and
  takes its VirGL renderer from the bounded GLX draw, since glxinfo -B
  does not work reliably in this VirGL context. This matches Mesa's
  upstream virpipe test configuration:
  https://cgit.freedesktop.org/mesa/mesa/commit/?id=b3b82fe8ea1f7d02c93513920143cba2fe145b6c
- Regression coverage confirms receipt denial prevents PRoot launch, backend
  values stay process-scoped for replay aliases, and the default Debian
  baseline remains unchanged.

## Live results

- Before adding LIBGL_ALWAYS_SOFTWARE=true, the explicit VirGL request
  selected Zink/Turnip. This was a real backend mismatch, not a pass.
- After the fix, tx proot verify --distro ternuxx-replay-p4-retry
  --guest-user sbj --display :1 --backend virgl --json returned
  status=complete: renderer virgl (Adreno (TM) 825), GLX draw
  verified, 1,246 frames on the first run and 584 on the final recheck;
  X11 and PulseAudio were reachable.
- The installed tx entrypoint ran a separate bounded glxgears draw through
  tx db's isolated replay route: renderer virgl (Adreno (TM) 825),
  1,027 frames in 5 seconds. The host status matched the Ternuxx-owned
  server record and socket.
- A final bounded Zink recheck on the same replay alias also returned
  status=complete with zink Vulkan 1.4 (Adreno TM 825, MESA_TURNIP)
  and 512 GLX frames. Starting VirGL did not change the qualified Zink path.
- The verifier reports read_only=false for the whole operation because
  the proot-distro login may rewrite its generated guest profile. Its fixed
  probe changed no packages and invoked no guest write command.
- The default Debian rootfs remains a separate target. No reset/reinstall,
  user-data deletion, or unverified PRoot signaling occurred.

## Cleanup result and remaining issue

I ran tx virgl stop --display :1 after the bounded draws. It failed closed:
Android lsof returned no socket-owner PID, while fuser could not read
/proc/net/unix (Permission denied). The service therefore remains
running with its exact Native Ternuxx owner record; it was not killed by PID or
by any fallback. This is the current live state. Do not claim service cleanup
or stop it outside the lifecycle manager.

This is a lifecycle client-visibility limitation, not a VirGL rendering
failure. P4 remains in progress until safe exact cleanup/client detection is
qualified, followed by the remaining Web mutation/client parity, wider
Native-independence injection, and complete source/installed/runtime audit.

## Reproduction

From Native Termux, after confirming the replay receipt:

    tx db --user sbj --distro ternuxx-replay-p4-retry --backend virgl --display :1 -- timeout -s TERM 6s glxgears -info -geometry 160x100
    tx proot verify --distro ternuxx-replay-p4-retry --guest-user sbj --display :1 --backend virgl --json
    tx virgl status --display :1
    tx virgl stop --display :1
