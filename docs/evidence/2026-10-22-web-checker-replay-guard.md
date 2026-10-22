# Firefox Web checker replay-target guard

## Finding

`tools/check_web_ui.py` previously hard-coded the `debian` PRoot-Distro alias. PRoot-Distro login may inject a Termux profile into the selected guest, so even a browser check that does not start a Ternuxx terminal session could modify the owner's protected default Debian rootfs.

## Change

The checker now requires an explicit alias matching `ternuxx-replay-*`, refuses the default Debian alias, reports the selected target and possible profile injection, and checks the current SSH public-key-only recovery guidance. `docs/testing/README.md` now documents the replay-only boundary and exact invocation.

## Verification

- `python3 -m py_compile tools/check_web_ui.py tests/test_check_web_ui.py` — PASS.
- `python3 -m unittest tests.test_check_web_ui` — 2 tests PASS (accepted replay alias; rejected default, unrelated, malformed and empty aliases).
- The selected `ternuxx-replay-p4` rootfs contains an executable Firefox ESR binary; no package was installed.
- The real Firefox checker was not launched. SKB `standards/supervisor-operating-model.md` § 5 and `standards/agent-device-testing.md` prohibit agent-driven application UI interaction. The requested visual review still requires owner-operated interaction and remains UNVERIFIED.

No guest was entered, no UI was driven, and no app, SSH credential, service, or boot setting was changed during this guard implementation.
