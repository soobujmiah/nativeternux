"""Typed CLI argument routing tests for backup and restore commands."""
from __future__ import annotations
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / "lib" / "recovery.sh"


class RecoveryCliTests(unittest.TestCase):
    def _run(self, expression):
        command = 'source "$1"; _nt_recovery_call() { printf "%s\\n" "$@"; }; ' + expression
        return subprocess.run(["bash", "-c", command, "bash", str(RECOVERY)],
                              text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

    def test_backup_preview_and_confirm_route_to_typed_service(self):
        preview = self._run('TERNUXX_JSON=0; nt_cmd_backup create --name safe-copy')
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertEqual(preview.stdout.splitlines(), ["backup.create", "--name", "safe-copy"])
        apply = self._run('TERNUXX_JSON=0; nt_cmd_backup create --name safe-copy --yes --plan-id abc')
        self.assertEqual(apply.returncode, 0, apply.stderr)
        self.assertEqual(apply.stdout.splitlines(), ["backup.create", "--name", "safe-copy", "--yes", "--plan-id", "abc"])

    def test_restore_defaults_to_preview_and_confirmation_is_explicit(self):
        preview = self._run('TERNUXX_JSON=0; nt_cmd_restore snapshot')
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertEqual(preview.stdout.splitlines(), ["restore.preview", "--backup-id", "snapshot"])
        apply = self._run('TERNUXX_JSON=0; nt_cmd_restore snapshot --yes --plan-id 123')
        self.assertEqual(apply.returncode, 0, apply.stderr)
        self.assertEqual(apply.stdout.splitlines(), ["restore.apply", "--backup-id", "snapshot", "--yes", "--plan-id", "123"])

    def test_recovery_status_and_inspect_route_to_typed_service(self):
        status = self._run('TERNUXX_JSON=0; nt_cmd_recovery status')
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertEqual(status.stdout.splitlines(), ["recovery.status"])
        inspect = self._run('TERNUXX_JSON=0; nt_cmd_recovery inspect 0123456789abcdef0123456789abcdef')
        self.assertEqual(inspect.returncode, 0, inspect.stderr)
        self.assertEqual(inspect.stdout.splitlines(), ["recovery.inspect", "--operation-id", "0123456789abcdef0123456789abcdef"])

    def test_recovery_rollback_defaults_to_preview_and_requires_exact_plan(self):
        operation_id = "0123456789abcdef0123456789abcdef"
        preview = self._run(f'TERNUXX_JSON=0; nt_cmd_recovery rollback {operation_id}')
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertEqual(preview.stdout.splitlines(), ["recovery.rollback.preview", "--operation-id", operation_id])
        apply = self._run(f'TERNUXX_JSON=0; nt_cmd_recovery rollback {operation_id} --yes --plan-id abc')
        self.assertEqual(apply.returncode, 0, apply.stderr)
        self.assertEqual(apply.stdout.splitlines(), ["recovery.rollback.apply", "--operation-id", operation_id,
                                                     "--yes", "--plan-id", "abc"])
        no_plan = self._run(f'TERNUXX_JSON=0; nt_cmd_recovery rollback {operation_id} --yes')
        self.assertEqual(no_plan.returncode, 2)
        self.assertEqual(no_plan.stdout, "")

    def test_invalid_cli_shapes_fail_before_service_call(self):
        missing = self._run('TERNUXX_JSON=0; nt_cmd_backup create --yes')
        self.assertEqual(missing.returncode, 2)
        self.assertEqual(missing.stdout, "")
        no_id = self._run('TERNUXX_JSON=0; nt_cmd_restore snapshot --yes')
        self.assertEqual(no_id.returncode, 2)
        self.assertEqual(no_id.stdout, "")
        backup_id_without_yes = self._run('TERNUXX_JSON=0; nt_cmd_backup create --name x --plan-id abc')
        self.assertEqual(backup_id_without_yes.returncode, 2)
        self.assertEqual(backup_id_without_yes.stdout, "")


if __name__ == "__main__":
    unittest.main()
