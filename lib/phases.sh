# =============================================================================
#  Ternuxx package setup
#
#  Installation always begins with a repository and dependency preview.
#  Nothing is installed unless the caller explicitly passes --yes.
# =============================================================================
# shellcheck source=lib/core.sh
. "$(dirname "${BASH_SOURCE[0]}")/core.sh"

# Native workstation packages include graphical diagnostics and X11 test
# utilities requested by the owner. Heavy applications and Mesa providers stay
# optional and are handled separately.
_NT_BASE_PACKAGES=(
  proot-distro
  termux-x11-nightly
  dbus
  pulseaudio
  python
  xfce4-session
  xfce4-panel
  xfce4-settings
  xfwm4
  xfdesktop
  xfconf
  thunar
  xfce4-terminal
  glmark2
  xorg-server-xvfb
  xdotool
)

_nt_package_installed() {
  local status
  status="$(dpkg-query -W -f='${Status}' "$1" 2>/dev/null || true)"
  [ "$status" = "install ok installed" ]
}

_nt_package_index_fresh() {
  local lists="${PREFIX:-/data/data/com.termux/files/usr}/var/lib/apt/lists"
  local now marker path stamp epoch newest matches
  now="$(date -u +%s 2>/dev/null)" || return 1
  [[ "$now" =~ ^[0-9]+$ ]] || return 1
  for marker in termux-main termux-x11; do
    newest=""
    matches=0
    for path in "$lists"/*"$marker"*_InRelease; do
      [ -f "$path" ] || continue
      matches=1
      stamp="$(awk 'index($0, "Date: ")==1 {sub(/^Date: /, ""); print; exit}' "$path" 2>/dev/null)"
      [ -n "$stamp" ] || continue
      epoch="$(date -u -d "$stamp" +%s 2>/dev/null || true)"
      [[ "$epoch" =~ ^[0-9]+$ ]] || continue
      if [ -z "$newest" ] || [ "$epoch" -gt "$newest" ]; then
        newest="$epoch"
      fi
    done
    [ "$matches" = "1" ] && [ -n "$newest" ] || {
      printf 'Missing or unreadable signed package index: %s\n' "$marker" >&2
      return 1
    }
    if [ "$newest" -gt "$((now + 900))" ] || [ "$((now - newest))" -gt 1209600 ]; then
      printf 'Package index is stale or future-dated: %s (epoch %s)\n' "$marker" "$newest" >&2
      return 1
    fi
  done
}

_nt_package_candidate_from_official_repo() {
  local package="$1" expected_repo="$2" policy candidate
  policy="$(apt-cache policy "$package" 2>/dev/null)" || return 1
  candidate="$(printf '%s\n' "$policy" | sed -n 's/^[[:space:]]*Candidate: //p' | head -1)"
  [ -n "$candidate" ] && [ "$candidate" != "(none)" ] || return 1
  printf '%s\n' "$policy" | awk -v version="$candidate" -v repo="$expected_repo" '
    $1 == "***" && $2 == version && $3 ~ /^[0-9]+$/ { in_candidate=1; next }
    $1 == version && $2 ~ /^[0-9]+$/ { in_candidate=1; next }
    in_candidate && $1 ~ /^[0-9]+$/ && $2 ~ /^https?:/ {
      if (index($0, repo)) found=1
      in_candidate=0
      next
    }
    END { exit !found }
  ' || return 1
  printf '%s\n' "$candidate"
}

_nt_make_install_plan() {
  local package expected_repo candidate simulation
  _NT_PLAN_PACKAGES=()
  _NT_PLAN_VERSIONS=()
  _NT_PLAN_TRANSACTION=()

  for package in "${_NT_BASE_PACKAGES[@]}"; do
    if _nt_package_installed "$package"; then
      continue
    fi
    case "$package" in
      dbus|pulseaudio|python|proot-distro) expected_repo="termux-main" ;;
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
  if ! printf '%s\n' "$simulation" | grep -q '^Inst '; then
    nt_fail "APT did not return a complete install transaction; refusing to preview or apply it. No packages were changed."
    return 1
  fi
  local index expected_version
  for index in "${!_NT_PLAN_PACKAGES[@]}"; do
    package="${_NT_PLAN_PACKAGES[$index]}"
    expected_version="${_NT_PLAN_VERSIONS[$index]#*=}"
    if ! printf '%s\n' "$simulation" | awk -v package="$package" -v version="$expected_version" '$1 == "Inst" && $2 == package && (($3 == "(" && $4 == version) || (substr($3, 1, 1) == "(" && substr($3, 2) == version)) { found=1 } END { exit !found }'; then
      nt_fail "APT transaction did not include the reviewed candidate for $package; refusing it. No packages were changed."
      return 1
    fi
  done
  _NT_PLAN_TRANSACTION=()
  while IFS=' ' read -r package expected_version; do
    [ -n "$package" ] && _NT_PLAN_TRANSACTION+=("$package=$expected_version")
  done < <(printf '%s\n' "$simulation" | awk '$1 == "Inst" { version=$3; if (version == "(") version=$4; if (substr(version, 1, 1) == "(") version=substr(version, 2); print $2, version }')
  _NT_PLAN_SIMULATION="$simulation"
}

_nt_compute_plan_id() {
  python3 - "$_NT_PLAN_SIMULATION" "${_NT_PLAN_VERSIONS[@]}" -- "${_NT_PLAN_TRANSACTION[@]}" <<'PYPLANID'
import hashlib, json, sys
simulation = sys.argv[1]
separator = sys.argv.index("--", 2)
record = {"requested_candidates": sys.argv[2:separator], "resolved_transaction": sys.argv[separator + 1:], "apt_simulation": simulation}
print(hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).hexdigest())
PYPLANID
}

_nt_reviewed_preview_matches() {
  local plan_id="$1"
  [[ "$plan_id" =~ ^[0-9a-f]{64}$ ]] || return 1
  python3 - "$TERNUXX_STATE_DIR/install-transactions" "$plan_id" "$HOME" "$_NT_PLAN_SIMULATION" "${_NT_PLAN_VERSIONS[@]}" -- "${_NT_PLAN_TRANSACTION[@]}" <<'PYCHECKPREVIEW'
import hashlib, json, os, pathlib, stat, sys
root = pathlib.Path(sys.argv[1])
plan_id, home, simulation = sys.argv[2:5]
separator = sys.argv.index("--", 5)
requested = sys.argv[5:separator]
transaction = sys.argv[separator + 1:]
try:
    resolved_root = root.resolve(strict=True)
    resolved_home = pathlib.Path(home).resolve(strict=True)
    if resolved_root == resolved_home or resolved_home not in resolved_root.parents:
        raise ValueError("preview directory is outside HOME")
    root_metadata = root.lstat()
    if stat.S_ISLNK(root_metadata.st_mode) or not stat.S_ISDIR(root_metadata.st_mode):
        raise ValueError("preview directory is not a regular directory")
    if stat.S_IMODE(root_metadata.st_mode) != 0o700:
        raise ValueError("preview directory permissions are not private")
    expected = {"requested_candidates": requested, "resolved_transaction": transaction, "apt_simulation": simulation}
    digest = hashlib.sha256(json.dumps(expected, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if digest != plan_id:
        raise ValueError("current transaction does not match the supplied preview ID")
    for path in resolved_root.glob("*.json"):
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            continue
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if record.get("schema_version") != 1 or record.get("outcome") != "preview":
            continue
        fields = {key: record.get(key) for key in expected}
        actual = hashlib.sha256(json.dumps(fields, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if actual == plan_id and record.get("plan_id") == plan_id:
            if stat.S_IMODE(metadata.st_mode) != 0o600:
                raise ValueError("preview record permissions are not private")
            print(path)
            raise SystemExit(0)
except (OSError, ValueError) as exc:
    print(f"{exc}", file=sys.stderr)
sys.exit(1)
PYCHECKPREVIEW
}

_nt_apply_install_transaction() {
  apt-get --assume-yes --no-install-recommends --no-remove --no-upgrade install "${_NT_PLAN_TRANSACTION[@]}"
}

_nt_install_state_dir_safe() {
  python3 - "$TERNUXX_STATE_DIR" "$HOME" <<'PYSTATEPATH'
import pathlib, stat, sys
state = pathlib.Path(sys.argv[1]).expanduser()
home = pathlib.Path(sys.argv[2]).expanduser().resolve()
try:
    absolute = pathlib.Path(state.absolute())
    relative = absolute.relative_to(home)
    current = home
    for part in relative.parts:
        current = current / part
        try:
            if stat.S_ISLNK(current.lstat().st_mode):
                raise ValueError("state path contains a symbolic link")
        except FileNotFoundError:
            pass
    resolved = state.resolve(strict=False)
    if resolved == home or home not in resolved.parents:
        raise ValueError("state path must be inside HOME")
except (OSError, ValueError) as exc:
    print(f"unsafe installer state path: {exc}", file=sys.stderr)
    sys.exit(1)
PYSTATEPATH
}

_nt_write_install_record() {
  local outcome="$1" root stamp target
  _nt_install_state_dir_safe || return 1
  root="${TERNUXX_STATE_DIR}/install-transactions"
  mkdir -p "$root" || return 1
  chmod 700 "$root" || return 1
  stamp="$(date -u +%Y%m%dT%H%M%SZ)" || return 1
  target="$root/${stamp}-$$-${RANDOM}-${outcome}.json"
  local plan_id
  plan_id="$( _nt_compute_plan_id )" || return 1
  python3 - "$target" "$outcome" "$plan_id" "$_NT_PLAN_SIMULATION" "${_NT_PLAN_VERSIONS[@]}" -- "${_NT_PLAN_TRANSACTION[@]}" <<'PYRECORD'
import json, os, pathlib, sys, tempfile
path = pathlib.Path(sys.argv[1])
outcome = sys.argv[2]
plan_id = sys.argv[3]
simulation = sys.argv[4]
separator = sys.argv.index("--", 5)
requested = sys.argv[5:separator]
transaction = sys.argv[separator + 1:]
record = {
    "schema_version": 1,
    "recorded_at_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    "outcome": outcome,
    "plan_id": plan_id,
    "requested_candidates": requested,
    "resolved_transaction": transaction,
    "apt_simulation": simulation,
}
path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
fd, temporary = tempfile.mkstemp(prefix=".install-transaction-", dir=path.parent)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
finally:
    try:
        os.unlink(temporary)
    except FileNotFoundError:
        pass
PYRECORD
}

nt_cmd_install() {
  local apply=0 consent=0 arg plan_id=""
  while [ $# -gt 0 ]; do
    arg="$1"; shift
    case "$arg" in
      --yes) apply=1; consent=1 ;;
      --plan-id) [ $# -gt 0 ] || { nt_fail "--plan-id requires an ID from a saved preview."; return 2; }; plan_id="$1"; shift ;;
      --preview) apply=0 ;;
      *) nt_fail "Unknown install option: $arg"; return 2 ;;
    esac
  done

  nt_require_termux || return 1
  if [ "$consent" = "1" ] && [ -z "$plan_id" ]; then
    nt_fail "Apply requires the ID from a saved preview: run 'tx install --preview', review it, then pass --yes --plan-id ID."
    return 2
  fi
  if [ -n "$plan_id" ] && [ "$consent" != "1" ]; then
    nt_fail "--plan-id requires explicit --yes consent after preview review."
    return 2
  fi
  if [ "$consent" = "1" ] && [[ ! "$plan_id" =~ ^[0-9a-f]{64}$ ]]; then
    nt_fail "--plan-id must be the 64-character ID printed by a saved preview."
    return 2
  fi
  for tool in apt-cache apt-get dpkg-query date; do
    nt_require_command "$tool" || return 1
  done

  if ! _nt_package_index_fresh; then
    nt_fail "Official Termux package indexes are missing or older than 14 days. Refresh them with your normal Termux package workflow, then review the preview again. Ternuxx did not refresh them."
    return 1
  fi

  if ! _nt_make_install_plan; then
    return 1
  fi

  if [ ${#_NT_PLAN_PACKAGES[@]} -eq 0 ]; then
    nt_ok "Ternuxx base workstation packages are already installed."
    if [ "$TERNUXX_JSON" = "1" ]; then
      printf '{"install":"already_installed","packages_changed":false}\n'
    fi
    return 0
  fi

  nt_info "Ternuxx base workstation package preview (official Termux repositories only):"
  printf '  %s\n' "${_NT_PLAN_VERSIONS[@]}"
  nt_info "Resolved APT transaction (all new packages, including dependencies):"
  printf '  %s\n' "${_NT_PLAN_TRANSACTION[@]}"
  nt_info "APT simulation only; no package state has changed."
  printf '%s\n' "$_NT_PLAN_SIMULATION"
  nt_info "No upgrades, removals, recommendations, or repository changes are allowed by this plan."

  if [ "$apply" != "1" ]; then
    local record_path="${TERNUXX_STATE_DIR}/install-transactions"
    if _nt_write_install_record preview; then
      nt_info "Full dependency preview recorded under $record_path."
    else
      nt_fail "Could not persist the dependency preview; refusing to report a reproducible plan."
      return 1
    fi
    local plan_id
    plan_id="$( _nt_compute_plan_id )" || return 1
    nt_info "Preview ID: $plan_id"
    nt_info "After reviewing this exact transaction, apply with: tx install --yes --plan-id $plan_id"
    if [ "$TERNUXX_JSON" = "1" ]; then
      local package_json
      package_json="$(nt_json_array "${_NT_PLAN_VERSIONS[@]}")"
      local transaction_json
      transaction_json="$(nt_json_array "${_NT_PLAN_TRANSACTION[@]}")"
      printf '{"install":"preview","plan_id":"%s","packages":%s,"transaction":%s}\n' "$plan_id" "$package_json" "$transaction_json"
    fi
    return 0
  fi

  # Rebuild the plan immediately before applying it and require an exact
  # match to a private saved preview explicitly named by the caller.
  if ! _nt_package_index_fresh || ! _nt_make_install_plan; then
    nt_fail "Package state changed since the preview. Review a fresh preview; nothing was installed."
    return 1
  fi
  if ! _nt_reviewed_preview_matches "$plan_id" >/dev/null; then
    nt_fail "The saved preview is missing, invalid, or does not match the current APT transaction. Nothing was installed; create and review a fresh preview."
    return 1
  fi
  if [ ${#_NT_PLAN_PACKAGES[@]} -eq 0 ]; then
    nt_ok "Ternuxx base workstation packages are already installed."
    return 0
  fi

  nt_step "Installing the reviewed Ternuxx base workstation packages (preview $plan_id)..."
  _nt_apply_install_transaction || {
    nt_fail "APT reported an installation failure. Review its output before retrying."
    return 1
  }
  if ! _nt_write_install_record applied; then
    nt_warn "Packages were installed, but the transaction record could not be persisted under $TERNUXX_STATE_DIR/install-transactions."
  fi
  nt_ok "Ternuxx base workstation packages installed. The Termux:X11 Android app still must be installed separately if absent."
  if [ "$TERNUXX_JSON" = "1" ]; then
    local package_json
    package_json="$(nt_json_array "${_NT_PLAN_VERSIONS[@]}")"
    local transaction_json
    transaction_json="$(nt_json_array "${_NT_PLAN_TRANSACTION[@]}")"
    printf '{"install":"complete","packages":%s,"transaction":%s}\n' "$package_json" "$transaction_json"
  fi
  return 0
}
