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

    def test_stale_inspection_cannot_overwrite_the_new_selection(self):
        self.assertIn('g_strcmp0(request->action, "inspect") == 0', SOURCE)
        self.assertIn('g_strcmp0(request->resource_id, c->selected_resource_id) != 0', SOURCE)

    def test_single_replay_action_keeps_a_visible_action_pane(self):
        self.assertIn('gtk_widget_set_visible(c->proot_guest_button, proot_apps || replay_guests);', SOURCE)
        self.assertIn('gtk_widget_set_visible(c->replay_guest_actions, proot_apps || replay_guests);', SOURCE)
        self.assertIn('gtk_widget_set_visible(c->action_scroll, !replay_guests);', SOURCE)
        self.assertIn('gtk_box_append(GTK_BOX(right),c->replay_guest_actions);', SOURCE)


if __name__ == "__main__":
    unittest.main()
