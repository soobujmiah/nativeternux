# =============================================================================
#  NativeTernux package setup
#
#  Installation always begins with a repository and dependency preview.
#  Nothing is installed unless the caller explicitly passes --yes.
# =============================================================================
# shellcheck source=lib/core.sh
. "$(dirname "${BASH_SOURCE[0]}")/core.sh"

# Keep the base desktop small and predictable. Browser/editor packages remain
# optional and are handled by later application profiles.
_NT_BASE_PACKAGES=(
  termux-x11-nightly
  dbus
  pulseaudio
  xfce4-session
  xfce4-panel
  xfce4-settings
  xfwm4
  xfdesktop
  xfconf
  thunar
  xfce4-terminal
)

_nt_package_installed() {
  local status
  status="$(dpkg-query -W -f='${Status}' "$1" 2>/dev/null || true)"
  [ "$status" = "install ok installed" ]
}

_nt_package_index_fresh() {
  local lists="${PREFIX:-/data/data/com.termux/files/usr}/var/lib/apt/lists"
  python3 - "$lists" <<'PY'
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
import sys

lists = Path(sys.argv[1])
required = ("termux-main", "termux-x11")
now = datetime.now(timezone.utc)
for marker in required:
    matches = list(lists.glob(f"*{marker}*_InRelease"))
    if not matches:
        print(f"Missing signed package index: {marker}", file=sys.stderr)
        raise SystemExit(1)
    newest = None
    for path in matches:
        try:
            for line in path.read_text(errors="replace").splitlines():
                if line.startswith("Date: "):
                    stamp = parsedate_to_datetime(line[6:]).astimezone(timezone.utc)
                    newest = max(newest, stamp) if newest else stamp
                    break
        except (OSError, ValueError, TypeError):
            continue
    if newest is None:
        print(f"Could not read signed index date: {marker}", file=sys.stderr)
        raise SystemExit(1)
    age = now - newest
    if age.total_seconds() < -900 or age.days > 14:
        print(f"Package index is stale or future-dated: {marker} ({newest.isoformat()})", file=sys.stderr)
        raise SystemExit(1)
PY
}

_nt_package_candidate_from_official_repo() {
  local package="$1" expected_repo="$2" policy candidate
  policy="$(apt-cache policy "$package" 2>/dev/null)" || return 1
  candidate="$(printf '%s\n' "$policy" | sed -n 's/^[[:space:]]*Candidate: //p' | head -1)"
  [ -n "$candidate" ] && [ "$candidate" != "(none)" ] || return 1
  printf '%s\n' "$policy" | awk -v version="$candidate" -v repo="$expected_repo" \
    '$1 == version && $2 ~ /^[0-9]+$/ && index($0, repo) { found=1 } END { exit !found }' || return 1
  printf '%s\n' "$candidate"
}

_nt_make_install_plan() {
  local package expected_repo candidate simulation
  _NT_PLAN_PACKAGES=()
  _NT_PLAN_VERSIONS=()

  for package in "${_NT_BASE_PACKAGES[@]}"; do
    if _nt_package_installed "$package"; then
      continue
    fi
    case "$package" in
      dbus|pulseaudio) expected_repo="termux-main" ;;
      *) expected_repo="termux-x11" ;;
    esac
    candidate="$(_nt_package_candidate_from_official_repo "$package" "$expected_repo")" || {
      nt_fail "No $expected_repo candidate found for $package. Enable/check the official repository and refresh package indexes yourself."
      return 1
    }
    _NT_PLAN_PACKAGES+=("$package")
    _NT_PLAN_VERSIONS+=("$package=$candidate")
  done

  if [ ${#_NT_PLAN_PACKAGES[@]} -eq 0 ]; then
    _NT_PLAN_SIMULATION=""
    return 0
  fi

  simulation="$(apt-get -s --no-install-recommends --no-remove --no-upgrade install "${_NT_PLAN_PACKAGES[@]}" 2>&1)" || {
    nt_fail "APT could not resolve the preview. No packages were changed."
    printf '%s\n' "$simulation" >&2
    return 1
  }
  if printf '%s\n' "$simulation" | grep -Eq '^(Remv|The following packages will be REMOVED:)'; then
    nt_fail "The proposed transaction removes packages; refusing it. No packages were changed."
    return 1
  fi
  if ! printf '%s\n' "$simulation" | awk '/^(Inst|Conf) / && $0 !~ /termux-main|termux-x11/ { bad=1 } END { exit bad ? 1 : 0 }'; then
    nt_fail "The dependency plan includes a package outside the official Termux repositories; refusing it."
    return 1
  fi
  _NT_PLAN_SIMULATION="$simulation"
}

nt_cmd_install() {
  local apply=0 arg
  while [ $# -gt 0 ]; do
    arg="$1"; shift
    case "$arg" in
      --yes) apply=1 ;;
      --preview) apply=0 ;;
      *) nt_fail "Unknown install option: $arg"; return 2 ;;
    esac
  done

  nt_require_termux || return 1
  for tool in apt-cache apt-get dpkg-query python3; do
    nt_require_command "$tool" || return 1
  done

  if ! _nt_package_index_fresh; then
    nt_fail "Official Termux package indexes are missing or older than 14 days. Refresh them with your normal Termux package workflow, then review the preview again. NativeTernux did not refresh them."
    return 1
  fi

  if ! _nt_make_install_plan; then
    return 1
  fi

  if [ ${#_NT_PLAN_PACKAGES[@]} -eq 0 ]; then
    nt_ok "NativeTernux base desktop packages are already installed."
    if [ "$NATIVERNUX_JSON" = "1" ]; then
      python3 -c 'import json; print(json.dumps({"install":"already_installed","packages_changed":False}))'
    fi
    return 0
  fi

  nt_info "NativeTernux base desktop package preview (official Termux repositories only):"
  printf '  %s\n' "${_NT_PLAN_VERSIONS[@]}"
  printf '%s\n' "$(_NT_PLAN_SIMULATION)"
  nt_info "No upgrades, removals, recommendations, or repository changes are allowed by this plan."

  if [ "$apply" != "1" ]; then
    nt_info "Preview only. Re-run 'nativeternux install --yes' to approve this package transaction."
    if [ "$NATIVERNUX_JSON" = "1" ]; then
      python3 -c 'import json,sys; print(json.dumps({"install":"preview","packages":sys.argv[1:]}))' "${_NT_PLAN_VERSIONS[@]}"
    fi
    return 0
  fi

  # Rebuild the plan immediately before applying it. The caller's explicit
  # --yes is the consent; APT is still blocked from removals and upgrades.
  if ! _nt_package_index_fresh || ! _nt_make_install_plan; then
    nt_fail "Package state changed since the preview. Review a fresh preview; nothing was installed."
    return 1
  fi
  if [ ${#_NT_PLAN_PACKAGES[@]} -eq 0 ]; then
    nt_ok "NativeTernux base desktop packages are already installed."
    return 0
  fi

  nt_step "Installing the approved NativeTernux base desktop packages..."
  apt-get --assume-yes --no-install-recommends --no-remove --no-upgrade install "${_NT_PLAN_PACKAGES[@]}" || {
    nt_fail "APT reported an installation failure. Review its output before retrying."
    return 1
  }
  nt_ok "NativeTernux base desktop packages installed. The Termux:X11 Android app still must be installed separately if absent."
  if [ "$NATIVERNUX_JSON" = "1" ]; then
    python3 -c 'import json,sys; print(json.dumps({"install":"complete","packages":sys.argv[1:]}))' "${_NT_PLAN_VERSIONS[@]}"
  fi
  return 0
}
