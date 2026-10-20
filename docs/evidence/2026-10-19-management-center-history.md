# Management Center recovery history reader — 2026-10-19

## Implementation

Work continued in Native Termux `$HOME/ternuxx`, on `main` at HEAD `69e378eb33247678437bda4b2de9ab25f6bcb91d`. Existing dirty changes were preserved.

The Web Console, TUI, and GTK app now expose the existing typed, read-only `recovery.status` operation as operation history, scoped to the catalog recovery resource. TUI uses `h` for history and `v` for the advanced structured detail view. The GTK app has a contextual history button. Web renders the journal's existing sanitized operation metadata with `textContent`. Service log files remain unavailable; the UI reports that honestly.

The shared CLI/API journal reader was reused. No parallel lifecycle or history backend was created.

## Verification

- `python3 -u -m unittest discover -s tests -p 'test_management_http_runtime.py' -v` — 7/7, exit 0. Includes authenticated Web recovery-history dispatch.
- `python3 -u -m unittest discover -s tests -p 'test_terminal_ui.py' -v` — 14/14, exit 0. Includes history resource restriction and full detail rendering.
- `python3 -u -m unittest discover -s tests -p 'test_management_desktop_bridge.py' -v` — 8/8, exit 0. Includes typed read-only history operation.
- GTK4 source build — exit 0.
- `./tx management center install` — exit 0; GTK binary installed from current repository source.
- Installed binary `--self-check` — exit 0; GTK 4.24.1.
- Full Native Termux `unittest` discovery with 240-second timeout and explicit remaining-thread check — **405/405 passed in 127.417 seconds**, zero remaining worker threads, wrapper exit 0.
- `python3 -m tools.repo_knowledge verify` — `VERIFY: 0 findings`, exit 0.
- `git diff --check` — exit 0.

## Actual Native Termux integration

- A real authenticated request to an ephemeral loopback Web-mode server called the shared management service's `recovery.status`. Response: `ok=true`, `read_only=true`, zero records in the isolated temporary fixture home, zero unresolved, exit 0. The server bound to loopback and closed cleanly.
- `python3 scripts/management_desktop_bridge.py history` called the Native Termux shared service and returned the actual private journal summary: 20 records, 0 unresolved, `read_only=true`, exit 0. Raw journal details were not copied to evidence.

Installed GTK identity file matches:

- GTK C source: `f4ed4af926fbec65b0655030c3a68590f3cde9e473691aea090af711861245ed`
- Bridge source: `06fd6175e6b8d5cb3fdea4b88f1a33039de755b0fac4cdfe9e46047fcf942548`
- Installed binary: `87acf74192d81bdd0217a5171972ee0a0ee99d8655b34367144d6ebd17adaf3d`
- Installed launcher: `e6bd1ffb7f001d557202fd66925bb993dd282d488814997a49c3022c0fc6efbd`

The GTK window and browser were not opened. Visual interaction and actual on-screen action feedback remain unverified. Service logs and operation progress remain unavailable. No service start/stop apply, GUI launch, Activity request, reboot, or PRoot action occurred.

## Evidence

Phase: `P3`

This is incremental P3 interface progress, not P3 completion or P4 qualification.
