"""Fixtures for short launch commands and canonical PRoot routing."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LaunchCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-launch-")
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        passwd = self.root / "var/lib/proot-distro/containers/debian/rootfs/etc/passwd"
        passwd.parent.mkdir(parents=True)
        passwd.write_text("root:x:0:0:root:/root:/bin/bash\n"
                          "dev:x:1000:1000:Dev:/home/dev:/bin/bash\n", encoding="utf-8")
        stub = self.bin / "proot-distro"
        stub.write_text('#!/bin/sh\nif [ -n \"${PROOT_ENV_CAPTURE:-}\" ]; then env > \"$PROOT_ENV_CAPTURE\"; fi\nprintf \"%s\\n\" \"$@\"\n')
        stub.chmod(0o755)
        prefix_bash = self.bin / "bash"
        prefix_bash.symlink_to(shutil.which("bash"))
        self.env = {**os.environ, "HOME": str(self.root), "PREFIX": str(self.root),
                    "PATH": f"{self.bin}:{os.environ['PATH']}",
                    "TERNUXX_STATE_DIR": str(self.root / "state"),
                    "TERNUXX_LOG_DIR": str(self.root / "log")}

    def tearDown(self) -> None:
        self.temp.cleanup()

    def tx(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([shutil.which("bash"), str(ROOT / "tx"), *args],
                              capture_output=True, text=True, env=self.env, timeout=30)

    def cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([shutil.which("bash"), str(ROOT / "tx"), *args],
                              capture_output=True, text=True, env=self.env, timeout=30)

    def test_shell_explicit_user_runs_proot_distro_login(self) -> None:
        result = self.tx("db", "--user", "dev")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.split(), ["login", "debian", "--shared-tmp", "--user", "dev"])

    def test_native_db_backend_is_per_process_and_shared_profile_stays_zink(self) -> None:
        capture = self.root / "proot-args"
        ensure = self.root / "virgl-ensure"
        stub = self.bin / "proot-distro"
        stub.write_text("#!/bin/sh\nprintf \"%s\\n\" \"$@\" > \"$PROOT_ARGS_CAPTURE\"\n")
        stub.chmod(0o755)
        script = "\n".join([
            '_TN_LIB_DIR="$LIB_DIR"',
            'source "$LIB_DIR/launch.sh"',
            'nt_fail() { echo "$*" >&2; }',
            'nt_warn() { echo "$*" >&2; }',
            'nt_require_command() { command -v "$1" >/dev/null; }',
            'nt_require_termux() { return 0; }',
            'nt_audio_ensure() { return 0; }',
            'nt_use() { return 0; }',
            '_nt_use() { return 0; }',
            '_nt_guest_pulse_cookie() { return 0; }',
            '_nt_launch_guest_shell() { printf "/bin/bash"; }',
            '_nt_virgl_ensure() { printf "%s\n" "$1" > "$VIRGL_ENSURE_CAPTURE"; }',
            'nt_cmd_db --user dev --backend virgl --display :1',
        ])
        env = {**self.env, "PREFIX": "/data/data/com.termux/files/usr",
               "TERMUX_VERSION": "fixture", "LIB_DIR": str(ROOT / "lib"),
               "PROOT_ARGS_CAPTURE": str(capture), "VIRGL_ENSURE_CAPTURE": str(ensure)}
        result = subprocess.run([shutil.which("bash"), "-c", script], capture_output=True,
                                text=True, env=env, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        virgl_args = capture.read_text().splitlines()
        separator = virgl_args.index("--")
        persisted = virgl_args[:separator]
        self.assertEqual(persisted[:5], ["login", "debian", "--shared-tmp", "--user", "dev"])
        self.assertIn("DISPLAY=:1", persisted)
        self.assertIn("GALLIUM_DRIVER=zink", persisted)
        self.assertIn("MESA_LOADER_DRIVER_OVERRIDE=zink", persisted)
        self.assertNotIn("GALLIUM_DRIVER=virpipe", persisted)
        self.assertFalse(any(arg.startswith("VTEST_SOCKET_NAME=") for arg in persisted))
        self.assertIn("GALLIUM_DRIVER=virpipe", virgl_args[separator + 4])
        self.assertIn("VTEST_SOCKET_NAME=/tmp/.ternuxx-virgl/virgl-1.sock", virgl_args[separator + 4])
        self.assertEqual(ensure.read_text().strip(), ":1")

        zink_capture = self.root / "zink-proot-args"
        zink_env = {**env, "PROOT_ARGS_CAPTURE": str(zink_capture)}
        zink_script = script.replace(
            "nt_cmd_db --user dev --backend virgl --display :1",
            "nt_cmd_db --user dev --backend zink --display :1")
        zink_result = subprocess.run([shutil.which("bash"), "-c", zink_script],
                                     capture_output=True, text=True, env=zink_env, timeout=10)
        self.assertEqual(zink_result.returncode, 0, zink_result.stderr)
        zink_args = zink_capture.read_text().splitlines()
        zink_separator = zink_args.index("--")
        self.assertEqual(zink_args[:zink_separator], persisted)
        self.assertIn("GALLIUM_DRIVER=zink", zink_args[zink_separator + 4])
        self.assertNotIn("VTEST_SOCKET_NAME=", zink_args[zink_separator + 4])

        parallel = []
        for label, invocation in (
                ("parallel-virgl", "nt_cmd_db --user dev --backend virgl --display :2"),
                ("parallel-zink", "nt_cmd_db --user dev --backend zink --display :1")):
            parallel_capture = self.root / f"{label}-args"
            parallel_script = script.replace(
                "nt_cmd_db --user dev --backend virgl --display :1", invocation)
            parallel_env = {**env, "PROOT_ARGS_CAPTURE": str(parallel_capture)}
            process = subprocess.Popen([shutil.which("bash"), "-c", parallel_script],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=parallel_env)
            parallel.append((process, parallel_capture, label))
        parallel_profiles = {}
        for process, parallel_capture, label in parallel:
            stdout, stderr = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, stderr or stdout)
            parallel_args = parallel_capture.read_text().splitlines()
            parallel_profiles[label] = parallel_args[:parallel_args.index("--")]
        self.assertEqual(parallel_profiles["parallel-virgl"], parallel_profiles["parallel-zink"])
        parallel_virgl_args = (self.root / "parallel-virgl-args").read_text().splitlines()
        self.assertIn("DISPLAY=:2", parallel_virgl_args[parallel_virgl_args.index("--") + 4])

        command_capture = self.root / "command-proot-args"
        command_env = {**env, "PROOT_ARGS_CAPTURE": str(command_capture)}
        command_script = script.replace(
            "nt_cmd_db --user dev --backend virgl --display :1",
            "nt_cmd_db --user dev --backend virgl --display :1 -- glxinfo -B")
        command_result = subprocess.run([shutil.which("bash"), "-c", command_script],
                                        capture_output=True, text=True, env=command_env, timeout=10)
        self.assertEqual(command_result.returncode, 0, command_result.stderr)
        command_args = command_capture.read_text().splitlines()
        command_separator = command_args.index("--")
        self.assertEqual(command_args[command_separator + 1], "/usr/bin/env")
        self.assertIn("GALLIUM_DRIVER=virpipe", command_args[command_separator + 1:])
        self.assertEqual(command_args[-2:], ["glxinfo", "-B"])

    def test_native_android_runtime_variables_do_not_leak_to_guest_profile(self) -> None:
        capture = self.root / "proot-env"
        env = {**self.env, "PROOT_ENV_CAPTURE": str(capture),
               "ANDROID_ART_ROOT": "/apex/com.android.art", "ANDROID_DATA": "/data",
               "ANDROID_ROOT": "/system", "BOOTCLASSPATH": "sentinel-classpath",
               "EXTERNAL_STORAGE": "/sdcard", "TERM": "xterm-256color"}
        result = subprocess.run([shutil.which("bash"), str(ROOT / "tx"), "db", "--user", "dev"],
                                capture_output=True, text=True, env=env, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        observed = capture.read_text()
        observed_keys = {line.split("=", 1)[0] for line in observed.splitlines() if "=" in line}
        for name in ("ANDROID_ART_ROOT", "ANDROID_DATA", "ANDROID_ROOT", "BOOTCLASSPATH", "EXTERNAL_STORAGE"):
            self.assertNotIn(name, observed_keys)
        self.assertIn("TERM", observed_keys)

    def test_legacy_tx_shell_command_is_removed(self) -> None:
        result = self.tx("shell")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unknown command", result.stderr)

    def test_shell_root_and_command_passthrough(self) -> None:
        result = self.tx("db", "--root", "--", "echo", "a b")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(),
                         ["login", "debian", "--shared-tmp", "--", "echo", "a b"])

    def test_shell_refuses_unresolvable_user_and_bad_names(self) -> None:
        self.assertNotEqual(self.tx("db", "--distro", "missing").returncode, 0)
        self.assertEqual(self.tx("db", "--user", "a;b").returncode, 2)
        self.assertEqual(self.tx("db", "--root", "--distro", "../x").returncode, 2)

    def test_gui_and_canonical_proot_gui_reject_unknown_actions(self) -> None:
        self.assertEqual(self.tx("gui", "bogus").returncode, 2)
        self.assertEqual(self.cli("proot", "gui", "bogus").returncode, 2)

    def test_gui_reports_missing_display_without_starting_desktop(self) -> None:
        env = dict(self.env)
        env["PREFIX"] = "/data/data/com.termux/files/usr"
        env["TERMUX_VERSION"] = "fixture"
        env.pop("DISPLAY", None)
        result = subprocess.run([shutil.which("bash"), str(ROOT / "tx"), "gui"],
                                capture_output=True, text=True, env=env, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn("The Ternuxx Native desktop is not verified running", result.stderr)
        self.assertIn("Run 'tx start', then retry 'tx gui'", result.stderr)

    def test_non_contract_app_and_pgui_shortcuts_are_not_registered(self) -> None:
        for command in ("app", "apps", "pgui"):
            result = self.tx(command)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Unknown command", result.stderr)

    def test_help_lists_short_form_and_commands(self) -> None:
        result = self.tx("--help")
        self.assertIn("tx <command> [options]", result.stdout)
        for name in ("tx db", "tx gui"):
            self.assertIn(name, result.stdout)
        self.assertNotIn("tx pgui", result.stdout)
        self.assertIn("tx proot gui", self.cli("proot", "--help").stdout)
        self.assertIn("--root", self.tx("db", "--help").stdout)
        self.assertIn("virgl", result.stdout)
        self.assertIn("tx virgl", self.cli("virgl", "--help").stdout)
        self.assertIn("zink|virgl", self.tx("db", "--help").stdout)

    def test_mng_is_canonical_and_long_management_route_is_deprecated_alias(self) -> None:
        canonical = self.cli("mng", "bogus")
        self.assertNotEqual(canonical.returncode, 0)
        self.assertNotIn("deprecated", canonical.stderr)
        legacy = self.cli("management", "bogus")
        self.assertNotEqual(legacy.returncode, 0)
        self.assertIn("tx management is deprecated; use tx mng", legacy.stderr)
        help_text = self.cli("mng", "--help")
        self.assertIn("tx mng cron status", help_text.stdout)
        self.assertIn("tx mng proot status", help_text.stdout)
        self.assertNotIn("tx management", help_text.stdout)
        bad_proot = self.cli("mng", "proot", "stop")
        self.assertEqual(bad_proot.returncode, 2)
        self.assertIn("Usage: tx mng proot stop SESSION_ID", bad_proot.stderr)
        proot_bad_action = self.cli("mng", "proot", "stop")
        self.assertEqual(proot_bad_action.returncode, 2)
        self.assertIn("Usage: tx mng proot stop SESSION_ID", proot_bad_action.stderr)

    def test_short_slugs_dispatch_to_the_same_canonical_commands(self) -> None:
        self.assertEqual(self.cli("st", "--json").returncode, 0)
        self.assertIn("Start the native Termux XFCE session", self.cli("up", "--help").stdout)
        self.assertIn("tx mng app launch", self.cli("--help").stdout)
        self.assertNotEqual(self.cli("zz").returncode, 0)


if __name__ == "__main__":
    unittest.main()
