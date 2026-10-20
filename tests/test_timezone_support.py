from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import timezone_support as tz  # noqa: E402
import management_authorization  # noqa: E402
import management_service  # noqa: E402
import management_sessions  # noqa: E402


def _android_tzdata(zone_name: str = "Fixture/Fixed", offset: int = 21600) -> bytes:
    # Minimal TZif v1 file: one fixed-offset type and one abbreviation.
    tzif = (b"TZif\0" + (b"\0" * 15)
            + struct.pack(">6I", 0, 0, 0, 0, 1, 4)
            + struct.pack(">lbb", offset, 0, 0) + b"BDT\0")
    index_offset = 24
    data_offset = index_offset + 52
    zonetab_offset = data_offset + len(tzif)
    name = zone_name.encode("ascii")
    entry = name.ljust(40, b"\0") + struct.pack(">III", 0, len(tzif), offset)
    return (b"tzdata2025a\0" + struct.pack(">III", index_offset, data_offset, zonetab_offset)
            + entry + tzif)


class TimezoneSupportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-timezone-")
        self.root = Path(self.temp.name)
        self.state = self.root / "state"
        self.state.mkdir(mode=0o700)
        self.prefix = self.root / "prefix"
        db = self.prefix / "share" / "zoneinfo"
        db.mkdir(parents=True)
        (db / "tzdata").write_bytes(_android_tzdata())

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_android_packed_database_parses_and_resolves_named_zone(self) -> None:
        data = (self.prefix / "share" / "zoneinfo" / "tzdata").read_bytes()
        version, index = tz._parse_android_database(data)
        self.assertEqual(version, "2025a")
        self.assertIn("Fixture/Fixed", index)
        zone = tz.get_timezone("Fixture/Fixed", prefix=str(self.prefix))
        value = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc).astimezone(zone)
        self.assertEqual(value.isoformat(), "2026-01-01T06:00:00+06:00")
        self.assertIn("Fixture/Fixed", tz.available_timezones(prefix=str(self.prefix)))

    def test_invalid_and_path_like_zone_names_rejected(self) -> None:
        for name in ("", "../UTC", "/etc/passwd", "Fixture//Fixed", "Fixture/../Fixed"):
            with self.subTest(name=name), self.assertRaises(tz.TimezoneError):
                tz.get_timezone(name, prefix=str(self.prefix))

    def test_unknown_zone_fails_closed(self) -> None:
        with self.assertRaisesRegex(tz.TimezoneError, "unknown or unavailable"):
            tz.get_timezone("Fixture/Missing", prefix=str(self.prefix))

    def test_status_and_default_work_without_creating_state_directory(self) -> None:
        missing = self.root / "not-created"
        self.assertEqual(tz.current_timezone(missing), "Asia/Dhaka")
        result = tz.status(missing, prefix=str(self.prefix))
        self.assertEqual(result["timezone"], "Asia/Dhaka")
        self.assertFalse(result["configured"])
        self.assertFalse(missing.exists())

    def test_default_timezone_and_preference_persistence(self) -> None:
        self.assertEqual(tz.current_timezone(self.state), "Asia/Dhaka")
        selected = tz.set_timezone(self.state, "Fixture/Fixed", prefix=str(self.prefix),
                                   now=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc))
        self.assertEqual(selected["timezone"], "Fixture/Fixed")
        self.assertEqual(selected["source"], "user")
        self.assertTrue(selected["available"])
        self.assertEqual(tz.current_timezone(self.state), "Fixture/Fixed")
        saved = self.state / "timezone.json"
        self.assertEqual(saved.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(saved.read_text())["schema_version"], 1)

    def test_invalid_timezone_is_not_persisted(self) -> None:
        with self.assertRaises(tz.TimezoneError):
            tz.set_timezone(self.state, "Fixture/Missing", prefix=str(self.prefix))
        self.assertFalse((self.state / "timezone.json").exists())

    def test_set_refuses_to_replace_symlinked_timezone_preference(self) -> None:
        target = self.root / "target"
        target.write_text("{}")
        (self.state / "timezone.json").symlink_to(target)
        with self.assertRaisesRegex(tz.TimezoneError, "identity or permissions"):
            tz.set_timezone(self.state, "UTC")
        self.assertEqual(target.read_text(), "{}")

    def test_symlinked_timezone_preference_is_rejected(self) -> None:
        target = self.root / "target"
        target.write_text("{}")
        (self.state / "timezone.json").symlink_to(target)
        with self.assertRaisesRegex(tz.TimezoneError, "identity or permissions"):
            tz.current_timezone(self.state)

    def test_shared_api_status_list_and_set_use_exact_scopes(self) -> None:
        env = {"TERMUX_VERSION": "test", "PREFIX": "/data/data/com.termux/files/usr", "HOME": str(self.root),
               "TERNUXX_STATE_DIR": str(self.state)}
        request = {"api_version": 1, "request_id": "timezone-test-0001",
                   "operation": "timezone.status", "args": {}}
        response = management_service.dispatch(request, env=env)
        self.assertTrue(response["ok"])
        self.assertEqual(response["data"]["timezone"], "Asia/Dhaka")
        listed = management_service.dispatch({**request, "request_id": "timezone-test-0002",
            "operation": "timezone.list"}, env=env)
        self.assertTrue(listed["ok"])
        self.assertIn("UTC", listed["data"]["timezones"])
        changed = management_service.dispatch({**request, "request_id": "timezone-test-0003",
            "operation": "timezone.set", "args": {"timezone": "UTC"}}, env=env)
        self.assertTrue(changed["ok"])
        self.assertEqual(changed["data"]["timezone"], "UTC")
        self.assertEqual(management_authorization.required_capability("timezone.set"), "timezone.manage")
        self.assertTrue(management_authorization.authorize("timezone.set", ["timezone.manage"]))
        self.assertFalse(management_authorization.authorize("timezone.set", ["diagnostics.read"]))
        self.assertIn("timezone.set", management_sessions.MUTATING_OPERATIONS)
        self.assertIn("timezone.status", management_sessions.READ_ONLY_OPERATIONS)

    def test_new_calendar_job_uses_saved_timezone_when_option_is_omitted(self) -> None:
        from unittest.mock import patch
        tz.set_timezone(self.state, "UTC")
        args = management_service._parser().parse_args([
            "--operation", "cron.jobs.create", "--job-name", "daily", "--job-action",
            "diagnostics.doctor", "--schedule-type", "calendar", "--calendar-mode",
            "daily", "--calendar-time", "07:30"])
        with patch.dict("os.environ", {"TERNUXX_STATE_DIR": str(self.state)}):
            job = management_service._cli_job(args)
        self.assertEqual(job["schedule"]["timezone"], "UTC")

    def test_installation_timezone_is_lower_precedence_than_saved_choice(self) -> None:
        self.assertEqual(tz.current_timezone(self.state, installation_timezone="Fixture/Fixed"),
                         "Fixture/Fixed")
        tz.set_timezone(self.state, "UTC", prefix=str(self.prefix))
        self.assertEqual(tz.current_timezone(self.state, installation_timezone="Fixture/Fixed"),
                         "UTC")


if __name__ == "__main__":
    unittest.main()
