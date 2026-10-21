# Web browser selection - 2026-10-22

## Behavior

tx web now presents available launch targets: Android's default browser, a detected Native Termux browser, Debian PRoot Firefox ESR when installed, and Auto-select. Auto-select prefers Native Termux, then PRoot, then Android. The command accepts --browser android|native|proot|auto to skip the interactive prompt. Browser detection is read-only; the command does not install packages.

The PRoot path launches the existing allowlisted firefox-esr through scripts/proot-x11-app.sh, so it uses the configured Native X11 display and standard PRoot GUI environment. The browser command receives only the loopback Web URL; the bootstrap secret remains on the clipboard.

## Native verification

- Runtime and source checkout: Native Termux over SSH 8022, $HOME/ternuxx.
- Native browser candidates: none found.
- Debian PRoot browser: /usr/bin/firefox-esr detected.
- ./tx web --browser proot --port 8767 started the loopback Web server and launched Debian PRoot Firefox ESR at the local URL.
- ./tx web --port 8768 displayed the browser chooser; selecting option 2 started the same PRoot browser path.
- ./tx web --browser auto --port 8769 selected PRoot Firefox ESR because no Native browser executable was detected.
- Both temporary Web listeners were stopped after the launch check. Existing tx db guest/rootfs were not modified.
- python3 -m py_compile lib/management_http_runtime.py, bash -n lib/management.sh, and git diff --check passed. No test suite was run.

## Limits

Auto-select was exercised on the live device and opened PRoot Firefox ESR because no Native browser executable was detected. Android was not launched during verification; no Native browser executable was detected. PRoot browser detection currently covers the repository's supported Debian Firefox ESR app.
