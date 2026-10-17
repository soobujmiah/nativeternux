# =============================================================================
#  nativeternux — core library
#  Shared utilities, I/O helpers, version info, and JSON/CLI framework.
#  Every other library sources this first.
#
#  Copyright (c) 2026 Sobuj Miah (@soobujmiah)
#  License: not yet selected; see README.md.
#  https://github.com/soobujmiah/nativeternux
# =============================================================================

# --- Logging ------------------------------------------------------------
nt_log() {
  # Logging is disabled in the read-only scaffold. A future mutating command
  # must opt into a scoped log policy before this starts writing files.
  return 0
}

nt_debug()  { [ "$NATIVERNUX_VERBOSE" = "1" ] && nt_log "DEBUG" "$@" || true; }
nt_info()   { nt_log "INFO"  "$@"; [ "$NATIVERNUX_QUIET" != "1" ] && printf '[INFO]  %s\n' "$*" >&2; }
nt_ok()     { nt_log "OK"    "$@"; [ "$NATIVERNUX_QUIET" != "1" ] && printf '\033[01;32m[OK]    %s\033[0m\n' "$*" >&2; }
nt_warn()   { nt_log "WARN"  "$@"; [ "$NATIVERNUX_QUIET" != "1" ] && printf '\033[01;33m[WARN]  %s\033[0m\n' "$*" >&2; }
nt_fail()   { nt_log "FAIL"  "$@"; [ "$NATIVERNUX_QUIET" != "1" ] && printf '\033[01;31m[FAIL]  %s\033[0m\n' "$*" >&2; }
nt_step()   { nt_log "STEP"  "$@"; [ "$NATIVERNUX_QUIET" != "1" ] && printf '\033[01;34m[STEP]  %s\033[0m\n' "$*" >&2; }

nt_die() {
  local msg="$1"; local code="${2:-1}"
  nt_fail "$msg"
  [ "$NATIVERNUX_JSON" = "1" ] && nt_json_object "error" "fatal" "message" "$msg"
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
  echo "$NATIVERNUX_STATE_DIR/state.json"
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
  mkdir -p "$NATIVERNUX_STATE_DIR" 2>/dev/null || true
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
  # Check we're in a Termux environment
  if [ -z "${TERMUX_VERSION:-}" ] && [ ! -d "/data/data/com.termux" ]; then
    # Allow in JSON mode for testing
    [ "$NATIVERNUX_JSON" = "1" ] && return 0
    nt_fail "Not running in Termux. Install Termux from F-Droid or GitHub."
    return 1
  fi
  return 0
}

# --- Display number allocation ------------------------------------------
nt_find_free_display() {
  # Find next available X11 display number, avoiding conflicts with existing
  # Termux:X11 sessions. Returns the display number or "error".
  local max_try=10
  local existing
  existing="$(ls /data/data/com.termux/files/usr/tmp/.X11-unix/ 2>/dev/null | sed 's/X//' || true)"
  for n in $(seq 0 $max_try); do
    local conflict=0
    for ex in $existing; do
      [ "$ex" = "$n" ] && { conflict=1; break; }
    done
    [ $conflict -eq 0 ] && echo "$n" && return 0
  done
  echo "error"
  return 1
}

# --- Process tracking ---------------------------------------------------
_nt_track_pid() {
  # Record a PID we started so we can stop it later
  local pid="$1" label="$2"
  mkdir -p "$NATIVERNUX_STATE_DIR" 2>/dev/null || true
  echo "$pid $label" >> "$NATIVERNUX_STATE_DIR/pids.log" 2>/dev/null || true
}

_nt_get_pids() {
  # Read tracked PIDs
  cat "$NATIVERNUX_STATE_DIR/pids.log" 2>/dev/null || true
}

_nt_clear_pids() {
  rm -f "$NATIVERNUX_STATE_DIR/pids.log" 2>/dev/null || true
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
