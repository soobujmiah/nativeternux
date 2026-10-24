from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "apps/management-center/management-center.c").read_text()


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

    def test_catalog_is_the_source_for_visible_resources(self):
        self.assertIn('script, "catalog", NULL', SOURCE)
        self.assertIn('Connected to Native Termux shared management service', SOURCE)


if __name__ == "__main__":
    unittest.main()
