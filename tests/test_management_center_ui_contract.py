from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "apps/management-center/management-center.c").read_text()


class ManagementCenterReplayGuestUiTests(unittest.TestCase):
    def test_replay_guest_resource_explains_its_action(self):
        self.assertIn('g_strcmp0(r->id, "proot.replay-guests") == 0', SOURCE)
        self.assertIn('Retire or restore an exact, idle Ternuxx replay guest', SOURCE)

    def test_replay_guest_dialog_copy_wraps_for_mobile_width(self):
        self.assertIn("gtk_label_set_wrap(GTK_LABEL(explanation),TRUE);", SOURCE)
        self.assertIn("gtk_label_set_max_width_chars(GTK_LABEL(explanation),46);", SOURCE)
        self.assertIn("gtk_window_set_default_size(GTK_WINDOW(window),420,300);", SOURCE)

    def test_replay_guest_apply_uses_inline_exact_target_confirmation(self):
        self.assertIn('gtk_widget_set_visible(c->replay_guest_confirmation, TRUE);', SOURCE)
        self.assertIn('gtk_button_set_label(GTK_BUTTON(c->replay_guest_apply_button)', SOURCE)
        self.assertIn('gtk_label_set_text(GTK_LABEL(c->replay_guest_confirmation_label), message);', SOURCE)
        self.assertIn('run_bridge(c, "guest-lifecycle-apply"', SOURCE)
        self.assertIn('gtk_label_set_text(GTK_LABEL(c->notice), "Replay guest action cancelled; no guest change was applied.");', SOURCE)
        self.assertIn('gtk_widget_set_visible(c->replay_guest_confirmation, FALSE);', SOURCE)

    def test_stale_inspection_cannot_overwrite_the_new_selection(self):
        self.assertIn('g_strcmp0(request->action, "inspect") == 0', SOURCE)
        self.assertIn('g_strcmp0(request->resource_id, c->selected_resource_id) != 0', SOURCE)

    def test_review_instance_opens_without_forwarding_to_the_running_app(self):
        self.assertIn('g_strcmp0(argv[1], "--review") == 0', SOURCE)
        self.assertIn('"dev.ternuxx.management-center.review"', SOURCE)
        self.assertIn('(test_attach || review_instance) ? G_APPLICATION_NON_UNIQUE', SOURCE)

    def test_gtk_test_attach_requires_a_verified_session_id(self):
        self.assertIn('"--test-attach-session"', SOURCE)
        self.assertIn('"^proot-[0-9a-f]{32}$"', SOURCE)
        self.assertIn('"Ternuxx GTK handoff test" : "Ternuxx Management Center"', SOURCE)
        self.assertIn('(test_attach || review_instance) ? G_APPLICATION_NON_UNIQUE : G_APPLICATION_DEFAULT_FLAGS', SOURCE)

    def test_proot_app_launcher_uses_friendly_selection_not_raw_ids(self):
        self.assertIn('run_bridge(data, "proot-app-options"', SOURCE)
        self.assertIn('show_proot_app_options(c, stdout_text,', SOURCE)
        self.assertIn('gtk_drop_down_new(G_LIST_MODEL(model), NULL)', SOURCE)
        self.assertIn('g_object_get_data(G_OBJECT(window), "proot-app-ids")', SOURCE)
        self.assertIn('" (Debian)"', SOURCE)
        self.assertNotIn('"App ID, for example files"', SOURCE)

    def test_proot_shortcut_manager_uses_live_named_catalog_and_exact_preview(self):
        self.assertIn('run_bridge(data, "proot-shortcut-options"', SOURCE)
        self.assertIn('g_strcmp0(request->action, "proot-shortcut-options") == 0', SOURCE)
        self.assertIn('shortcut_mode ? "Preview shortcut change" : "Launch app"', SOURCE)
        self.assertIn('run_bridge(c, "shortcut-preview", actions[action_index], target', SOURCE)
        self.assertIn('shortcut for the selected Debian app?', SOURCE)
        self.assertNotIn('Action: add or remove', SOURCE)

    def test_shortcut_sync_rollback_has_a_visible_shared_service_action(self):
        self.assertIn('gtk_button_new_with_label("Restore saved PRoot app menu…")', SOURCE)
        self.assertIn('gtk_widget_set_visible(c->proot_rollback_button, proot_apps);', SOURCE)
        self.assertIn('g_signal_connect(c->proot_rollback_button,"clicked",G_CALLBACK(show_proot_shortcut_rollbacks),c);', SOURCE)
        self.assertIn('run_bridge(data, "shortcut-sync-rollback-list"', SOURCE)
        self.assertIn('run_bridge(request->center, "shortcut-sync-rollback-preview"', SOURCE)
        self.assertIn('run_bridge(request->center, "shortcut-sync-rollback-apply"', SOURCE)
        self.assertIn('ask_proot_shortcut_rollback_confirmation(c, f[2], f[1], f[3]);', SOURCE)
        self.assertIn('gtk_alert_dialog_set_default_button(dialog, 0);', SOURCE)

    def test_single_replay_action_keeps_a_visible_action_pane(self):
        self.assertIn('gtk_widget_set_visible(c->proot_guest_button, proot_apps || replay_guests);', SOURCE)
        self.assertIn('gtk_widget_set_visible(c->replay_guest_actions, proot_apps || replay_guests);', SOURCE)
        self.assertIn('gtk_widget_set_visible(c->action_scroll, !replay_guests);', SOURCE)
        self.assertIn('gtk_box_append(GTK_BOX(right),c->replay_guest_actions);', SOURCE)


if __name__ == "__main__":
    unittest.main()
