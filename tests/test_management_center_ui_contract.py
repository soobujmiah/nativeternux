from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "apps/management-center/management-center.c").read_text()
BRIDGE = (ROOT / "scripts/management_desktop_bridge.py").read_text()


class ManagementCenterNativeUiContractTests(unittest.TestCase):
    def test_gtk_client_has_no_guest_or_broker_controls(self):
        for retired in ("proot", "debian", "guest-lifecycle", "terminal_cli", "VteTerminal"):
            with self.subTest(retired=retired):
                self.assertNotIn(retired.lower(), SOURCE.lower())

    def test_review_instance_remains_available(self):
        self.assertIn('g_strcmp0(argv[1], "--review") == 0', SOURCE)
        self.assertIn('"dev.ternuxx.management-center.review"', SOURCE)

    def test_native_cpu_inference_controls_share_model_preview_and_stdin_prompt(self):
        for contract in ("cpu-model-preview", "cpu-model-apply", "run_bridge_input",
                         "G_SUBPROCESS_FLAGS_STDIN_PIPE", "inference.cpu.local"):
            with self.subTest(contract=contract):
                self.assertIn(contract, SOURCE)

    def test_graphics_selection_warns_about_experimental_candidate_and_future_scope(self):
        self.assertIn("KGSL option is experimental", SOURCE)
        self.assertIn("must already be extracted", SOURCE)
        self.assertIn("Ternuxx does not install it", SOURCE)
        self.assertIn("Experimental KGSL (already present)", SOURCE)

    def test_curated_native_app_client_uses_saved_preview_and_exact_confirmation(self):
        for contract in ("software.curated-apps", "software-preview", "software-apply",
                         "software-run", "HOME-relative file or directory path",
                         "^[0-9a-f]{64}$", "Review exact Native Termux APT transaction",
                         "Browse Native Termux apps"):
            with self.subTest(contract=contract):
                self.assertIn(contract, SOURCE)

    def test_gtk_cron_update_form_supports_name_and_enabled_fields(self):
        for contract in ('cron-update-field', '"name"', '"enabled"',
                         'g_strcmp0(name_value, "true")', 'g_strcmp0(name_value, "false")',
                         'run_bridge(c, "cron-preview", "update", job_id, field_value, name_value, NULL)'):
            with self.subTest(contract=contract):
                self.assertIn(contract, SOURCE)

    def test_gtk_cron_create_supports_every_schedule_type_via_typed_bridge(self):
        for contract in ("cron-schedule-type", "cron-schedule-extra", "cron-timezone",
                         'g_strcmp0(type_value, "cron")', 'g_strcmp0(type_value, "interval")',
                         'g_strcmp0(type_value, "calendar")', 'g_strcmp0(type_value, "one_time")',
                         'run_bridge_full(c, "cron-preview", "create"',
                         '"Optional IANA timezone for cron/daily; blank uses preference"',
                         '"Cron expression, interval seconds, HH:MM or ISO datetime"'):
            with self.subTest(contract=contract):
                self.assertIn(contract, SOURCE)

    def test_gtk_cron_read_details_use_typed_bridge_references(self):
        for contract in ("cron_target_entry", "Inspect saved job", "Preview next five runs",
                         "Inspect execution record", "inspect_cron_reference", "cron-inspect-kind"):
            self.assertIn(contract, SOURCE)
        for contract in ('action == "cron-inspect" and len(argv) == 3', 'job-[0-9a-f]{32}',
                         'exec-[0-9a-f]{32}', '"cron.jobs.next_runs"'):
            self.assertIn(contract, BRIDGE)

    def test_gtk_recovery_controls_are_read_only_and_bridge_ids_are_typed(self):
        for contract in ("List verified configuration backups", "Preview restore (read-only)",
                         "Preview restore rollback (read-only)", "inspect_recovery_reference",
                         "recovery_target_entry", "recovery-action"):
            self.assertIn(contract, SOURCE)
        for contract in ('action in {"recovery-status", "backup-list", "continuity-status"}',
                         '"restore-preview"', '"recovery-rollback-preview"',
                         '"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}"'):
            self.assertIn(contract, BRIDGE)

    def test_cron_scheduler_controls_use_explicit_confirmation_and_shared_bridge(self):
        for contract in ("cron_start_button", "cron_stop_button", "ask_cron_scheduler_confirmation",
                         "cron-scheduler-start", "cron-scheduler-stop", '"cron-scheduler", "start", "10"',
                         '"cron-scheduler", "stop"'):
            with self.subTest(contract=contract):
                self.assertIn(contract, SOURCE)

    def test_catalog_is_the_source_for_visible_resources(self):
        self.assertIn('script, "catalog", NULL', SOURCE)
        self.assertIn('Connected to Native Termux shared management service', SOURCE)


if __name__ == "__main__":
    unittest.main()
