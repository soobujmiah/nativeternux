# Existing Debian adoption metadata refresh and rollback

Date: 2026-10-24 (Dhaka local)
Phase: P4, in progress

## Change

The previous Native adoption record described the current Debian rootfs but carried an older setup-manifest hash. Previously the refresh preview was blocked because no rollback path existed. Same-rootfs refresh now binds the exact previous-record hash, writes the original bytes to a private mode-0600 backup before replacing metadata, and records the backup ID in the refreshed record. Rootfs identity changes remain blocked. The rollback path has a separate preview and apply; it requires the current record hash, backup hash, and rootfs device/inode to match the preview.

No guest files, package state, services, user/password credentials, processes, or display state are part of either operation.

## Fixture evidence

The proot setup tests verify stale metadata refresh, exact prior-byte backup, rollback preview/apply, restoration of byte-identical previous metadata, and unchanged guest-file digest. Presentation tests verify that refresh and recovery commands are shown to users. The CLI help contract covers the new recovery commands. The full Native suite passed 922 tests with one skip in 145.509 seconds; document inventory and repository-knowledge checks also passed.

## Native live evidence

The read-only preview selected existing Debian Trixie user sbj, rootfs device/inode 65086/3240111, all 50/50 manifest packages installed, one held package, and zero guest/package/service changes. Exact refresh plan 5639407fcb813a38a6d45678e8b850099a7353d0d78942d3b2758a023cdbb4c9 was applied through tx install debian apply ... --yes.

The exact previous-record backup ID is 0911df75f0a859bc0eec23d36d1dacdf5dab971a5fd64d55403f241f70d0e264. Follow-up tx proot setup status reports adopted, package_baseline: matches, and the same rootfs identity. Rollback preview 550ba24b5c0b9810cde3572783844b37718d3278dcae79da1229bbd541983a0c succeeded; it was not applied because the refreshed metadata is now current. proot-distro ps still reported the pre-existing Debian login PID 590; no session command was run.

This qualifies Native-side adoption metadata refresh and fixture rollback only. It does not migrate or repair guest configuration, install missing packages, prove graphics acceleration, or close the remaining P4 client-parity and clean-install requirements.
