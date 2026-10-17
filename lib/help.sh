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
  start     Launch native XFCE desktop via Termux:X11
  stop      Stop the native desktop session
  restart   Stop then start
  status    Show current session state
  doctor    Comprehensive diagnosis
  install   Install required packages (explicit consent required)
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
  nativeternux start          # Launch desktop
  nativeternux stop           # Clean up
  nativeternux install --yes  # Install packages (requires consent)
EOF
      ;;
    start)
      cat <<'EOF'
nativeternux start — Launch native XFCE desktop

Uses Termux:X11 + native XFCE packages (no PRoot).

Prerequisites checked:
  - Termux:X11 app is installed
  - xfce4-session and dependencies are installed
  - dbus-launch is available
  - pulseaudio is available

The command will:
  1. Find a free X11 display number
  2. Start Termux:X11 on that display
  3. Wait for the X11 socket
  4. Start dbus and xfce4-session
  5. Track all PIDs for clean stop

Display number is allocated dynamically; :0 is tried first,
then :1, :2, etc. No existing session is clobbered.
EOF
      ;;
    stop)
      cat <<'EOF'
nativeternux stop — Stop the native desktop session

Kills only the processes that nativeternux started
(Termux:X11, dbus-launch, xfce4-session, pulseaudio).
Does not use blanket pkill. Removes only its own socket files.
EOF
      ;;
    install)
      cat <<'EOF'
nativeternux install — Install required packages

Requires explicit --yes flag. Installs:
  - xfce4-session xfce4-panel xfwm4 thunar xfce4-terminal
  - pulseaudio (if not present)
  - dbus-x11 (if not present)

No PRoot packages are touched. No system files are modified.
EOF
      ;;
    check)
      cat <<'EOF'
nativeternux check — Inspect device readiness

Reports which required packages are installed, which commands
are available, and whether Termux:X11 is present.
Does NOT install or modify anything.
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
