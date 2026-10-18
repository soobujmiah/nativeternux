"""Tests for read-only boot and Wake Lock capability diagnostics."""

from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import runtime_diagnostics  # noqa: E402


class RuntimeDiagnosticsTests(unittest.TestCase):
    def test_boot_observer_script_is_executable_evidence_only(self) -> None:
        script = ROOT / "scripts/termux-boot/ternuxx-recovery"
        self.assertTrue(script.stat().st_mode & 0o111)
        source = script.read_text(encoding="utf-8")
        self.assertIn("boot-observe", source)
        self.assertNotIn("termux-wake-lock", source)
        self.assertNotIn("termux-wake-unlock", source)
        self.assertNotIn("sshd -", source)
        self.assertNotIn("proot-distro", source)

    def test_boot_status_detects_app_and_does_not_read_script_contents(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ternuxx-boot-status-") as temp:
            home = Path(temp)
            boot_dir = home / ".termux/boot"
            boot_dir.mkdir(parents=True)
            (boot_dir / "start.sh").write_text("private script contents", encoding="utf-8")
            def runner(args: list[str], **kwargs: object):
                return type("Result", (), {"returncode": 0, "stdout": "package:/private/apk/base.apk"})()
            result = runtime_diagnostics.inspect_boot(
                home=home, which=lambda cmd: "/bin/cmd" if cmd == "cmd" else "/bin/pm" if cmd == "pm" else None, runner=runner,
            )
            self.assertEqual(result["app"], "installed")
            self.assertEqual(result["script_directory"], "present")
            self.assertEqual(result["regular_script_count"], 1)
            self.assertEqual(result["non_executable_script_count"], 1)
            self.assertEqual(result["startup_policy"], "unknown")
            self.assertFalse(result["safety"]["script_contents_read"])

    def test_boot_status_fails_unknown_when_package_query_cannot_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ternuxx-boot-status-") as temp:
            result = runtime_diagnostics.inspect_boot(home=temp, which=lambda _cmd: None)
        self.assertEqual(result["app"], "unknown")
        self.assertEqual(result["startup_policy"], "not_configured")

    def test_boot_status_uses_cmd_package_when_pm_wrapper_is_unavailable(self) -> None:
        calls: list[list[str]] = []
        def runner(args: list[str], **kwargs: object):
            calls.append(args)
            return type("Result", (), {"returncode": 0, "stdout": "package:/data/app/com.termux.boot/base.apk\n"})()
        with tempfile.TemporaryDirectory(prefix="ternuxx-boot-status-") as temp:
            result = runtime_diagnostics.inspect_boot(
                home=temp, which=lambda cmd: "/bin/cmd" if cmd == "cmd" else None, runner=runner,
            )
        self.assertEqual(result["app"], "installed")
        self.assertEqual(calls[0], ["/bin/cmd", "package", "path", "com.termux.boot"])
        self.assertEqual(len(calls), 5)

    def test_boot_status_reports_enabled_package_and_boot_receiver_without_claiming_delivery(self) -> None:
        def runner(args: list[str], **kwargs: object):
            if args[-2:] == ["path", "com.termux.boot"]:
                output = "package:/data/app/base.apk"
            elif "-e" in args:
                output = "package:com.termux.boot"
            elif "-d" in args:
                output = ""
            elif "query-receivers" in args:
                output = "com.termux.boot/.BootReceiver"
            else:
                output = ""
            return type("Result", (), {"returncode": 0, "stdout": output})()
        with tempfile.TemporaryDirectory(prefix="ternuxx-boot-status-") as temp:
            result = runtime_diagnostics.inspect_boot(
                home=temp, which=lambda cmd: "/bin/cmd" if cmd == "cmd" else None, runner=runner,
            )
        self.assertEqual(result["app"], "installed")
        self.assertEqual(result["package_enabled"], "enabled")
        self.assertEqual(result["boot_completed_receiver"], "enabled")
        self.assertEqual(result["system_delivery_policy"], "unknown")

    def test_boot_status_distinguishes_disabled_boot_receiver(self) -> None:
        def runner(args: list[str], **kwargs: object):
            if "path" in args:
                output = "package:/data/app/base.apk"
            elif "-e" in args:
                output = "package:com.termux.boot"
            elif "-d" in args:
                output = ""
            elif "--query-flags" in args:
                output = "com.termux.boot/.BootReceiver"
            elif "query-receivers" in args:
                output = ""
            else:
                output = ""
            return type("Result", (), {"returncode": 0, "stdout": output})()
        with tempfile.TemporaryDirectory(prefix="ternuxx-boot-status-") as temp:
            result = runtime_diagnostics.inspect_boot(
                home=temp, which=lambda cmd: "/bin/cmd" if cmd == "cmd" else None, runner=runner,
            )
        self.assertEqual(result["package_enabled"], "enabled")
        self.assertEqual(result["boot_completed_receiver"], "disabled")

    def test_boot_status_falls_back_to_pm_and_does_not_infer_absence_from_empty_output(self) -> None:
        calls: list[list[str]] = []
        def runner(args: list[str], **kwargs: object):
            calls.append(args)
            if args[0] == "/bin/cmd":
                return type("Result", (), {"returncode": 1, "stdout": ""})()
            return type("Result", (), {"returncode": 0, "stdout": ""})()
        with tempfile.TemporaryDirectory(prefix="ternuxx-boot-status-") as temp:
            result = runtime_diagnostics.inspect_boot(
                home=temp, which=lambda cmd: "/bin/cmd" if cmd == "cmd" else "/bin/pm" if cmd == "pm" else None,
                runner=runner,
            )
        self.assertEqual(result["app"], "unknown")
        self.assertEqual(calls[:2], [["/bin/cmd", "package", "path", "com.termux.boot"],
                                     ["/bin/pm", "path", "com.termux.boot"]])
        self.assertGreater(len(calls), 2)

    def test_boot_status_reports_absence_only_from_explicit_package_error(self) -> None:
        def runner(args: list[str], **kwargs: object):
            return type("Result", (), {"returncode": 0, "stdout": "Unable to find package: com.termux.boot"})()
        with tempfile.TemporaryDirectory(prefix="ternuxx-boot-status-") as temp:
            result = runtime_diagnostics.inspect_boot(
                home=temp, which=lambda cmd: "/bin/cmd" if cmd == "cmd" else None, runner=runner,
            )
        self.assertEqual(result["app"], "not_installed")

    def test_boot_diagnostic_outcomes_match_strict_response_schema(self) -> None:
        schema = json.loads((ROOT / "schemas/termux-boot-diagnostics.schema.json").read_text())
        with tempfile.TemporaryDirectory(prefix="ternuxx-boot-schema-") as temp:
            reports = [
                runtime_diagnostics.inspect_boot(home=temp, which=lambda _cmd: None),
                runtime_diagnostics.inspect_boot(
                    home=temp, which=lambda cmd: "/bin/cmd" if cmd == "cmd" else None,
                    runner=lambda *_args, **_kwargs: type("Result", (), {"returncode": 0, "stdout": "package:/app.apk"})()),
                runtime_diagnostics.inspect_boot(
                    home=temp, which=lambda cmd: "/bin/cmd" if cmd == "cmd" else None,
                    runner=lambda *_args, **_kwargs: type("Result", (), {"returncode": 0, "stdout": "Unable to find package"})()),
            ]
        expected = set(schema["properties"])
        for report in reports:
            self.assertEqual(set(report), expected)
            self.assertEqual(report["component"], schema["properties"]["component"]["const"])
            self.assertIn(report["app"], schema["properties"]["app"]["enum"])
            self.assertIn(report["package_enabled"], schema["properties"]["package_enabled"]["enum"])
            self.assertIn(report["boot_completed_receiver"], schema["properties"]["boot_completed_receiver"]["enum"])
            self.assertEqual(report["system_delivery_policy"], "unknown")
            self.assertIn(report["script_directory"], schema["properties"]["script_directory"]["enum"])
            self.assertIn(report["startup_policy"], schema["properties"]["startup_policy"]["enum"])
            self.assertIs(report["safety"]["read_only"], True)
            self.assertIs(report["safety"]["script_contents_read"], False)

    def test_wakelock_status_never_executes_acquire_or_release(self) -> None:
        calls: list[str] = []
        def which(command: str) -> str | None:
            calls.append(command)
            return f"/bin/{command}"
        result = runtime_diagnostics.inspect_wakelock(which=which)
        self.assertEqual(result["active_lock_state"], "unknown")
        self.assertEqual(result["ownership_scope"], "global_unscoped")
        self.assertTrue(result["safety"]["acquire_or_release_invoked"] is False)
        self.assertEqual(calls, ["termux-wake-lock", "termux-wake-unlock"])


if __name__ == "__main__":
    unittest.main()
