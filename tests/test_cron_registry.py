from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import cron_registry  # noqa: E402
import management_authorization  # noqa: E402
import management_service  # noqa: E402

NOW = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)


class CronRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ternuxx-cron-")
        self.state = Path(self.temp.name) / ".local" / "share" / "ternuxx"
        self.state.mkdir(parents=True, mode=0o700)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def job(self, schedule_type="cron", schedule=None, **kwargs):
        if schedule is None:
            schedule = {"expression": "*/15 * * * *", "timezone": "UTC"}
        return cron_registry.new_job(name="sample", action_id="diagnostics.doctor",
                                     schedule_type=schedule_type, schedule=schedule,
                                     now=NOW, **kwargs)

    def test_cron_numeric_semantics_and_next_runs(self) -> None:
        job = self.job()
        self.assertEqual(cron_registry.next_runs(job, count=3, now=NOW), [
            "2026-01-01T00:15:00Z", "2026-01-01T00:30:00Z", "2026-01-01T00:45:00Z"])

    def test_cron_dom_dow_or_semantics(self) -> None:
        job = self.job(schedule={"expression": "0 0 1 * 1", "timezone": "UTC"})
        # January 1 is Thursday; the next match is Monday Jan 5 (DOW is OR'd with DOM).
        self.assertEqual(cron_registry.next_runs(job, count=1, now=NOW), ["2026-01-05T00:00:00Z"])

    def test_interval_is_anchor_based_and_skips_elapsed_slots(self) -> None:
        job = self.job("interval", {"interval_seconds": 60, "anchor_at": "2025-12-31T23:58:55Z"})
        self.assertEqual(cron_registry.next_runs(job, count=2, now=NOW), [
            "2026-01-01T00:00:55Z", "2026-01-01T00:01:55Z"])

    def test_daily_timezone_requires_available_zone_database(self) -> None:
        try:
            job = self.job("calendar", {"mode": "daily", "time": "02:30", "timezone": "Asia/Dhaka"})
            runs = cron_registry.next_runs(job, count=1, now=NOW)
        except cron_registry.CronError as exc:
            self.assertIn("unavailable", str(exc))
        else:
            self.assertTrue(runs)

    def test_timezone_resolver_is_replaceable_for_deterministic_fixtures(self) -> None:
        from unittest.mock import patch
        with patch("timezone_support.get_timezone", return_value=dt.timezone(dt.timedelta(hours=6))):
            job = self.job("calendar", {"mode": "daily", "time": "02:30", "timezone": "Asia/Dhaka"})
            self.assertEqual(cron_registry.next_runs(job, count=1, now=NOW), ["2026-01-01T20:30:00Z"])

    def test_specific_calendar_and_one_time(self) -> None:
        specific = self.job("calendar", {"mode": "specific", "datetime": "2026-01-02T06:00:00+06:00"})
        one_time = self.job("one_time", {"at": "2026-01-02T00:00:00Z"})
        self.assertEqual(cron_registry.next_runs(specific, now=NOW), ["2026-01-02T00:00:00Z"])
        self.assertEqual(cron_registry.next_runs(one_time, now=NOW), ["2026-01-02T00:00:00Z"])

    def test_rejects_invalid_schedules_and_policy_bounds(self) -> None:
        for expr in ("@daily", "0 0 * *", "61 * * * *", "0 0 32 * *", "*/0 * * * *"):
            with self.subTest(expr=expr), self.assertRaises(cron_registry.CronError):
                self.job(schedule={"expression": expr, "timezone": "UTC"})
        for change in ({"timeout_seconds": 0}, {"timeout_seconds": 86401},
                       {"missed_run_policy": "catch_up_forever"},
                       {"concurrency_policy": "parallel"},
                       {"retry_policy": {"max_attempts": 11, "delay_seconds": 0, "backoff": "fixed"}},
                       {"retry_policy": {"max_attempts": 2, "delay_seconds": 0, "backoff": []}},
                       {"missed_run_policy": []}, {"concurrency_policy": []}, {"output_policy": []}):
            job = self.job()
            job.update(change)
            with self.subTest(change=change), self.assertRaises(cron_registry.CronError):
                cron_registry.validate_job(job, now=NOW)

    def test_only_policies_supported_by_runtime_can_be_created(self) -> None:
        self.assertEqual(self.job()["environment"], "native-termux")
        unsupported = (
            {"environment": "debian-proot"},
            {"retry_policy": {"max_attempts": 2, "delay_seconds": 1, "backoff": "fixed"}},
            {"retry_policy": {"max_attempts": 1, "delay_seconds": 1, "backoff": "fixed"}},
            {"retry_policy": {"max_attempts": 1, "delay_seconds": 0, "backoff": "exponential"}},
            {"missed_run_policy": "run_once_after_recovery"},
            {"missed_run_policy": "catch_up_bounded"},
            {"concurrency_policy": "queue_one"},
            {"run_after_device_boot": True},
            {"run_after_scheduler_recovery": True},
            {"required_capabilities": ["cron.manage"]},
        )
        for change in unsupported:
            with self.subTest(change=change), self.assertRaises(cron_registry.CronError):
                self.job(**change)

    def test_legacy_unsupported_record_remains_readable_but_cannot_be_dispatched(self) -> None:
        import cron_execution
        job = self.job()
        job["retry_policy"] = {"max_attempts": 2, "delay_seconds": 1, "backoff": "fixed"}
        root = cron_registry._store_root(self.state)
        cron_registry._write(root, {"schema_version": 1, "jobs": [job]})
        self.assertEqual(cron_registry.list_jobs(self.state)[0]["retry_policy"]["max_attempts"], 2)
        with self.assertRaisesRegex(cron_execution.ExecutionError, "policy is unsupported"):
            cron_execution.claim_event(self.state, job_id=job["job_id"], event_id="legacy-event",
                scheduled_at="2026-01-01T00:00:00Z", scheduler_instance_id="fixture",
                now=NOW)
        self.assertFalse((self.state / "cron" / "executions.json").exists())

    def test_startup_trigger_policy_keeps_boot_and_recovery_distinct_and_dedupes_same_boot(self) -> None:
        job = self.job(enabled=True)
        job["run_after_device_boot"] = True
        job["run_after_scheduler_recovery"] = True
        events = [{"source": "scheduler_recovery", "event_id": "recovery-1", "boot_id": "boot-1"},
                  {"source": "device_boot", "event_id": "boot-1", "boot_id": "boot-1"},
                  {"source": "scheduler_recovery", "event_id": "recovery-1", "boot_id": "boot-1"}]
        self.assertEqual(cron_registry.plan_startup_triggers(job, events), [
            {"source": "device_boot", "event_id": "boot-1"}])
        self.assertEqual(cron_registry.plan_startup_triggers(job, events, processed_event_ids={"boot-1"}), [])
        recovery_only = cron_registry.plan_startup_triggers(job, [
            {"source": "scheduler_recovery", "event_id": "recovery-2", "boot_id": "boot-2"}])
        self.assertEqual(recovery_only, [{"source": "scheduler_recovery", "event_id": "recovery-2"}])

    def test_disabled_and_completed_one_time_jobs_do_not_get_startup_triggers(self) -> None:
        events = [{"source": "device_boot", "event_id": "boot-1"}]
        disabled = self.job(enabled=False)
        disabled["run_after_device_boot"] = True
        self.assertEqual(cron_registry.plan_startup_triggers(disabled, events), [])
        one_time = self.job("one_time", {"at": "2099-01-02T00:00:00Z"}, enabled=True)
        one_time["run_after_device_boot"] = True
        self.assertEqual(cron_registry.plan_startup_triggers(one_time, events, one_time_completed=True), [])

    def test_registry_crud_persists_atomically_and_read_only_does_not_create_store(self) -> None:
        self.assertEqual(cron_registry.status(self.state)["scheduler"], "not_installed")
        self.assertFalse((self.state / "cron").exists())
        job = cron_registry.create_job(self.state, self.job())
        root = self.state / "cron"
        self.assertEqual(root.stat().st_mode & 0o777, 0o700)
        self.assertEqual((root / "jobs.json").stat().st_mode & 0o777, 0o600)
        loaded = cron_registry.show_job(self.state, job["job_id"])
        self.assertEqual(loaded, job)
        updated = cron_registry.update_job(self.state, job["job_id"], {"enabled": True})
        self.assertTrue(updated["enabled"])
        with self.assertRaisesRegex(cron_registry.CronError, "delivery are not currently supported"):
            cron_registry.update_job(self.state, job["job_id"], {"run_after_device_boot": True})
        self.assertEqual(cron_registry.list_jobs(self.state)[0]["job_id"], job["job_id"])
        self.assertEqual(cron_registry.remove_job(self.state, job["job_id"])["execution_data_removed"], False)
        self.assertEqual(cron_registry.list_jobs(self.state), [])

    def test_corrupt_store_and_lock_fail_closed(self) -> None:
        job = self.job()
        self.assertEqual(cron_registry.create_job(self.state, job), job)
        path = self.state / "cron" / "jobs.json"
        path.write_text("not-json", encoding="utf-8")
        with self.assertRaises(cron_registry.CronError):
            cron_registry.list_jobs(self.state)
        path.unlink()
        lock = self.state / "cron" / cron_registry.LOCK_NAME
        lock.mkdir()
        with self.assertRaises(cron_registry.CronError):
            cron_registry.create_job(self.state, job)

    def test_preview_confirm_apply_create_update_remove_uses_exact_saved_plan(self) -> None:
        job = self.job()
        preview = cron_registry.preview_job_mutation(
            self.state, action="create", job=job, now=NOW)
        plan = preview["plan"]
        self.assertTrue(preview["confirmation_required"])
        self.assertEqual(plan["action"], "create")
        self.assertEqual(plan["after"], job)
        self.assertEqual(cron_registry.list_jobs(self.state), [])
        plan_path = self.state / "cron" / cron_registry.MUTATION_PLAN_STORE
        self.assertEqual(plan_path.stat().st_mode & 0o777, 0o600)
        created = cron_registry.apply_job_mutation(
            self.state, plan_id=plan["plan_id"], confirmed=True, now=NOW + dt.timedelta(seconds=1))
        self.assertEqual(created["job"], job)
        self.assertEqual(cron_registry.list_jobs(self.state), [job])

        update_preview = cron_registry.preview_job_mutation(
            self.state, action="update", job_id=job["job_id"],
            changes={"name": "renamed"}, now=NOW + dt.timedelta(seconds=2))
        updated = cron_registry.apply_job_mutation(
            self.state, plan_id=update_preview["plan"]["plan_id"], confirmed=True,
            now=NOW + dt.timedelta(seconds=3))
        self.assertEqual(updated["job"]["name"], "renamed")
        self.assertEqual(cron_registry.list_jobs(self.state)[0]["name"], "renamed")

        remove_preview = cron_registry.preview_job_mutation(
            self.state, action="remove", job_id=job["job_id"], now=NOW + dt.timedelta(seconds=4))
        removed = cron_registry.apply_job_mutation(
            self.state, plan_id=remove_preview["plan"]["plan_id"], confirmed=True,
            now=NOW + dt.timedelta(seconds=5))
        self.assertTrue(removed["removed"])
        self.assertEqual(cron_registry.list_jobs(self.state), [])

    def test_stale_and_expired_cron_plans_fail_without_overwriting_registry(self) -> None:
        first = self.job()
        preview = cron_registry.preview_job_mutation(
            self.state, action="create", job=first, now=NOW)
        concurrent = self.job()
        concurrent["name"] = "concurrent"
        cron_registry.create_job(self.state, concurrent)
        with self.assertRaisesRegex(cron_registry.CronError, "registry changed after preview"):
            cron_registry.apply_job_mutation(
                self.state, plan_id=preview["plan"]["plan_id"], confirmed=True,
                now=NOW + dt.timedelta(seconds=1))
        jobs = cron_registry.list_jobs(self.state)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["name"], "concurrent")

        expired = cron_registry.preview_job_mutation(
            self.state, action="remove", job_id=jobs[0]["job_id"], now=NOW)
        with self.assertRaisesRegex(cron_registry.CronError, "expired"):
            cron_registry.apply_job_mutation(
                self.state, plan_id=expired["plan"]["plan_id"], confirmed=True,
                now=NOW + dt.timedelta(seconds=cron_registry.MUTATION_PLAN_TTL_SECONDS + 1))
        self.assertEqual(cron_registry.list_jobs(self.state), jobs)

    def test_confirmation_and_private_plan_store_integrity_fail_closed(self) -> None:
        job = self.job()
        preview = cron_registry.preview_job_mutation(self.state, action="create", job=job, now=NOW)
        with self.assertRaisesRegex(cron_registry.CronError, "explicit confirmation"):
            cron_registry.apply_job_mutation(
                self.state, plan_id=preview["plan"]["plan_id"], confirmed=False, now=NOW)
        path = self.state / "cron" / cron_registry.MUTATION_PLAN_STORE
        path.unlink()
        path.symlink_to(self.state / "missing-target")
        with self.assertRaisesRegex(cron_registry.CronError, "identity or permissions are unsafe"):
            cron_registry.preview_job_mutation(self.state, action="create", job=job, now=NOW)

    def test_api_crud_and_read_write_authority(self) -> None:
        env = {"TERMUX_VERSION": "test", "PREFIX": "/data/data/com.termux/files/usr",
               "HOME": self.temp.name, "TERNUXX_STATE_DIR": str(self.state)}
        request = lambda operation, args={}: {"api_version": 1, "request_id": "cron-test-1234",
                                               "operation": operation, "args": args}
        self.assertEqual(management_authorization.required_capability("cron.jobs.list"), "diagnostics.read")
        self.assertEqual(management_authorization.required_capability("cron.jobs.mutation.preview"), "cron.manage")
        self.assertEqual(management_authorization.required_capability("cron.jobs.mutation.apply"), "cron.manage")
        self.assertTrue(management_authorization.authorize("cron.jobs.list", ["diagnostics.read"]))
        self.assertFalse(management_authorization.authorize("cron.jobs.mutation.apply", ["diagnostics.read"]))
        job = self.job()
        preview = management_service.dispatch(request("cron.jobs.mutation.preview", {
            "action": "create", "job": job}), env=env)
        self.assertTrue(preview["ok"], preview)
        self.assertEqual(cron_registry.list_jobs(self.state), [])
        direct = management_service.dispatch(request("cron.jobs.create", {"job": job}), env=env)
        self.assertFalse(direct["ok"])
        created = management_service.dispatch(request("cron.jobs.mutation.apply", {
            "plan_id": preview["data"]["plan"]["plan_id"], "confirmed": True}), env=env)
        self.assertTrue(created["ok"], created)
        shown = management_service.dispatch(request("cron.jobs.show", {"job_id": job["job_id"]}), env=env)
        self.assertEqual(shown["data"]["job"], job)
        preview = management_service.dispatch(request("cron.jobs.next_runs", {"job_id": job["job_id"], "count": 2}), env=env)
        self.assertEqual(len(preview["data"]["runs"]), 2)
        remove_preview = management_service.dispatch(request("cron.jobs.mutation.preview", {
            "action": "remove", "job_id": job["job_id"]}), env=env)
        self.assertTrue(remove_preview["ok"], remove_preview)
        removed = management_service.dispatch(request("cron.jobs.mutation.apply", {
            "plan_id": remove_preview["data"]["plan"]["plan_id"], "confirmed": True}), env=env)
        self.assertTrue(removed["ok"], removed)
        self.assertFalse(management_service.dispatch(request("cron.jobs.show", {"job_id": job["job_id"]}), env=env)["ok"])

    def test_cli_typed_create_and_preview_do_not_execute_jobs(self) -> None:
        from contextlib import redirect_stdout
        from io import StringIO
        from unittest.mock import patch
        env = {"TERMUX_VERSION": "test", "PREFIX": "/data/data/com.termux/files/usr",
               "HOME": self.temp.name, "TERNUXX_STATE_DIR": str(self.state)}
        output = StringIO()
        argv = ["--operation", "cron.jobs.mutation.preview", "--mutation-action", "create",
                "--job-name", "fixture", "--job-action", "diagnostics.doctor",
                "--schedule-type", "cron", "--cron-expression", "*/30 * * * *",
                "--timezone", "UTC", "--json"]
        with patch.dict("os.environ", env, clear=True), redirect_stdout(output):
            self.assertEqual(management_service.main(argv), 0)
        response = json.loads(output.getvalue())
        self.assertTrue(response["ok"])
        self.assertFalse(response["data"]["plan"]["after"]["enabled"])
        self.assertIsNone(response["data"]["plan"]["after"]["last_execution"])
        self.assertEqual(cron_registry.list_jobs(self.state), [])
        apply_output = StringIO()
        apply_argv = ["--operation", "cron.jobs.mutation.apply", "--yes", "--plan-id",
                      response["data"]["plan"]["plan_id"], "--json"]
        with patch.dict("os.environ", env, clear=True), redirect_stdout(apply_output):
            self.assertEqual(management_service.main(apply_argv), 0)
        applied = json.loads(apply_output.getvalue())
        self.assertTrue(applied["ok"], applied)
        self.assertEqual(len(cron_registry.list_jobs(self.state)), 1)


    def test_schema_declares_only_runtime_supported_execution_policies(self) -> None:
        schema = json.loads((ROOT / "schemas/cron-job-v1.schema.json").read_text())
        fields = schema["properties"]
        self.assertEqual(fields["environment"], {"const": "native-termux"})
        self.assertEqual(fields["missed_run_policy"], {"const": "skip"})
        self.assertEqual(fields["concurrency_policy"], {"const": "skip_overlap"})
        self.assertEqual(fields["retry_policy"]["properties"]["max_attempts"], {"const": 1})
        self.assertEqual(fields["retry_policy"]["properties"]["delay_seconds"], {"const": 0})
        self.assertEqual(fields["retry_policy"]["properties"]["backoff"], {"const": "fixed"})
        self.assertEqual(fields["run_after_device_boot"], {"const": False})
        self.assertEqual(fields["run_after_scheduler_recovery"], {"const": False})
        self.assertEqual(fields["required_capabilities"]["maxItems"], 0)
        self.assertIn("scheduler.self_test", fields["action_id"]["enum"])

    def test_one_time_must_be_future(self) -> None:
        with self.assertRaises(cron_registry.CronError):
            self.job("one_time", {"at": "2025-12-31T23:59:59Z"})


if __name__ == "__main__":
    unittest.main()
