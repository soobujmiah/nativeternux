"""Tests for bounded, read-only PRoot distribution discovery."""

from __future__ import annotations

from types import SimpleNamespace
import json
import stat
import subprocess
import tempfile
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import proot_diagnostics  # noqa: E402


class ProotDiagnosticsTests(unittest.TestCase):
    def _ternux_state_fixture(self, home: Path, contents: str = "user=guest\n") -> Path:
        state_dir = home / ".local" / "share" / "ternux"
        state_dir.mkdir(parents=True, mode=0o700)
        for directory in (home / ".local", home / ".local" / "share", state_dir):
            directory.chmod(0o700)
        state = state_dir / "state"
        state.write_text(contents)
        state.chmod(0o600)
        return state_dir

    def test_resolves_ternux_guest_user_from_private_state_without_emitting_it(self):
        with tempfile.TemporaryDirectory(prefix="ternuxx-profile-home-") as temp:
            home = Path(temp) / "home"
            home.mkdir(mode=0o700)
            state_dir = self._ternux_state_fixture(home)
            calls = []
            def runner(args, **kwargs):
                calls.append((args, kwargs))
                return SimpleNamespace(returncode=0, stdout=json.dumps({
                    "command": "state", "status": "ok", "version": "1.4.0",
                    "state_dir": str(state_dir),
                }))
            user = proot_diagnostics.resolve_ternux_guest_user(
                home=home, path="/prefix/bin", which=lambda name, path=None: "/prefix/bin/ternux",
                runner=runner,
            )
            self.assertEqual(user, "guest")
            self.assertEqual(calls[0][0], ["/prefix/bin/ternux", "--json", "state"])
            self.assertEqual(calls[0][1]["timeout"], 10)
            self.assertEqual(stat.S_IMODE(state_dir.joinpath("state").stat().st_mode), 0o600)

    def test_ternux_guest_user_resolution_rejects_unsafe_state_paths_and_accounts(self):
        with tempfile.TemporaryDirectory(prefix="ternuxx-profile-home-") as temp:
            home = Path(temp) / "home"
            home.mkdir(mode=0o700)
            outside = Path(temp) / "outside"
            outside.mkdir(mode=0o700)
            outside_state = self._ternux_state_fixture(outside)
            def cli(state_dir):
                return lambda *_args, **_kwargs: SimpleNamespace(
                    returncode=0, stdout=json.dumps({"command": "state", "status": "ok",
                        "version": "1.4.0", "state_dir": str(state_dir)}))
            with self.assertRaises(proot_diagnostics.GuestProfileError):
                proot_diagnostics.resolve_ternux_guest_user(
                    home=home, which=lambda *_a, **_kw: "/prefix/bin/ternux", runner=cli(outside_state))
            safe_state = self._ternux_state_fixture(home, "user=root\n")
            with self.assertRaises(proot_diagnostics.GuestProfileError):
                proot_diagnostics.resolve_ternux_guest_user(
                    home=home, which=lambda *_a, **_kw: "/prefix/bin/ternux", runner=cli(safe_state))
            (safe_state / "state").write_text("user=guest\nuser=other\n")
            (safe_state / "state").chmod(0o600)
            with self.assertRaises(proot_diagnostics.GuestProfileError):
                proot_diagnostics.resolve_ternux_guest_user(
                    home=home, which=lambda *_a, **_kw: "/prefix/bin/ternux", runner=cli(safe_state))

    def test_ternux_guest_user_resolution_rejects_loose_permissions_and_symlink(self):
        with tempfile.TemporaryDirectory(prefix="ternuxx-profile-home-") as temp:
            home = Path(temp) / "home"
            home.mkdir(mode=0o700)
            state_dir = self._ternux_state_fixture(home)
            response = json.dumps({"command": "state", "status": "ok", "version": "1.4.0",
                                   "state_dir": str(state_dir)})
            runner = lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout=response)
            state = state_dir / "state"
            state.chmod(0o644)
            with self.assertRaises(proot_diagnostics.GuestProfileError):
                proot_diagnostics.resolve_ternux_guest_user(
                    home=home, which=lambda *_a, **_kw: "/prefix/bin/ternux", runner=runner)
            state.unlink()
            target = Path(temp) / "target-state"
            target.write_text("user=guest\n")
            target.chmod(0o600)
            state.symlink_to(target)
            with self.assertRaises(proot_diagnostics.GuestProfileError):
                proot_diagnostics.resolve_ternux_guest_user(
                    home=home, which=lambda *_a, **_kw: "/prefix/bin/ternux", runner=runner)

    def test_parses_installed_names_and_never_enters_guest(self):
        calls = []
        output = "Installed containers:\n  \x1b[32m* \x1b[0mDebian\nLog in with: proot-distro login <name>\n"
        def runner(args, **kwargs):
            calls.append((args, kwargs))
            return SimpleNamespace(returncode=0, stdout=output)
        report = proot_diagnostics.inspect_installed(
            which=lambda name: "/prefix/bin/proot-distro" if name == "proot-distro" else None,
            runner=runner,
        )
        self.assertEqual(report["status"], "installed")
        self.assertEqual(report["installed_distributions"], ["debian"])
        self.assertEqual(report["ownership"], "unverified")
        self.assertFalse(report["guest_entered"])
        self.assertTrue(report["read_only"])
        self.assertEqual(calls[0][0], ["/prefix/bin/proot-distro", "list"])
        self.assertIs(calls[0][1]["stderr"], subprocess.STDOUT)

    def test_empty_inventory_is_distinct_from_query_failure(self):
        report = proot_diagnostics.inspect_installed(
            which=lambda _name: "/prefix/bin/proot-distro",
            runner=lambda *_args, **_kwargs: SimpleNamespace(
                returncode=0, stdout="Installed containers:\nLog in with: proot-distro login <name>\n"),
        )
        self.assertEqual(report["status"], "none")
        self.assertEqual(report["installed_distributions"], [])

    def test_all_inventory_outcomes_match_strict_response_schema(self):
        schema = json.loads((ROOT / "schemas/proot-distribution-inventory.schema.json").read_text())
        expected = set(schema["properties"])
        reports = [
            proot_diagnostics.inspect_installed(which=lambda _name: None),
            proot_diagnostics.inspect_installed(
                which=lambda _name: "/prefix/bin/proot-distro",
                runner=lambda *_args, **_kwargs: SimpleNamespace(
                    returncode=0, stdout="Installed containers:\nLog in with: proot-distro login <name>\n")),
            proot_diagnostics.inspect_installed(
                which=lambda _name: "/prefix/bin/proot-distro",
                runner=lambda *_args, **_kwargs: SimpleNamespace(
                    returncode=0, stdout="Installed containers:\n * Debian\nLog in with: proot-distro login <name>\n")),
            proot_diagnostics.inspect_installed(
                which=lambda _name: "/prefix/bin/proot-distro",
                runner=lambda *_args, **_kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired("proot-distro", 5))),
        ]
        for report in reports:
            self.assertEqual(set(report), expected)
            self.assertEqual(report["component"], schema["properties"]["component"]["const"])
            self.assertIn(report["status"], schema["properties"]["status"]["enum"])
            self.assertEqual(report["ownership"], "unverified")
            self.assertIs(report["guest_entered"], False)
            self.assertIs(report["read_only"], True)
            self.assertIsInstance(report["manager_available"], bool)
            self.assertIsInstance(report["installed_distributions"], list)
            self.assertEqual(report["installed_distributions"], sorted(set(report["installed_distributions"])))

    def test_ternux_guest_verify_uses_typed_readonly_commands_and_reports_partial_state(self):
        calls = []
        outputs = [
            SimpleNamespace(returncode=0, stdout="Installed containers:\n * Debian\nLog in with: proot-distro login <name>\n"),
            SimpleNamespace(returncode=0, stdout="ternux guest v1.4.0\nhttps://github.com/soobujmiah/ternux\n"),
            SimpleNamespace(returncode=1, stdout="ternux Debian guest status\n  Display: :1\n  X11: reachable\n  Audio: PulseAudio not reachable\n  Renderer: zink Vulkan 1.4(Adreno (TM) 825 (MESA_TURNIP))\n"),
        ]
        def runner(args, **kwargs):
            calls.append((args, kwargs))
            return outputs.pop(0)
        report = proot_diagnostics.verify_ternux_guest(
            distro="debian", user="sbj", display=":1", backend="zink",
            which=lambda name: "/prefix/bin/proot-distro" if name == "proot-distro" else None,
            runner=runner,
        )
        self.assertEqual(report["status"], "partial")
        self.assertTrue(report["guest_entered"])
        self.assertEqual(report["profile_owner"], "unverified")
        self.assertEqual(report["companion_version"], "1.4.0")
        self.assertEqual(report["checks"], {
            "observed_display": ":1", "x11": "reachable", "audio": "unavailable",
            "renderer_class": "zink_turnip",
            "renderer": "zink Vulkan 1.4(Adreno (TM) 825 (MESA_TURNIP))",
        })
        command = calls[1][0]
        self.assertIn("--isolated", command)
        self.assertNotIn("--shared-tmp", command)
        self.assertIn("/data/data/com.termux/files/usr/tmp/.X11-unix:/tmp/.X11-unix", command)
        self.assertEqual(command[2], "--isolated")
        self.assertIn("/dev/kgsl-3d0:/dev/kgsl", command)
        self.assertIn("DISPLAY=:1", command)
        self.assertIn("PULSE_SERVER=tcp:127.0.0.1:4713", command)
        self.assertIn("MESA_SHADER_CACHE_DISABLE=true", command)
        self.assertEqual(command[-2:], ["ternux", "--version"])
        self.assertEqual(calls[2][0][-2:], ["ternux", "status"])
        self.assertNotIn("-c", command)
        self.assertTrue(report["read_only"])
        self.assertTrue(report["safety"]["host_home_and_shared_storage_unbound"])
        self.assertTrue(all(value is False for key, value in report["safety"].items()
                            if key != "host_home_and_shared_storage_unbound"))

    def test_guest_verification_includes_native_ternux_status_without_claiming_ownership(self):
        outputs = [
            "Installed containers:\n * Debian\nLog in with: proot-distro login <name>\n",
            json.dumps({"command": "status", "status": "running", "timestamp": "2026-10-18T01:00:13Z",
                        "version": "1.4.0", "x11_running": "yes", "pulseaudio": "stopped",
                        "virgl": "stopped", "launcher": "present"}),
            json.dumps({"command": "backend", "status": "ok", "version": "1.4.0",
                        "backend": "zink", "renderer": "unknown", "vulkan": "yes",
                        "available_backends": "zink,virgl"}),
            "ternux guest v1.4.0\nhttps://github.com/soobujmiah/ternux\n",
            "Display: :1\nX11: reachable\nAudio: PulseAudio reachable\nRenderer: zink Vulkan 1.4(Adreno (TM) 825 (MESA_TURNIP))\n",
        ]
        calls = []
        def runner(args, **kwargs):
            calls.append(args)
            return SimpleNamespace(returncode=0, stdout=outputs.pop(0))
        report = proot_diagnostics.verify_ternux_guest(
            distro="debian", user="sbj", display=":1", backend="zink",
            which=lambda name: {"proot-distro": "/prefix/bin/proot-distro",
                                "ternux": "/prefix/bin/ternux"}.get(name),
            runner=runner,
        )
        self.assertEqual(report["status"], "complete")
        self.assertEqual(report["native_ternux_status"]["pulseaudio"], "stopped")
        self.assertEqual(report["native_ternux_status"]["identity"], "unverified")
        self.assertEqual(report["native_ternux_status"]["backend"], "zink")
        self.assertEqual(report["native_pulseaudio_endpoint"],
                         {"status": "unavailable", "server_name": None, "default_sink": None})
        self.assertEqual(calls[1], ["/prefix/bin/ternux", "--json", "status"])
        self.assertEqual(calls[2], ["/prefix/bin/ternux", "--json", "backend", "show"])
        self.assertIn("PULSE_SERVER=tcp:127.0.0.1:4713", calls[3])

    def test_guest_verify_fails_closed_for_unsafe_or_unsupported_inputs(self):
        calls = []
        for values in (
            {"distro": "ubuntu", "user": "sbj", "display": ":1", "backend": "zink"},
            {"distro": "debian", "user": "root", "display": ":1", "backend": "zink"},
            {"distro": "debian", "user": "sbj;id", "display": ":1", "backend": "zink"},
            {"distro": "debian", "user": "sbj", "display": ":1;id", "backend": "zink"},
            {"distro": "debian", "user": "sbj", "display": ":1", "backend": "auto"},
        ):
            with self.subTest(values=values), self.assertRaises(ValueError):
                proot_diagnostics.verify_ternux_guest(**values, runner=lambda *a, **k: calls.append(a))
        self.assertEqual(calls, [])

    def test_unverified_companion_never_runs_guest_status(self):
        outputs = [
            SimpleNamespace(returncode=0, stdout="Installed containers:\n * Debian\n"),
            SimpleNamespace(returncode=0, stdout="unexpected command\n"),
        ]
        calls = []
        def runner(args, **kwargs):
            calls.append(args)
            return outputs.pop(0)
        result = proot_diagnostics.verify_ternux_guest(
            distro="debian", user="sbj", display=":1", backend="zink",
            which=lambda name: "/prefix/bin/proot-distro" if name == "proot-distro" else None, runner=runner)
        self.assertEqual(result["status"], "unsupported_companion")
        self.assertEqual(len(calls), 2)

    def test_guest_diagnostic_outcomes_match_strict_response_schema(self):
        schema = json.loads((ROOT / "schemas/ternux-guest-diagnostics.schema.json").read_text())
        inventory = "Installed containers:\n * Debian\nLog in with: proot-distro login <name>\n"
        companion = "ternux guest v1.4.0\nhttps://github.com/soobujmiah/ternux\n"
        status = "Display: :1\nX11: reachable\nAudio: PulseAudio reachable\nRenderer: zink Vulkan 1.4(Adreno (TM) 825 (MESA_TURNIP))\n"
        outputs = [inventory, companion, status]
        def runner(args, **kwargs):
            output = outputs.pop(0)
            return SimpleNamespace(returncode=0, stdout=output)
        complete = proot_diagnostics.verify_ternux_guest(
            distro="debian", user="sbj", display=":1", backend="zink",
            which=lambda name: "/prefix/bin/proot-distro" if name == "proot-distro" else None, runner=runner)
        absent = proot_diagnostics.verify_ternux_guest(
            distro="debian", user="sbj", display=":1", backend="zink", which=lambda _name: None)
        for report in (complete, absent):
            self.assertEqual(set(report), set(schema["required"]))
            self.assertEqual(report["component"], schema["properties"]["component"]["const"])
            self.assertIn(report["status"], schema["properties"]["status"]["enum"])
            self.assertEqual(set(report["checks"]), set(schema["properties"]["checks"]["required"]))
            self.assertEqual(set(report["safety"]), set(schema["properties"]["safety"]["required"]))
            self.assertTrue(report["safety"]["host_home_and_shared_storage_unbound"])
            self.assertTrue(all(value is False for key, value in report["safety"].items()
                                if key != "host_home_and_shared_storage_unbound"))
        self.assertEqual(complete["status"], "complete")
        self.assertEqual(absent["status"], "unavailable")

    def test_guest_command_disables_default_host_mounts_and_scopes_zink_bindings(self):
        zink = proot_diagnostics._guest_command(
            "/prefix/bin/proot-distro", "sbj", ":1", "zink", "status", prefix="/prefix")
        self.assertIn("--isolated", zink)
        self.assertNotIn("--shared-home", zink)
        self.assertNotIn("--shared-tmp", zink)
        self.assertIn("/prefix/tmp/.X11-unix:/tmp/.X11-unix", zink)
        self.assertIn("/dev/kgsl-3d0:/dev/kgsl", zink)
        self.assertIn("/dev/dri", zink)
        self.assertNotIn("/data/data/com.termux", zink)
        virgl = proot_diagnostics._guest_command(
            "/prefix/bin/proot-distro", "sbj", ":1", "virgl", "status", prefix="/prefix")
        self.assertIn("--isolated", virgl)
        self.assertIn("--shared-tmp", virgl)
        self.assertNotIn("--shared-home", virgl)
        self.assertNotIn("/data/data/com.termux", virgl)

    def test_native_pulseaudio_endpoint_is_read_only_and_typed(self):
        calls = []
        def runner(args, **kwargs):
            calls.append((args, kwargs))
            return SimpleNamespace(returncode=0, stdout="Server Name: pulseaudio\nDefault Sink: OpenSL_ES_sink\n")
        report = proot_diagnostics.inspect_native_pulseaudio_endpoint(
            which=lambda name: "/prefix/bin/pactl" if name == "pactl" else None, runner=runner)
        self.assertEqual(report, {"status": "available", "server_name": "pulseaudio",
                                  "default_sink": "OpenSL_ES_sink"})
        self.assertEqual(calls[0][0], ["/prefix/bin/pactl", "info"])
        self.assertEqual(calls[0][1]["timeout"], 5)
        self.assertTrue(calls[0][1]["capture_output"])

    def test_native_pulseaudio_endpoint_distinguishes_unavailable_and_unknown(self):
        missing = proot_diagnostics.inspect_native_pulseaudio_endpoint(which=lambda _name: None)
        failed = proot_diagnostics.inspect_native_pulseaudio_endpoint(
            which=lambda _name: "/prefix/bin/pactl",
            runner=lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stdout=""))
        malformed = proot_diagnostics.inspect_native_pulseaudio_endpoint(
            which=lambda _name: "/prefix/bin/pactl",
            runner=lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout="Server Name: bad value!\n"))
        timed_out = proot_diagnostics.inspect_native_pulseaudio_endpoint(
            which=lambda _name: "/prefix/bin/pactl",
            runner=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                subprocess.TimeoutExpired("pactl", 5)))
        self.assertEqual(missing["status"], "unavailable")
        self.assertEqual(failed["status"], "unavailable")
        self.assertEqual(malformed["status"], "unknown")
        self.assertIsNone(malformed["server_name"])
        self.assertEqual(timed_out["status"], "unknown")

    def test_termux_x11_process_inspection_returns_displays_without_pid_or_argv(self):
        calls = []
        outputs = [
            "16032 termux-x11\n16040 proot\n16050 termux-x11\n",
            "/data/data/com.termux/files/usr/bin/termux-x11 :1 -ac\n",
            "/data/data/com.termux/files/usr/bin/termux-x11 invalid\n",
        ]
        def runner(args, **kwargs):
            calls.append((args, kwargs))
            return SimpleNamespace(returncode=0, stdout=outputs.pop(0))
        report = proot_diagnostics.inspect_termux_x11_process_displays(
            which=lambda name: "/prefix/bin/ps" if name == "ps" else None, runner=runner)
        self.assertEqual(report, {"status": "available", "observed_displays": [":1"]})
        self.assertEqual(calls[0][0], ["/prefix/bin/ps", "-A", "-o", "pid=,comm="])
        self.assertEqual(calls[1][0], ["/prefix/bin/ps", "-p", "16032", "-o", "args="])
        self.assertEqual(calls[2][0], ["/prefix/bin/ps", "-p", "16050", "-o", "args="])
        self.assertEqual(calls[0][1]["timeout"], 5)
        unavailable = proot_diagnostics.inspect_termux_x11_process_displays(which=lambda _name: None)
        unknown = proot_diagnostics.inspect_termux_x11_process_displays(
            which=lambda _name: "/prefix/bin/ps",
            runner=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                subprocess.TimeoutExpired("ps", 5)))
        self.assertEqual(unavailable["status"], "unavailable")
        self.assertEqual(unknown["status"], "unknown")

    def test_failed_guest_display_reports_visible_host_display_mismatch_without_identity_claim(self):
        outputs = [
            SimpleNamespace(returncode=0, stdout="Installed containers:\n * Debian\nLog in with: proot-distro login <name>\n"),
            SimpleNamespace(returncode=0, stdout="ternux guest v1.4.0\nhttps://github.com/soobujmiah/ternux\n"),
            SimpleNamespace(returncode=1, stdout="Display: :0\nX11: unavailable\nAudio: PulseAudio reachable\nRenderer: unavailable\n"),
            SimpleNamespace(returncode=0, stdout="16032 termux-x11\n"),
            SimpleNamespace(returncode=0, stdout="termux-x11 :1 -ac\n"),
        ]
        calls = []
        def runner(args, **kwargs):
            calls.append((args, kwargs))
            return outputs.pop(0)
        report = proot_diagnostics.verify_ternux_guest(
            distro="debian", user="sbj", display=":0", backend="zink",
            which=lambda name: {"proot-distro": "/prefix/bin/proot-distro",
                                "ps": "/prefix/bin/ps"}.get(name),
            runner=runner,
        )
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["checks"]["observed_display"], ":0")
        self.assertIn("requested display :0 not observed in the Termux-visible X11 process list",
                      report["blockers"])
        self.assertLessEqual(len(report["blockers"]), 4)
        self.assertEqual(calls[-2][0], ["/prefix/bin/ps", "-A", "-o", "pid=,comm="])
        self.assertEqual(calls[-1][0], ["/prefix/bin/ps", "-p", "16032", "-o", "args="])
        self.assertNotIn("16032", json.dumps(report))
        self.assertNotIn("termux-x11", json.dumps(report))
        self.assertEqual(report["profile_owner"], "unverified")

    def test_native_ternux_status_is_typed_and_keeps_identity_unverified(self):
        calls = []
        payload = {
            "command": "status", "status": "running", "timestamp": "2026-10-18T01:00:13Z",
            "version": "1.4.0", "x11_running": "yes", "pulseaudio": "stopped",
            "virgl": "stopped", "launcher": "present",
        }
        backend_payload = {"command": "backend", "status": "ok", "version": "1.4.0",
                           "backend": "zink", "renderer": "unknown", "vulkan": "yes",
                           "available_backends": "zink,virgl"}
        outputs = [json.dumps(payload), json.dumps(backend_payload)]
        def runner(args, **kwargs):
            calls.append((args, kwargs))
            return SimpleNamespace(returncode=0, stdout=outputs.pop(0))
        report = proot_diagnostics.inspect_native_ternux(
            which=lambda name: "/prefix/bin/ternux" if name == "ternux" else None,
            runner=runner,
        )
        self.assertEqual(report, {
            "availability": "available", "identity": "unverified", "version": "1.4.0",
            "status": "running", "x11_running": "yes", "pulseaudio": "stopped",
            "virgl": "stopped", "launcher": "present", "backend_availability": "available",
            "backend": "zink", "renderer": "unknown", "vulkan": "yes",
        })
        self.assertEqual(calls[0][0], ["/prefix/bin/ternux", "--json", "status"])
        self.assertEqual(calls[1][0], ["/prefix/bin/ternux", "--json", "backend", "show"])
        self.assertEqual(calls[0][1]["timeout"], 5)
        self.assertTrue(calls[0][1]["capture_output"])

    def test_native_backend_status_fails_unknown_without_discarding_host_status(self):
        outputs = [
            json.dumps({"command": "status", "status": "running", "version": "1.4.0",
                        "x11_running": "yes", "pulseaudio": "stopped", "virgl": "stopped",
                        "launcher": "present"}),
            "malformed backend response",
        ]
        report = proot_diagnostics.inspect_native_ternux(
            which=lambda name: "/prefix/bin/ternux" if name == "ternux" else None,
            runner=lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout=outputs.pop(0)),
        )
        self.assertEqual(report["availability"], "available")
        self.assertEqual(report["status"], "running")
        self.assertEqual(report["backend_availability"], "unknown")
        self.assertEqual(report["backend"], "unknown")
        self.assertIsNone(report["renderer"])

    def test_native_ternux_status_fails_closed_on_malformed_output(self):
        report = proot_diagnostics.inspect_native_ternux(
            which=lambda name: "/prefix/bin/ternux" if name == "ternux" else None,
            runner=lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout="{}"),
        )
        self.assertEqual(report["availability"], "unknown")
        self.assertEqual(report["status"], "unknown")
        self.assertEqual(report["identity"], "unverified")

    def test_unavailable_manager_and_unrecognized_output_remain_unknown(self):
        absent = proot_diagnostics.inspect_installed(which=lambda _name: None)
        failed = proot_diagnostics.inspect_installed(
            which=lambda _name: "/prefix/bin/proot-distro",
            runner=lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stdout="private error"),
        )
        malformed = proot_diagnostics.inspect_installed(
            which=lambda _name: "/prefix/bin/proot-distro",
            runner=lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout="unexpected format"),
        )
        self.assertEqual(absent["status"], "unavailable")
        self.assertEqual(failed["status"], "unknown")
        self.assertEqual(malformed["status"], "unknown")
        self.assertNotIn("private error", str(failed))


if __name__ == "__main__":
    unittest.main()
