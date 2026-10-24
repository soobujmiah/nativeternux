# Management API

Ternuxx exposes one local management service for Native Termux operations. The CLI and TUI call it directly, the GTK client uses a narrow local bridge, and the Web UI uses an authenticated loopback adapter. The caller label is diagnostic metadata, not authentication.

The service rejects unknown operations and validates typed arguments. HTTP sessions receive only explicitly granted capabilities. Mutating operations require the applicable preview and exact plan ID. No endpoint accepts arbitrary shell commands, caller-provided environment maps, unrestricted file paths, or ADB forwarding. The sole file-path handoff is the read-only directory-tree action: one selected regular file or directory below Native HOME, no symlink traversal, fixed argv, depth/entry/output bounds, and filenames only.

Cron clients submit form-level typed create values to `cron.jobs.mutation.preview`. The shared service generates registry IDs and ownership metadata, applies safe defaults, validates the schedule, and stores the exact plan for later confirmation. Supported schedule types are `cron` expressions, fixed `interval`s, daily or specific `calendar` entries, and `one_time` UTC-offset datetimes. CLI, TUI, Web, and GTK use this same mutation path.

PRoot and guest-terminal operations have been retired from the service contract. The prior multi-provider contract is preserved in [historical API documentation](../history/MANAGEMENT-API-pre-native-only-2026-10-24.md). Current operation and capability definitions live in `lib/management_service.py`, `lib/management_authorization.py`, `lib/management_sessions.py`, and `lib/management_http_runtime.py`.

The Web adapter binds to loopback. Browser choices are Android or installed Native Termux browsers. See the [Native-only migration audit](../evidence/2026-10-24-native-only-proot-removal-audit.md) for retirement scope and verification evidence.
