# =============================================================================
#  nativeternux — help system
# =============================================================================
# shellcheck source=lib/core.sh
. "$(dirname "${BASH_SOURCE[0]}")/core.sh"

nt_help() {
  local cmd="${1:-}"
  case "$cmd" in
    "")
      cat <<'EOF'
nativeternux — Native Termux desktop

Usage:
  nativeternux <command> [options]

Commands:
  check     Inspect device, report what's installed and what's missing
  info      Show system information (renderer, Vulkan, packages)
  start     Check readiness (desktop launch not implemented)
  stop      Stop stub (process teardown not implemented)
  restart   Restart stub (desktop lifecycle not implemented)
  status    Inspect related process status (ownership not tracked)
  doctor    Comprehensive diagnosis
  install   Preview package requirements (no install yet)
  guides    Show documentation links
  help      Show this help
  --version Show version

Options:
  --json      Machine-readable output
  --verbose   Extra diagnostic messages
  --quiet     Suppress informational output
  --help, -h  Show help

Examples:
  nativeternux check          # See what's ready
  nativeternux info           # Renderer + Vulkan details
  nativeternux start          # Check readiness only
  nativeternux stop           # Stop stub; no processes are killed
  nativeternux install --yes  # Preview only; no packages are installed
EOF
      ;;
    start)
      cat <<'EOF'
nativeternux start — Native XFCE readiness stub

This milestone does not launch Termux:X11 or XFCE. It only checks prerequisites.

Prerequisites checked:
  - Termux:X11 app is installed
  - xfce4-session and dependencies are installed
  - dbus-launch is available
  - pulseaudio is available

The command currently checks whether prerequisites exist and reports readiness.
No processes, sockets, or package state are changed.
EOF
      ;;
    stop)
      cat <<'EOF'
nativeternux stop — Stop stub

Process tracking and session teardown are not implemented. This command does
not kill processes or remove socket files.
EOF
      ;;
    install)
      cat <<'EOF'
nativeternux install — Package preview stub

Requires explicit --yes to show the preview. No packages are installed.
  - The planned package set is not yet verified or installed.

This command makes no package or system-file changes.
EOF
      ;;
    check)
      cat <<'EOF'
nativeternux check — Inspect device readiness

Reports which required packages are installed, which commands
are available, and whether Termux:X11 is present.
Does NOT install packages or modify files. Diagnostic tools may query device interfaces.
EOF
      ;;
    doctor)
      cat <<'EOF'
nativeternux doctor — Full diagnostic

Combines check + renderer info + Vulkan info + process status.
Provides structured JSON output with --json flag.
EOF
      ;;
    info)
      cat <<'EOF'
nativeternux info — System information

Shows renderer string, Vulkan adapter info, package status,
and current session state. Read-only.
EOF
      ;;
    guides)
      printf '%s\n' \
        'NativeTernux guides:' \
        '  Installation: https://soobujmiah.github.io/nativeternux/docs/INSTALLATION.html' \
        '  Architecture: https://soobujmiah.github.io/nativeternux/docs/ARCHITECTURE.html' \
        '  Troubleshooting: https://soobujmiah.github.io/nativeternux/docs/TROUBLESHOOTING.html' \
        '' 'Open these links in a browser. This command does not install anything.'
      ;;
    *)
      nt_fail "No help available for '$cmd'. Run 'nativeternux help' for usage."
      return 1
      ;;
  esac
}

nt_cmd_help() { nt_help "${1:-}"; }
