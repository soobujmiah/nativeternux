# Timezone preference in management clients — 2026-10-20

Phase: `P3` (incremental; no phase gate marked complete)

## Behavior

TUI and Native GTK can save the Ternuxx timezone preference through the typed
`timezone.set` operation. TUI first reads the current value and available IANA
zones, rejects a name not in the runtime list, and asks for explicit confirmation.
GTK presents a preference form and sends its value through the local typed
bridge. Neither flow changes Android's system timezone.

Web can inspect the current timezone and list available zones. The authenticated
browser session does not receive `timezone.manage`; the page contains no
`timezone.set` action. Other Web mutation rules are unchanged.

## Verification

Native Termux through SSH 8022:

- `bash scripts/repo_test.sh` — 586/586 passed.
- Focused TUI, GTK bridge, HTTP runtime, and timezone suites — 58/58 passed.
- GTK compile with `clang -O2 -Wall -Wextra -Werror -fsyntax-only ...` — passed.
- `git diff --check` — passed; repo-knowledge verify — 0 findings.
- Live `tx mng timezone status` — available, default `Asia/Dhaka`, preference not explicitly configured, Android packed tzdata version `2025a`.
- Live `tx mng timezone list` — 596 zones returned.
- `./tx mng center install` — passed. Installed GTK binary SHA-256:
  `a768b25d568e136d534c2a3d6e65b9eb00fbbb66b99d9170cab643fd1d8e2c26`.

The GUI session was not restarted, so an already running management window still
uses its previous binary until the owner next launches it. Browser layout and GTK
controls were not visually operated. The Codex, SSH 8022, and desktop sessions
remain running. This slice did not change the stored timezone preference.

## Remaining scope

The updated [capability matrix](../architecture/CAPABILITY-MATRIX.md) records
these action boundaries. Web timezone mutation remains disabled by design in
this iteration; full management-client parity and P3 visual/recovery/boot gates
remain open.
