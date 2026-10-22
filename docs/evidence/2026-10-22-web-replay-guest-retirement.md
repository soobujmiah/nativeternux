# Authenticated Web replay-guest retirement and restore — 2026-10-22

Phase: P4
Gate: PASS for the authenticated loopback HTTP API lifecycle; Web page rendering remains unverified.

## Live Native evidence

Ran the real loopback management_http_runtime Web-mode server from Native Termux over SSH 8022 and sent HTTP requests over urllib to its bound 127.0.0.1 port. The test created a one-time in-memory bootstrap secret, authenticated a Web session with the proot.guest.manage capability, and used bearer, CSRF, and idempotency headers. The server and credentials were process-local and were not saved.

Before mutation, the shared session inventory showed no running managed session on the exact target. The private fresh-guest receipt and rootfs identity were validated for ternuxx-replay-p4. Through the authenticated API, the test completed:

1. proot.setup.retire.preview
2. proot.setup.retire.apply with the exact returned plan
3. proot.setup.restore.preview for the returned backup
4. proot.setup.restore.apply with the exact returned plan

The API returned retired then restored; files_deleted was false. The test compared the container and rootfs device/inode pairs, the container manifest hash, and hashes for available /etc/os-release, /etc/passwd, and /home/sbj/.bashrc sentinels. All matched before and after. The default Debian rootfs identity and etc/profile.d/termux-profile.sh hash also matched.

## Scope

This verifies the authenticated Web-mode HTTP transport, operation dispatch, CSRF/idempotency requirements, and exact replay-guest lifecycle through the shared service. It does not verify browser-rendered controls, visual presentation, unauthenticated/under-capability denial behavior, or the GTK replay-guest dialog. No browser was launched. The existing Debian rootfs and the owner's active PRoot session were not targeted.
