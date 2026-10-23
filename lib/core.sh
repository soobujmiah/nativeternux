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
  # nt_json_object <key1> <val1> [key2 val2 ...]; all values are JSON strings.
  python3 - "$@" <<'PYJSON'
import json, sys
args=sys.argv[1:]
if len(args) % 2:
    raise SystemExit("nt_json_object requires key/value pairs")
print(json.dumps(dict(zip(args[::2], args[1::2])), ensure_ascii=False))
PYJSON
}

nt_json_array() {
  # nt_json_array <item1> <item2> ...; items are JSON strings.
  python3 - "$@" <<'PYJSON'
import json, sys
print(json.dumps(sys.argv[1:], ensure_ascii=False))
PYJSON
}

nt_json_object_typed() {
  # nt_json_object_typed <key1> <json-value1> [key2 json-value2 ...]
  # Use only for internal callers that already hold validated JSON values.
  python3 - "$@" <<'PYJSON'
import json, sys
args=sys.argv[1:]
if len(args) % 2:
    raise SystemExit("nt_json_object_typed requires key/value pairs")
result={}
for key, raw in zip(args[::2], args[1::2]):
    result[key]=json.loads(raw)
print(json.dumps(result, ensure_ascii=False))
PYJSON
}

# --- Library loader -------------------------------------------------------
declare -A _NT_LOADED
_nt_use() {
  local lib="$1"
  [ -n "${_NT_LOADED[$lib]:-}" ] && return 0
  local f="${_TN_LIB_DIR:-}/${lib}.sh"
  if [ -f "$f" ]; then
    # shellcheck disable=SC1090
    . "$f"
    _NT_LOADED["$lib"]=1
    return 0
  fi
  nt_die "Internal error: library '$lib' not found at $f" 99
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
  python3 - "$f" "$key" <<'PYSTATE'
import json, sys
with open(sys.argv[1], encoding="utf-8") as stream:
    data=json.load(stream)
value=data.get(sys.argv[2], "")
if isinstance(value, str):
    sys.stdout.write(value + "\n")
else:
    print(json.dumps(value, ensure_ascii=False))
PYSTATE
}

nt_state_set() {
  local key="$1" value="$2"
  local f; f="$(_nt_state_file)"
  python3 - "$f" "$key" "$value" <<'PYSTATE'
import json, os, sys, tempfile
path, key, value=sys.argv[1:]
parent=os.path.dirname(path)
os.makedirs(parent, mode=0o700, exist_ok=True)
try:
    with open(path, encoding="utf-8") as stream:
        data=json.load(stream)
    if not isinstance(data, dict):
        raise ValueError("state root must be a JSON object")
except FileNotFoundError:
    data={}
data[key]=value
fd, temporary=tempfile.mkstemp(prefix=".state.", dir=parent)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    try:
        mode=os.stat(path).st_mode & 0o777
    except FileNotFoundError:
        mode=0o600
    os.chmod(temporary, mode)
    os.replace(temporary, path)
    dir_fd=os.open(parent, os.O_RDONLY)
    try: os.fsync(dir_fd)
    finally: os.close(dir_fd)
except BaseException:
    try: os.unlink(temporary)
    except FileNotFoundError: pass
    raise
PYSTATE
}

nt_state_has() {
  local key="$1"
  local val; val="$(nt_state_get "$key")" || return 1
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
  # Native Ternuxx has one stable default display. Never silently move an
  # existing workstation session to another display when :1 is occupied.
  local tmp_root="${TMPDIR:-/data/data/com.termux/files/usr/tmp}"
  local helper="${_TN_LIB_DIR:-}/x11_display.py" result
  if [ -f "$helper" ]; then
    result="$(python3 "$helper" "$tmp_root" 1 2>/dev/null)" || result=busy
    [ "$result" = "available" ] || { printf '%s\n' error; return 1; }
  else
    [ ! -e "$tmp_root/.X1-lock" ] && [ ! -e "$tmp_root/.X11-unix/X1" ] || { printf '%s\n' error; return 1; }
  fi
  printf '%s\n' 1
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
