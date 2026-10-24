# P4 replay guest retire/restore recheck

Date: 2026-10-24 (Dhaka)
Phase: `P4`
Native checkout: `main`, source revision `c91ab9d`
Target: receipt-owned `ternuxx-replay-p4` Debian Trixie container only

## Preconditions and preview

The fresh-install receipt identified the alias as `fresh-preview-confirmed-install`, with package-version evidence recorded and all requested packages verified. The guest had no managed session or PRoot process. Its container identity was device/inode `65086/101280`; rootfs identity was `65086/5078478`. Before the operation, `/etc/os-release` SHA-256 was `e249e69c32d81350fdd6b05ac5575255f14e380ba14b8454acea14e49f088bfa`, and its package-version record SHA-256 was `5835f69ca5f67f2d3e98e2e1a8237edb0c4447c4dece3b9423a44be79ba0c234`.

The shared CLI returned an exact retire preview (plan `45321a4eb1b33db18edda05ab09e3f3ab25a2817ef411b53b009f68940b6c4fa`) targeting only this alias. The reviewed effect was a same-filesystem atomic move into private Native Ternuxx state; no guest files would be deleted.

## Evidence

- Exact-plan retire returned `status: retired`, backup ID `828be2f7987243fca847675668dfb326`, `files_deleted: false`, and the original container inode.
- Restore preview bound the same container/rootfs identity (plan `ac82d36ecc15ff1befabb1ae358874bd11c06d5099dc9d0ec42f77b595ea77d9`). Exact-plan restore returned `status: restored`, `files_deleted: false`.
- Post-restore checks found the same container/rootfs device and inode, the same release-file hash, and the same package-version-record hash. The replay guest was idle and listed again by PRoot-Distro.
- During this check, observed PRoot processes 590, 27030, and 32668 all had `/containers/debian/rootfs` as cwd. The default Debian rootfs inode remained `3240111`; its legacy ICD SHA-256 remained `6e03d879305dcae3371a212bc7e9dcb23a5e42e9bf741966fe455972baa0b145`, and its canonical Ternuxx ICD path remained absent. No default guest process was targeted.

This verifies the current installed CLI/shared-service rename and restore path for one idle, Ternuxx-owned replay guest. It does not qualify every client dialog, distro, GUI/audio workload, clean-device installation, or long-term package artifact retention.

Implementation: `replay retirement service`, `CLI route`. Prior cross-client evidence: [Web replay retirement](2026-10-22-web-replay-guest-retirement.md), [GTK replay dialog](2026-10-22-gtk-replay-guest-dialog-review.md).
