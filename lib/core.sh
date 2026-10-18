# =============================================================================
#  Ternuxx — core library
#  Shared utilities, I/O helpers, version info, and JSON/CLI framework.
#  Every other library sources this first.
#
#  Copyright (c) 2026 Sobuj Miah (@soobujmiah)
#  License: not yet selected; see README.md.
#  https://github.com/soobujmiah/ternuxx
# =============================================================================

# --- Logging ------------------------------------------------------------
nt_log() {
  # Logging is disabled in the read-only scaffold. A future mutating command
  # must opt into a scoped log policy before this starts writing files.
  return 0
}

nt_debug()  { [ "$TERNUXX_VERBOSE" = "1" ] && nt_log "DEBUG" "$@" || true; }
nt_info()   { nt_log "INFO"  "$@"; [ "$TERNUXX_QUIET" != "1" ] && printf '[INFO]  %s\n' "$*" >&2; }
nt_ok()     { nt_log "OK"    "$@"; [ "$TERNUXX_QUIET" != "1" ] && printf '\033[01;32m[OK]    %s\033[0m\n' "$*" >&2; }
nt_warn()   { nt_log "WARN"  "$@"; [ "$TERNUXX_QUIET" != "1" ] && printf '\033[01;33m[WARN]  %s\033[0m\n' "$*" >&2; }
nt_fail()   { nt_log "FAIL"  "$@"; [ "$TERNUXX_QUIET" != "1" ] && printf '\033[01;31m[FAIL]  %s\033[0m\n' "$*" >&2; }
nt_step()   { nt_log "STEP"  "$@"; [ "$TERNUXX_QUIET" != "1" ] && printf '\033[01;34m[STEP]  %s\033[0m\n' "$*" >&2; }

nt_die() {
  local msg="$1"; local code="${2:-1}"
  nt_fail "$msg"
  [ "$TERNUXX_JSON" = "1" ] && nt_json_object "error" "fatal" "message" "$msg"
  exit "$code"
}

# --- JSON output helper -------------------------------------------------
nt_json_object() {
  # nt_json_object <key1> <val1> [key2 val2 ...]
  local pairs=("$@")
  local out="{"
  local first=1
  for ((i=0; i<${#pairs[@]}; i+=2)); do
    [ $first -eq 0 ] && out+=", "
    out+="\"${pairs[$i]}\":\"${pairs[$((i+1))]}\""
    first=0
  done
  out+="}"
  echo "$out"
}

nt_json_array() {
  # nt_json_array <item1> <item2> ...
  local out="["
  local first=1
  for item in "$@"; do
    [ $first -eq 0 ] && out+=", "
    out+="\"$item\""
    first=0
  done
  out+="]"
  echo "$out"
}

# --- State file ---------------------------------------------------------
_nt_state_file() {
  # Resolve only. Readers must not create the state directory as a side effect.
  echo "$TERNUXX_STATE_DIR/state.json"
}

nt_state_get() {
  local key="$1"
  local f; f="$(_nt_state_file)"
  [ -f "$f" ] || return 1
  python3 -c "import json,sys; d=json.load(open('$f')); print(d.get('$key',''))" 2>/dev/null || true
}

nt_state_set() {
  local key="$1" value="$2"
  local f; f="$(_nt_state_file)"
  mkdir -p "$TERNUXX_STATE_DIR" 2>/dev/null || true
  if [ -f "$f" ]; then
    python3 -c "
import json,sys
d=json.load(open('$f'))
d['$key']='$value'
json.dump(d,open('$f','w'),indent=2)
" 2>/dev/null || true
  else
    printf '{\n  "%s": "%s"\n}\n' "$key" "$value" > "$f"
  fi
}

nt_state_has() {
  local key="$1"
  local val; val="$(nt_state_get "$key")"
  [ -n "$val" ]
}

# --- Requirement checks -------------------------------------------------
nt_require_command() {
  local cmd="$1" desc="${2:-$cmd}"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    nt_fail "Required command not found: $cmd ($desc)"
    return 1
  fi
  return 0
}

nt_require_termux() {
  # PRoot may see /data/data/com.termux through a bind mount. Require the
  # native Termux environment markers instead of treating that path as proof.
  if [ -z "${TERMUX_VERSION:-}" ] || [ "${PREFIX:-}" != "/data/data/com.termux/files/usr" ]; then
    nt_fail "This operation requires the native Termux shell (TERMUX_VERSION and PREFIX do not identify it). Do not run native package or desktop lifecycle commands from Debian PRoot."
    return 1
  fi
  return 0
}

# --- Display number allocation ------------------------------------------
nt_find_free_display() {
  # :0 is the existing Ternux PRoot allocation on the owner device. Prefer
  # native Termux displays :1 through :10; recover only positively stale,
  # same-UID lock/socket pairs. Ambiguous artifacts stay unavailable.
  local max_try=10
  local tmp_root="${TMPDIR:-/data/data/com.termux/files/usr/tmp}"
  local helper="${_TN_LIB_DIR:-}/x11_display.py" result
  for n in $(seq 1 "$max_try"); do
    if [ -f "$helper" ]; then
      result="$(python3 "$helper" "$tmp_root" "$n" 2>/dev/null)" || continue
      [ "$result" = "recovered" ] && nt_warn "Recovered stale Termux:X11 socket and lock for :$n."
      printf '%s\n' "$n"
      return 0
    fi
    [ ! -e "$tmp_root/.X$n-lock" ] || continue
    [ ! -e "$tmp_root/.X11-unix/X$n" ] || continue
    printf '%s\n' "$n"
    return 0
  done
  printf '%s\n' "error"
  return 1
}

# --- Process tracking ---------------------------------------------------
_nt_track_pid() {
  # Record a PID we started so we can stop it later
  local pid="$1" label="$2"
  mkdir -p "$TERNUXX_STATE_DIR" 2>/dev/null || true
  echo "$pid $label" >> "$TERNUXX_STATE_DIR/pids.log" 2>/dev/null || true
}

_nt_get_pids() {
  # Read tracked PIDs
  cat "$TERNUXX_STATE_DIR/pids.log" 2>/dev/null || true
}

_nt_clear_pids() {
  rm -f "$TERNUXX_STATE_DIR/pids.log" 2>/dev/null || true
}

# --- Renderer detection -------------------------------------------------
_nt_detect_renderer() {
  # Returns the OpenGL renderer string if glxinfo is available, else "unknown"
  if command -v glxinfo >/dev/null 2>&1; then
    glxinfo -B 2>/dev/null | awk -F': ' '/OpenGL renderer string/{print $2; found=1; exit} END{if(!found) exit 1}' || echo "unknown"
  else
    echo "unknown (glxinfo not available)"
  fi
}

_nt_detect_vulkan() {
  # Returns vulkaninfo summary or "unknown"
  if command -v vulkaninfo >/dev/null 2>&1; then
    vulkaninfo --summary 2>/dev/null | head -20 || echo "unknown"
  else
    echo "unknown (vulkaninfo not available)"
  fi
}
