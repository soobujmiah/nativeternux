# Dynamic PRoot guest-account selection

Date: 2026-10-24 (Dhaka local)
Phase: P4, in progress

## Change

Removed the owner-specific `sbj` assumption from the Debian interactive broker profile and both Ternuxx XFCE guest launch paths. The shared profile now resolves the sole ordinary account from the selected Debian rootfs `/etc/passwd`, returns that account in the preview, binds it into the exact preview plan, and checks the account again before start. Session ownership verification reads the selected user from its own recorded fixed argv and compares the resulting guest UID/GID with `/etc/passwd`. More than one eligible ordinary account causes the interactive profile to report unavailable instead of picking arbitrarily. `tx pgui` and its XFCE wrapper perform the same read-only account discovery before launch.

No guest package, account, configuration, process, display, or service was changed. The active guest and desktop were not started or stopped by this work.

## Verification

- Live Native `./tx mng proot start --profile debian-interactive` returned the existing Debian Trixie account `sbj`, rootfs identity (device 65086, inode 3240111), and plan `plan-42d3ed404bef61e296d52c263a897faa6abd346c125340e9b79f9226f78c6b99`. The direct profile preview returned the same plan. Both were read-only; no apply or login occurred.
- Fixture tests use the non-default username `workuser`, confirm the selected account reaches the login argv, verify a username change invalidates the plan, and ensure an ambiguous guest is refused.
- The combined focused PRoot-session, GUI-route, management-service, HTTP-adapter, and terminal-broker tests passed 122/122 after the final rootfs identity race check.
- Full Native test suite: 911 passed, 1 skipped in 105.825 seconds.
- `python3 -m tools.repo_knowledge verify`: 0 findings. Document inventory: 117/448 read, 0 broken links. `bash -n` for both launchers, `git diff --check`, and a production-source search for account hard-codes passed.

## Limits

The unique-account resolver is implemented for the existing Debian interactive/GUI entrypoints. It intentionally fails closed for multiple ordinary guest users; an explicit shared-client account selector remains open. The fresh Debian Trixie installer accepts a user via `--user` and securely prompts for the sudo password during apply. Multi-distro account setup, selecting accounts from TUI/Web/GTK, and general existing-guest package/config migration remain unfinished. This evidence does not qualify visible GUI rendering, audio, GPU acceleration, or a clean install.
