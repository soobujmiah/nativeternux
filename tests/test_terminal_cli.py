from __future__ import annotations

from contextlib import ExitStack
import io
import json
import os
from pathlib import Path
import socket
import stat
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import terminal_cli


class TerminalCLIAttachmentTests(unittest.TestCase):
    def test_service_socket_recovery_cli_requires_the_preview_id(self):
        with tempfile.TemporaryDirectory(prefix="ternuxx-terminal-cli-recovery-") as temp:
            state = Path(temp) / "state"
            state.mkdir(mode=0o700)
            path = terminal_cli.terminal_broker.broker_socket_path(state)
            stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            stale.bind(str(path))
            stale.close()
            os.chmod(path, 0o600)
            with mock.patch.dict(os.environ, {"TERNUXX_STATE_DIR": str(state)}):
                with mock.patch.object(terminal_cli.sys, "stdout", new_callable=io.StringIO) as output:
                    self.assertEqual(terminal_cli.run(["service", "socket", "preview"]), 0)
                    plan = json.loads(output.getvalue())
                self.assertEqual(stat.S_IMODE(path.lstat().st_mode), 0o600)
                with mock.patch.object(terminal_cli.sys, "stderr", new_callable=io.StringIO):
                    self.assertEqual(terminal_cli.run(["service", "socket", "recover"]), 1)
                with mock.patch.object(terminal_cli.sys, "stdout", new_callable=io.StringIO) as output:
                    self.assertEqual(terminal_cli.run(["service", "socket", "recover", "--yes",
                        "--plan-id", plan["plan_id"]]), 0)
                    result = json.loads(output.getvalue())
            self.assertEqual(result["status"], "recovered")
            self.assertFalse(path.exists())

    def run_attach(self, *, supplied=False, resize_fails=False, tty=True):
        lease = {"session_id": "proot-" + "a" * 32,
                 "generation": 7, "attachment_id": "attach-" + "b" * 32}
        client = mock.Mock()
        def request(operation, **kwargs):
            if operation == "terminal.attach":
                return {"ok": True, **lease}
            if operation == "terminal.resize" and resize_fails:
                raise terminal_cli.terminal_broker.BrokerError("fixture resize failure")
            return {"ok": True}
        client.request.side_effect = request
        with ExitStack() as stack:
            stdin = stack.enter_context(mock.patch.object(terminal_cli.sys, "stdin"))
            stdout = stack.enter_context(mock.patch.object(terminal_cli.sys, "stdout"))
            stdin.isatty.return_value = stdout.isatty.return_value = tty
            stdin.fileno.return_value = 10
            stack.enter_context(mock.patch.object(terminal_cli, "_dimensions", return_value=(80, 24)))
            stack.enter_context(mock.patch.object(terminal_cli.termios, "tcgetattr", return_value=[]))
            restore = stack.enter_context(mock.patch.object(terminal_cli.termios, "tcsetattr"))
            stack.enter_context(mock.patch.object(terminal_cli.signal, "signal"))
            stack.enter_context(mock.patch.object(terminal_cli.tty, "setraw"))
            stack.enter_context(mock.patch.object(terminal_cli.select, "select", return_value=([10], [], [])))
            stack.enter_context(mock.patch.object(terminal_cli.os, "read", return_value=b"\x1d"))
            if resize_fails or not tty:
                with self.assertRaises(terminal_cli.terminal_broker.BrokerError):
                    terminal_cli.attach(lease["session_id"], client=client,
                                        lease=lease if supplied else None)
            else:
                self.assertEqual(terminal_cli.attach(lease["session_id"], client=client,
                                  lease=lease if supplied else None), 0)
                restore.assert_called_once()
        return client, lease

    def assert_released(self, client, lease):
        detached = [c for c in client.request.call_args_list if c.args[0] == "terminal.detach"]
        self.assertEqual(len(detached), 1)
        self.assertEqual(detached[0].kwargs, lease)
        self.assertFalse(any(c.args[0].startswith("terminal.close")
                             for c in client.request.call_args_list))

    def test_control_bracket_releases_writer_without_stopping_guest(self):
        self.assert_released(*self.run_attach())

    def test_initial_resize_failure_releases_acquired_writer(self):
        self.assert_released(*self.run_attach(resize_fails=True))

    def test_supplied_start_lease_is_released_if_terminal_disappears(self):
        self.assert_released(*self.run_attach(supplied=True, tty=False))


if __name__ == "__main__":
    unittest.main()
