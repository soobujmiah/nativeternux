# P3 off-home transport candidate review — 2026-10-18

**Result:** documentary candidate review only. No provider selected; no account, network, VPN, SSH, or service configuration was changed.

## Live Ternuxx constraints already recorded

- The owner-approved product requirement is optional off-home access, disabled by default. [ADR-0013](../architecture/decisions/ADR-0013-owner-controlled-remote-access.md) requires an owner-selected authenticated private transport and keeps local management services loopback-only.
- The latest native Doctor reports the independent SSH configuration on port 8022 as wildcard-bound with password authentication enabled; listener owner and external reachability are unknown. Managed Ternuxx SSH on port 8023 is loopback-only, running under Runit, but listener ownership remains unverified. See [P3 current gate evidence](2026-10-18-p3-current-readonly-gate-latest.json) and [SSH ownership evidence](2026-10-18-p3-ssh-current-session-recheck.json).
- The earlier read-only Tailscale runtime check found the Android app installed but no Termux CLI or process; VPN/tailnet connection state was unknown. See [remote access live recheck](2026-10-18-p3-remote-access-current-recheck-0238.json). This is dated state, not a current connection claim.

## Official documentation reviewed

- [Connect to devices](https://tailscale.com/kb/1452/connect-to-devices), checked 2026-10-18: Tailscale supplies private connectivity, but the destination still needs a running service and policy permitting the client-to-device connection.
- [Manage client preferences](https://tailscale.com/docs/features/client/manage-preferences), checked 2026-10-18: incoming connections are allowed by default, subject to tailnet policy; Android does not expose the documented client-side “block incoming connections” control.
- [Tailscale CLI support](https://tailscale.com/kb/1080/cli), checked 2026-10-18: the CLI is not supported on Android.
- [Tailscale Serve command](https://tailscale.com/docs/reference/tailscale-cli/serve), checked 2026-10-18: Serve can forward tailnet TCP traffic to a local service, but it is a CLI capability, so its presence cannot be inferred from the Android app alone.

## Assessment

Tailscale remains a possible **transport candidate** because the Android client can participate in a tailnet and documented connections can reach services on an allowed device. This is an inference from the official device-connection and client-policy documentation; it is not a live reachability test.

The Android app alone does not supply the Termux CLI/Serve relay assumed by a loopback-only 8023 design. Directly reusing wildcard/password SSH on 8022 would preserve a broad bind and its current ownership/authentication uncertainty, so this review does not recommend or enable that path. A Ternuxx off-home adapter still needs a reviewed service boundary, client allowlist/policy, strong service authentication, Android background behavior evidence, and an owner-selected client/provider. Public Funnel and router port forwarding are outside the selected design.

## Outcome / next evidence

- Provider selection: **pending owner choice**.
- Tailnet identity/connection and incoming policy: **unknown**.
- Android-to-Termux service delivery: **not tested**.
- `tailscale serve` availability on Android: **not available through the documented Android CLI**; no alternative app-level relay was verified.
- No account sign-in, VPN enablement, port probe, service change, or external connection was attempted.


## 2026-10-18 06:50 UTC native package recheck

- Android package-manager queries report `com.tailscale.ipn` installed/enabled (versionCode 298177930). Native Termux `tailscale` and `tailscaled` commands are absent and an exact `tailscaled` process-name query found no match. This does not establish whether the Android VPN is connected or what tailnet policy applies.
- No sign-in, VPN toggle, peer/client inspection, route probe, or network action was performed. The Android app's presence alone still does not provide the Termux-side authenticated relay needed for Ternuxx's loopback-only management service. Sanitized paired Shizuku/Tailscale probe: [Android add-on state](2026-10-18-p3-android-addon-state-0650.json).
