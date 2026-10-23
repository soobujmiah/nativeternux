from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DebianInstallCliTests(unittest.TestCase):
    def _run(self, *args: str, json_mode: bool = False) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            capture = Path(temporary) / "setup-args"
            script = r'''
set -u
_TN_LIB_DIR="$1"
export _TN_LIB_DIR
export CAPTURE="$2"
export TERNUXX_QUIET=0 TERNUXX_VERBOSE=0
export REAL_PYTHON="$3"
shift 3
. "$_TN_LIB_DIR/core.sh"
. "$_TN_LIB_DIR/phases.sh"
nt_require_termux() { return 0; }
nt_require_command() { return 0; }
python3() {
  if [ "${1:-}" = -c ]; then
    case "$*" in
      *resolve_proot_guest_user*) printf 'sbj\n' ;;
      *) printf 'human summary\n' ;;
    esac
    return 0
  fi
  case "${1:-}" in
    */proot_setup_present.py) command "$REAL_PYTHON" "$@"; return $? ;;
  esac
  printf '%s\n' "$@" > "$CAPTURE"
  printf '{"status":"preview","plan_id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","operation":{"guest_release":{"VERSION_ID":"13","VERSION_CODENAME":"trixie"},"guest_user":"sbj","rootfs":"/guest/debian/rootfs","observed_graphics_files":{},"guest_mutations":[],"package_changes":[],"service_changes":[]}}\n'
}
_nt_install_debian "$@"
status=$?
printf '\n--SETUP-ARGS--\n'
cat "$CAPTURE" 2>/dev/null || true
exit "$status"
'''
            env = {**os.environ, "TERNUXX_JSON": "1" if json_mode else "0"}
            return subprocess.run(
                ["bash", "-c", script, "test", str(ROOT / "lib"), str(capture), sys.executable, *args],
                text=True, capture_output=True, env=env, check=False,
            )

    def test_preview_defaults_to_existing_guest_and_formats_result(self) -> None:
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Existing Debian guest profile preview", result.stdout)
        self.assertIn("Guest files, packages, services: unchanged", result.stdout)
        self.assertIn("adopt-preview", result.stdout)
        self.assertIn("--user\nsbj", result.stdout)

    def test_apply_requires_explicit_yes(self) -> None:
        result = self._run("apply", "a" * 64)
        self.assertEqual(result.returncode, 2)
        self.assertIn("explicit --yes", result.stderr)
        self.assertNotIn("adopt\n", result.stdout)

    def test_apply_passes_exact_plan_and_confirmation_to_adoption_adapter(self) -> None:
        result = self._run("apply", "a" * 64, "--yes", "--user", "sbj")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("adopt\n", result.stdout)
        self.assertIn("--plan-id\n" + "a" * 64, result.stdout)
        self.assertIn("--yes", result.stdout)

    def test_json_mode_keeps_structured_preview(self) -> None:
        result = self._run("preview", "--user", "sbj", json_mode=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"status":"preview"', result.stdout)


if __name__ == "__main__":
    unittest.main()
