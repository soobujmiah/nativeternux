# GTK terminal picker review — 2026-10-22

Phase: P4; gate remains in progress.

Native SSH 8022 source adds an asynchronous bridge-backed chooser in the installed GTK Management Center. It offers a new fixed Debian terminal and attach buttons only for running, Ternuxx-verified `debian-interactive` sessions. The VTE child invokes the shared terminal CLI, which revalidates the session and handles preview, confirmation, relay and detach. The stop preview bridge accepts only the verified isolated-probe SIGTERM or interactive-terminal SIGHUP contracts and shows profile, exact session, signal, scope and impact before confirmation.

The Native GTK app was rebuilt and installed with `scripts/install-management-center.sh`; its recorded source and bridge hashes matched the current checkout, and `tx-management-center --self-check` reported GTK 4.24.1 and VTE 0.84.1. C syntax and warnings check (`clang -fsyntax-only -Wall -Wextra` with GTK/VTE pkg-config flags) and `git diff --check` passed. Focused bridge tests passed 27/27, including filtering foreign sessions and the interactive stop contract. The private replay broker and installed GTK app were launched on existing Native display :1. A focused app-window screenshot visually confirmed the category, resource, detail and scrollable action layout. The private bridge returned no attach options before any replay session was started, as expected.

The GUI interaction did not complete a start/attach/stop lifecycle: X11 injected pointer coordinates did not consistently map to the focused window, so the chooser and VTE content were not visually qualified in this review. CLI, TUI and Web had already exercised the separate replay guest lifecycle; that evidence does not establish GTK input behavior. The focused screenshot also showed a machine-oriented Debian status report, which remains a presentation issue.

The replay broker used a private state directory and the completed separate `ternuxx-replay-p4` guest. The existing Debian rootfs, Codex PRoot session, 8022/8023 SSH services and Native desktop were not modified. Optional Native `scrot` 2.0.0 was installed to capture only the focused app window. Temporary screenshots were removed after inspection; no image of the desktop or guest output is retained in the repository.

Full Native regression after the GTK and bridge changes: `bash scripts/repo_test.sh` — **752/752 passed** in 103.584 seconds. Document inventory: **75/389** read, zero broken local links; `tools/audit_documents.py --check` passed. Remaining repository audit coverage is explicitly open.
