"""Regression tests for shell JSON and state helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "lib/core.sh"


class CoreShellTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-core-shell-")
        self.state_dir = Path(self.temp.name) / "state"
        self.env = os.environ.copy()
        self.env["TERNUXX_STATE_DIR"] = str(self.state_dir)
        self.env["TERNUXX_VERBOSE"] = "0"
        self.env["TERNUXX_QUIET"] = "1"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _call(self, function: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", "-c", '. "$1"; shift; "$@"', "test", str(CORE), function, *args],
            env=self.env, text=True, capture_output=True, check=False, timeout=5,
        )

    def test_json_helpers_escape_arbitrary_strings_and_preserve_types(self) -> None:
        special = 'quote=" slash=\\ newline=\nUnicode=বাংলা 🙂'
        array = self._call("nt_json_array", special, "")
        self.assertEqual(array.returncode, 0, array.stderr)
        self.assertEqual(json.loads(array.stdout), [special, ""])

        obj = self._call("nt_json_object", "message", special, "empty", "")
        self.assertEqual(obj.returncode, 0, obj.stderr)
        self.assertEqual(json.loads(obj.stdout), {"message": special, "empty": ""})

        typed = self._call("nt_json_object_typed", "count", "2", "missing", array.stdout)
        self.assertEqual(typed.returncode, 0, typed.stderr)
        parsed = json.loads(typed.stdout)
        self.assertEqual(parsed, {"count": 2, "missing": [special, ""]})
        self.assertIsInstance(parsed["missing"], list)

    def test_state_helpers_round_trip_special_characters_without_code_interpolation(self) -> None:
        key = "k'\\\nবাংলা"
        value = 'v"\\\nবাংলা 🙂'
        write = self._call("nt_state_set", key, value)
        self.assertEqual(write.returncode, 0, write.stderr)
        path = self.state_dir / "state.json"
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {key: value})
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

        read = self._call("nt_state_get", key)
        self.assertEqual(read.returncode, 0, read.stderr)
        self.assertEqual(read.stdout, value + "\n")

    def test_state_read_of_missing_key_is_empty_and_does_not_create_state(self) -> None:
        self.state_dir.mkdir()
        (self.state_dir / "state.json").write_text("{}\n", encoding="utf-8")
        read = self._call("nt_state_get", "absent")
        self.assertEqual(read.returncode, 0, read.stderr)
        self.assertEqual(read.stdout, "\n")
        self.assertEqual((self.state_dir / "state.json").read_text(encoding="utf-8"), "{}\n")

    def test_atomic_replace_failure_preserves_original_and_cleans_temporary(self) -> None:
        self.state_dir.mkdir()
        path = self.state_dir / "state.json"
        original = '{"kept":"original"}\n'
        path.write_text(original, encoding="utf-8")
        inject = Path(self.temp.name) / "inject"
        inject.mkdir()
        (inject / "sitecustomize.py").write_text(
            "import os\ndef denied_replace(*args, **kwargs):\n    raise OSError('injected replace failure')\nos.replace = denied_replace\n",
            encoding="utf-8",
        )
        env = self.env.copy()
        env["PYTHONPATH"] = str(inject)
        result = subprocess.run(
            ["bash", "-c", '. "$1"; nt_state_set "$2" "$3"', "test", str(CORE), "key", "new"],
            env=env, text=True, capture_output=True, check=False, timeout=5,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(path.read_text(encoding="utf-8"), original)
        self.assertEqual(sorted(item.name for item in self.state_dir.iterdir()), ["state.json"])

    def test_state_write_preserves_corrupt_file_instead_of_truncating_it(self) -> None:
        self.state_dir.mkdir()
        path = self.state_dir / "state.json"
        path.write_text('{ invalid json', encoding="utf-8")
        write = self._call("nt_state_set", "key", "value")
        self.assertNotEqual(write.returncode, 0)
        self.assertEqual(path.read_text(encoding="utf-8"), '{ invalid json')
        self.assertEqual(list(self.state_dir.iterdir()), [path])


if __name__ == "__main__":
    unittest.main()
