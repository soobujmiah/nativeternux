# Verified local recovery route for managed SSH 8023

## Observation

On 2026-10-22, the existing Debian PRoot SSH client authenticated to the Native Termux managed SSH service at `127.0.0.1:8023` using the client's already configured key. The client alias resolves to the Termux account and holds the identity selection; no private-key path or material was copied into this evidence.

The effective managed-service policy reports `AuthenticationMethods publickey`, `PasswordAuthentication no`, and `KbdInteractiveAuthentication no`. A password cannot authenticate to this service. The verified command shape for this existing client is:

```sh
ssh -p 8023 termux
```

The client test used noninteractive public-key authentication. The observed Ed25519 host key from loopback port 8023 was compared with the Native Termux `sshd` configured public host key, and the authenticated retry used strict host-key checking. The command exited 0.

## Scope and preservation

- Port 8023 remained bound to loopback; no external access was configured.
- Port 8022 remained the separate owner-managed development channel.
- No password, key, `authorized_keys`, SSH configuration, service state, boot policy, or Wake Lock setting was changed.
- No private key, public authorization entry, fingerprint value, or credential was recorded here.

This proves recovery for the already configured PRoot client on this device. It does not prove access from another device or recover an unknown/lost private key. Key enrollment/removal UI, password/recovery controls, and per-service boot/Wake Lock settings remain open.
