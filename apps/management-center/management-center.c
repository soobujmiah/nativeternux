#include <gtk/gtk.h>
#include <vte/vte.h>
#include <string.h>

typedef struct { gchar *id, *category, *name, *status, *availability, *description, *operations; } Resource;
typedef struct { GtkWidget *window, *category_list, *resource_list, *details, *notice, *search, *action_scroll;
                 GtkWidget *start_button, *stop_button, *ssh_restart_button, *ssh_keys_button, *ssh_enroll_button, *ssh_revoke_button, *ssh_rollback_button, *ssh_generate_button, *ssh_autostart_button, *ssh_wakelock_button, *graphics_select_button, *graphics_api_button, *history_button, *logs_button, *audit_logs_button, *desktop_log_button, *cron_button, *cron_history_button, *cron_manage_button, *timezone_set_button, *proot_app_button, *proot_shortcut_button, *proot_list_button, *proot_sessions_button, *proot_recovery_button, *proot_probe_button, *proot_terminal_button, *proot_stop_button, *proot_confirm_button, *proot_cancel_button, *monitor_box, *monitor_enabled,
                 *monitor_interval, *monitor_unit, *monitor_focus, *monitor_launch; gchar *proot_pending_action, *proot_pending_session_id, *proot_pending_plan_id; GPtrArray *categories,
                 *resources; gchar *selected_category, *selected_resource_id; guint category_count; } Center;
typedef struct { Center *center; gchar *action; gchar *resource_id; gchar *detail_id; gchar *plan_id; } Request;
typedef struct { Center *center; gchar **argv; gchar *working_directory; } TerminalSpawn;
static Center *app_center;
static void run_bridge(Center *c, const gchar *action, const gchar *arg1, const gchar *arg2,
                       const gchar *arg3, const gchar *arg4, const gchar *arg5);
static void ask_ssh_confirmation(Center *c, const gchar *preview_action, const gchar *plan_id, const gchar *impact);
static void ask_ssh_rollback_confirmation(Center *c, const gchar *rollback_id, const gchar *plan_id, const gchar *effect);
static void choose_graphics_api(GtkButton *button, gpointer data);
static void ask_shortcut_confirmation(Center *c, const gchar *action, const gchar *app_id, const gchar *plan_id, const gchar *target, const gchar *transition);
static void ask_cron_confirmation(Center *c, const gchar *plan_id, const gchar *summary);
static void confirmed_action(GObject *source, GAsyncResult *result, gpointer user_data);
static void proot_app_cancel_clicked(GtkButton *button, gpointer data);
static void proot_recovery_submit(GtkButton *button, gpointer data);
static void show_management_log(GtkButton *button, gpointer data);
static void show_ssh_keys(GtkButton *button, gpointer data);
static void enroll_ssh_key(GtkButton *button, gpointer data);
static void revoke_ssh_key(GtkButton *button, gpointer data);
static void restore_ssh_key(GtkButton *button, gpointer data);
static void ssh_rollback_choice(GObject *source, GAsyncResult *result, gpointer user_data);
static void generate_ssh_key(GtkButton *button, gpointer data);
static void ssh_client_key_preview(GtkButton *button, gpointer data);
static void ask_ssh_client_key_confirmation(Center *c, const gchar *name, const gchar *plan_id, const gchar *path, const gchar *impact);
static void change_ssh_autostart(GtkButton *button, gpointer data);
static void change_ssh_wakelock(GtkButton *button, gpointer data);
static void ask_ssh_wakelock_confirmation(Center *c, const gchar *enabled, const gchar *plan_id, const gchar *effect);
static void change_ssh_wakelock(GtkButton *button, gpointer data) {
    (void)button; run_bridge(data, "ssh-wakelock-status", NULL, NULL, NULL, NULL, NULL);
}
static void ask_ssh_wakelock_confirmation(Center *c, const gchar *enabled,
                                          const gchar *plan_id, const gchar *effect) {
    gboolean desired = g_strcmp0(enabled, "true") == 0;
    gchar *message = g_strdup_printf("%s the managed SSH keep-awake preference?\n\n%s\n\nThe current SSH process and Wake Lock lease will remain unchanged.",
        desired ? "Enable" : "Disable", effect);
    GtkAlertDialog *dialog = gtk_alert_dialog_new("%s", message);
    const char *choices[] = {"Cancel", desired ? "Keep SSH awake" : "Do not keep SSH awake", NULL};
    gtk_alert_dialog_set_buttons(dialog, choices); gtk_alert_dialog_set_default_button(dialog, 0);
    Request *request = g_new0(Request, 1); request->center = c;
    request->action = g_strdup("ssh-wakelock-apply"); request->resource_id = g_strdup(enabled);
    request->plan_id = g_strdup(plan_id);
    gtk_alert_dialog_choose(dialog, GTK_WINDOW(c->window), NULL, confirmed_action, request);
    gtk_label_set_text(GTK_LABEL(c->notice), "Reviewing managed SSH Wake Lock preference");
    g_object_unref(dialog); g_free(message);
}

static void ask_ssh_autostart_confirmation(Center *c, const gchar *enabled, const gchar *plan_id, const gchar *effect);
static void ask_ssh_key_confirmation(Center *c, const gchar *action, const gchar *subject, const gchar *plan_id, const gchar *fingerprint);
static void show_cron_log(GtkButton *button, gpointer data);
static void show_desktop_log(GtkButton *button, gpointer data);
static gchar *python_path(void);

static void terminal_child_exited(VteTerminal *terminal, gint status, gpointer data) {
    (void)terminal;
    GtkWidget *window=data;
    Center *c=g_object_get_data(G_OBJECT(window),"terminal-center");
    if (c && c->notice) {
        gchar *message=g_strdup_printf("Debian terminal closed (exit status %d).",status);
        gtk_label_set_text(GTK_LABEL(c->notice),message);
        g_free(message);
    }
    gtk_window_destroy(GTK_WINDOW(window));
}

static void terminal_spawn_done(VteTerminal *terminal, GPid pid, GError *error, gpointer data) {
    (void)pid;
    TerminalSpawn *spawn = data;
    Center *c = spawn->center;
    if (error || !terminal) {
        if (terminal && error) {
            gchar *message = g_strdup_printf("Could not open the terminal client: %s\n", error->message);
            vte_terminal_feed_child(terminal, message, -1); g_free(message);
        }
        gtk_label_set_text(GTK_LABEL(c->notice), "Terminal client could not open; inspect its window.");
    } else {
        gtk_label_set_text(GTK_LABEL(c->notice), "Terminal client opened; closing its window detaches.");
    }
    g_strfreev(spawn->argv);
    g_free(spawn->working_directory);
    g_free(spawn);
}

static void spawn_interactive_terminal(Center *c, const gchar *session_id) {
    if (session_id && !g_regex_match_simple("^proot-[0-9a-f]{32}$", session_id, 0, 0)) {
        gtk_label_set_text(GTK_LABEL(c->notice), "The selected managed terminal identity is invalid.");
        return;
    }
    const gchar *root=g_getenv("TERNUXX_CHECKOUT");
    if (!root || !g_file_test(root,G_FILE_TEST_IS_DIR)) {
        gtk_label_set_text(GTK_LABEL(c->notice),"Native Ternuxx checkout is unavailable."); return;
    }
    GtkWidget *window=gtk_window_new();
    gtk_window_set_title(GTK_WINDOW(window),"Ternuxx Debian terminal");
    gtk_window_set_transient_for(GTK_WINDOW(window),GTK_WINDOW(c->window));
    g_object_set_data(G_OBJECT(window),"terminal-center",c);
    gtk_window_set_default_size(GTK_WINDOW(window),680,720);
    GtkWidget *box=gtk_box_new(GTK_ORIENTATION_VERTICAL,6);
    GtkWidget *hint=gtk_label_new(session_id
        ? "Attach to the selected managed Debian terminal. Close this window or press Ctrl-] to detach."
        : "Review the exact Debian login preview before confirming. Close this window or press Ctrl-] to detach.");
    gtk_label_set_wrap(GTK_LABEL(hint),TRUE); gtk_box_append(GTK_BOX(box),hint);
    VteTerminal *terminal=VTE_TERMINAL(vte_terminal_new());
    g_signal_connect_object(terminal,"child-exited",G_CALLBACK(terminal_child_exited),window,0);
    vte_terminal_set_scrollback_lines(terminal,2000);
    GtkWidget *scroll=gtk_scrolled_window_new(); gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(scroll),GTK_WIDGET(terminal));
    gtk_widget_set_vexpand(scroll,TRUE); gtk_box_append(GTK_BOX(box),scroll);
    gtk_window_set_child(GTK_WINDOW(window),box);
    TerminalSpawn *spawn=g_new0(TerminalSpawn,1);
    spawn->center=c;
    spawn->working_directory=g_strdup(root);
    spawn->argv=g_new0(gchar *,5);
    spawn->argv[0]=python_path();
    spawn->argv[1]=g_build_filename(root,"lib","terminal_cli.py",NULL);
    spawn->argv[2]=g_strdup(session_id ? "attach" : "start");
    spawn->argv[3]=session_id ? g_strdup(session_id) : NULL;
    vte_terminal_spawn_async(terminal,VTE_PTY_DEFAULT,spawn->working_directory,spawn->argv,NULL,G_SPAWN_DEFAULT,
                             NULL,NULL,NULL,10000,NULL,terminal_spawn_done,spawn);
    gtk_window_present(GTK_WINDOW(window));
}

static void terminal_choice_cancel(GtkButton *button, gpointer data) {
    (void)button; gtk_window_destroy(GTK_WINDOW(data));
}
static void terminal_choice_start(GtkButton *button, gpointer data) {
    (void)button; GtkWidget *dialog=data;
    Center *c=g_object_get_data(G_OBJECT(dialog),"terminal-center");
    gtk_window_destroy(GTK_WINDOW(dialog));
    spawn_interactive_terminal(c,NULL);
}
static void terminal_choice_attach(GtkButton *button, gpointer data) {
    GtkWidget *dialog=data;
    Center *c=g_object_get_data(G_OBJECT(dialog),"terminal-center");
    gchar *session_id=g_strdup(g_object_get_data(G_OBJECT(button),"terminal-session-id"));
    gtk_window_destroy(GTK_WINDOW(dialog));
    spawn_interactive_terminal(c,session_id);
    g_free(session_id);
}
static void show_terminal_choices(Center *c, const gchar *options) {
    GtkWidget *dialog=gtk_window_new();
    gtk_window_set_title(GTK_WINDOW(dialog),"Debian terminal");
    gtk_window_set_transient_for(GTK_WINDOW(dialog),GTK_WINDOW(c->window));
    gtk_window_set_modal(GTK_WINDOW(dialog),TRUE);
    gtk_window_set_default_size(GTK_WINDOW(dialog),460,330);
    g_object_set_data(G_OBJECT(dialog),"terminal-center",c);
    GtkWidget *box=gtk_box_new(GTK_ORIENTATION_VERTICAL,8);
    gtk_widget_set_margin_top(box,14);gtk_widget_set_margin_bottom(box,14);
    gtk_widget_set_margin_start(box,14);gtk_widget_set_margin_end(box,14);
    gtk_window_set_child(GTK_WINDOW(dialog),box);
    GtkWidget *intro=gtk_label_new("Start a fixed Debian terminal or attach to a verified running one.");
    gtk_label_set_wrap(GTK_LABEL(intro),TRUE);gtk_box_append(GTK_BOX(box),intro);
    GtkWidget *start=gtk_button_new_with_label("Start new Debian terminal…");
    gtk_box_append(GTK_BOX(box),start);
    g_signal_connect(start,"clicked",G_CALLBACK(terminal_choice_start),dialog);
    GtkWidget *scroll=gtk_scrolled_window_new();
    gtk_widget_set_vexpand(scroll,TRUE);
    GtkWidget *list=gtk_box_new(GTK_ORIENTATION_VERTICAL,6);
    gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(scroll),list);
    gtk_box_append(GTK_BOX(box),scroll);
    guint count=0;
    gchar **lines=g_strsplit(options ? options : "","\n",-1);
    for (guint i=0;lines[i];i++) {
        gchar **fields=g_strsplit(lines[i],"\t",3);
        if (fields[0] && g_strcmp0(fields[0],"S")==0 && fields[1] && fields[2]
                && g_regex_match_simple("^proot-[0-9a-f]{32}$",fields[1],0,0)) {
            GtkWidget *attach=gtk_button_new_with_label(fields[2]);
            gtk_widget_set_tooltip_text(attach,fields[1]);
            g_object_set_data_full(G_OBJECT(attach),"terminal-session-id",g_strdup(fields[1]),g_free);
            g_signal_connect(attach,"clicked",G_CALLBACK(terminal_choice_attach),dialog);
            gtk_box_append(GTK_BOX(list),attach);
            count++;
        }
        g_strfreev(fields);
    }
    g_strfreev(lines);
    if (!count) gtk_box_append(GTK_BOX(list),gtk_label_new("No verified running Debian terminal is available to attach."));
    GtkWidget *cancel=gtk_button_new_with_label("Cancel");
    gtk_box_append(GTK_BOX(box),cancel);
    g_signal_connect(cancel,"clicked",G_CALLBACK(terminal_choice_cancel),dialog);
    gtk_window_present(GTK_WINDOW(dialog));
}
static void open_interactive_terminal(GtkButton *button, gpointer data) {
    (void)button;run_bridge(data,"terminal-session-options",NULL,NULL,NULL,NULL,NULL);
}

static gchar *bridge_path(void) {
    const gchar *root = g_getenv("TERNUXX_CHECKOUT");
    if (!root || !*root) return NULL;
    return g_build_filename(root, "scripts", "management_desktop_bridge.py", NULL);
}
static gchar *python_path(void) {
    const gchar *prefix = g_getenv("PREFIX");
    return g_build_filename(prefix && *prefix ? prefix : "/data/data/com.termux/files/usr", "bin", "python", NULL);
}
static void set_text(Center *c, const gchar *text) {
    GtkTextBuffer *buffer = gtk_text_view_get_buffer(GTK_TEXT_VIEW(c->details));
    gtk_text_buffer_set_text(buffer, text ? text : "", -1);
}
static void clear_proot_confirmation(Center *c) {
    g_clear_pointer(&c->proot_pending_action,g_free); g_clear_pointer(&c->proot_pending_session_id,g_free);
    g_clear_pointer(&c->proot_pending_plan_id,g_free);
    gtk_widget_set_visible(c->proot_confirm_button,FALSE); gtk_widget_set_visible(c->proot_cancel_button,FALSE);
}
static void proot_confirm_clicked(GtkButton *button, gpointer data) {
    (void)button; Center *c=data;
    if (g_strcmp0(c->proot_pending_action,"proot-probe-apply")==0)
        run_bridge(c,"proot-probe-apply",c->proot_pending_plan_id,NULL,NULL,NULL,NULL);
    else if (g_strcmp0(c->proot_pending_action,"proot-session-stop-apply")==0)
        run_bridge(c,"proot-session-stop-apply",c->proot_pending_session_id,c->proot_pending_plan_id,NULL,NULL,NULL);
    clear_proot_confirmation(c);
}
static void proot_cancel_clicked(GtkButton *button, gpointer data) {
    (void)button; Center *c=data; clear_proot_confirmation(c);
    gtk_label_set_text(GTK_LABEL(c->notice),"PRoot action cancelled; no session change was applied.");
}
static void queue_proot_confirmation(Center *c, const gchar *action, const gchar *session_id,
                                     const gchar *plan_id, const gchar *message) {
    clear_proot_confirmation(c); c->proot_pending_action=g_strdup(action);
    c->proot_pending_session_id=session_id?g_strdup(session_id):NULL; c->proot_pending_plan_id=g_strdup(plan_id);
    set_text(c,message); gtk_button_set_label(GTK_BUTTON(c->proot_confirm_button),g_strcmp0(action,"proot-probe-apply")==0?"Start 300-second probe":"Stop this verified session"); gtk_widget_set_visible(c->proot_confirm_button,TRUE); gtk_widget_set_visible(c->proot_cancel_button,TRUE);
    gtk_label_set_text(GTK_LABEL(c->notice),"Review the exact PRoot plan, then confirm or cancel.");
}
static void request_done(GObject *source, GAsyncResult *result, gpointer user_data) {
    Request *request = user_data; Center *c = request->center; GError *error = NULL;
    gchar *stdout_text = NULL, *stderr_text = NULL;
    gboolean ok = g_subprocess_communicate_utf8_finish(G_SUBPROCESS(source), result,
        &stdout_text, &stderr_text, &error);
    if (!ok) {
        gtk_label_set_text(GTK_LABEL(c->notice), error ? error->message : "Request failed");
        g_clear_error(&error);
    } else {
        gboolean success = g_subprocess_get_successful(G_SUBPROCESS(source));
        if (g_strcmp0(request->action, "terminal-session-options") == 0 && success) {
            show_terminal_choices(c, stdout_text);
        } else if (g_strcmp0(request->action, "cron-preview") == 0 && stdout_text && g_str_has_prefix(stdout_text, "P\t")) {
            gchar **f = g_strsplit(stdout_text, "\t", 3);
            if (f[1] && f[2] && strlen(f[1]) == 32) {
                g_strchomp(f[2]);
                ask_cron_confirmation(c, f[1], f[2]);
            } else {
                gtk_label_set_text(GTK_LABEL(c->notice), "Cron preview response was invalid.");
            }
            g_strfreev(f);
        } else if (g_strcmp0(request->action, "ssh-wakelock-status") == 0 && stdout_text && g_str_has_prefix(stdout_text, "S\t")) {
            gchar *value = g_strdup(stdout_text + 2); g_strchomp(value);
            if (g_strcmp0(value, "true") == 0 || g_strcmp0(value, "false") == 0)
                run_bridge(c, "ssh-wakelock-preview", g_strcmp0(value, "true") == 0 ? "disabled" : "enabled", NULL, NULL, NULL, NULL);
            else gtk_label_set_text(GTK_LABEL(c->notice), "Managed SSH Wake Lock status was invalid.");
            g_free(value);
        } else if (g_strcmp0(request->action, "ssh-wakelock-preview") == 0 && stdout_text && g_str_has_prefix(stdout_text, "P\t")) {
            gchar **f = g_strsplit(stdout_text, "\t", 4);
            if (f[1] && g_regex_match_simple("^[0-9a-f]{32}$", f[1], 0, 0) && f[2]
                    && (g_strcmp0(f[2], "true") == 0 || g_strcmp0(f[2], "false") == 0) && f[3]) {
                g_strchomp(f[3]); ask_ssh_wakelock_confirmation(c, f[2], f[1], f[3]);
            } else gtk_label_set_text(GTK_LABEL(c->notice), "Managed SSH Wake Lock preview was invalid.");
            g_strfreev(f);
        } else if (g_strcmp0(request->action, "ssh-autostart-status") == 0 && stdout_text && g_str_has_prefix(stdout_text, "S\t")) {
            gchar **f = g_strsplit(stdout_text, "\t", 2);
            if (f[1]) { g_strchomp(f[1]); if (g_strcmp0(f[1], "true") == 0 || g_strcmp0(f[1], "false") == 0)
                run_bridge(c, "ssh-autostart-preview", g_strcmp0(f[1], "true") == 0 ? "disabled" : "enabled", NULL, NULL, NULL, NULL);
                else gtk_label_set_text(GTK_LABEL(c->notice), "SSH startup preference response was invalid."); }
            else gtk_label_set_text(GTK_LABEL(c->notice), "SSH startup preference response was incomplete.");
            g_strfreev(f);
        } else if (g_strcmp0(request->action, "ssh-autostart-preview") == 0 && stdout_text && g_str_has_prefix(stdout_text, "P\t")) {
            gchar **f = g_strsplit(stdout_text, "\t", 4);
            if (f[1] && g_regex_match_simple("^[0-9a-f]{32}$", f[1], 0, 0) && f[2]
                    && (g_strcmp0(f[2], "true") == 0 || g_strcmp0(f[2], "false") == 0) && f[3]) {
                g_strchomp(f[3]); ask_ssh_autostart_confirmation(c, f[2], f[1], f[3]);
            } else gtk_label_set_text(GTK_LABEL(c->notice), "SSH startup preference preview was invalid.");
            g_strfreev(f);
        } else if (g_strcmp0(request->action, "ssh-key-rollback-list") == 0 && stdout_text && g_str_has_prefix(stdout_text, "R\t")) {
            gchar **lines = g_strsplit(stdout_text, "\n", -1);
            GPtrArray *ids = g_ptr_array_new_with_free_func(g_free);
            GPtrArray *labels = g_ptr_array_new_with_free_func(g_free);
            for (guint i = 0; lines[i]; i++) {
                gchar **f = g_strsplit(lines[i], "\t", 5);
                if (f[0] && g_strcmp0(f[0], "R") == 0 && f[1] && g_strcmp0(f[1], "-") != 0
                        && g_regex_match_simple("^[0-9a-f]{32}$", f[1], 0, 0)) {
                    g_ptr_array_add(ids, g_strdup(f[1]));
                    g_ptr_array_add(labels, g_strdup_printf("%s key %s (%s)", f[3] ? f[3] : "changed",
                        f[2] ? f[2] : "fingerprint unavailable", f[4] ? f[4] : "saved"));
                }
                g_strfreev(f);
            }
            g_strfreev(lines);
            if (ids->len == 0) {
                gtk_label_set_text(GTK_LABEL(c->notice), "No saved SSH key changes are available to restore.");
            } else {
                gchar **choices = g_new0(gchar *, labels->len + 2); choices[0] = g_strdup("Cancel");
                GString *message = g_string_new("Choose a saved authorized-key change to restore:");
                GString *joined = g_string_new(NULL);
                for (guint i = 0; i < ids->len; i++) {
                    choices[i + 1] = g_strdup_printf("%u. %s", i + 1, (gchar *)g_ptr_array_index(labels, i));
                    g_string_append_printf(message, "\n\n%u. %s", i + 1, (gchar *)g_ptr_array_index(labels, i));
                    if (i) g_string_append_c(joined, ',');
                    g_string_append(joined, g_ptr_array_index(ids, i));
                }
                GtkAlertDialog *dialog = gtk_alert_dialog_new("%s", message->str);
                gtk_alert_dialog_set_buttons(dialog, (const char * const *)choices);
                gtk_alert_dialog_set_default_button(dialog, 0);
                Request *request = g_new0(Request, 1); request->center = c;
                request->action = g_strdup("ssh-key-rollback-select"); request->resource_id = g_string_free(joined, FALSE);
                gtk_alert_dialog_choose(dialog, GTK_WINDOW(c->window), NULL, ssh_rollback_choice, request);
                gtk_label_set_text(GTK_LABEL(c->notice), "Choose an exact saved SSH key state to review.");
                g_object_unref(dialog); g_string_free(message, TRUE);
                g_strfreev(choices);
            }
            g_ptr_array_unref(ids); g_ptr_array_unref(labels);
        } else if (g_strcmp0(request->action, "ssh-key-rollback-preview") == 0 && stdout_text && g_str_has_prefix(stdout_text, "P\t")) {
            gchar **f = g_strsplit(stdout_text, "\t", 4);
            if (f[1] && g_regex_match_simple("^[0-9a-f]{24}$", f[1], 0, 0) && f[2]
                    && g_regex_match_simple("^[0-9a-f]{32}$", f[2], 0, 0) && f[3]) {
                g_strchomp(f[3]); ask_ssh_rollback_confirmation(c, f[2], f[1], f[3]);
            } else gtk_label_set_text(GTK_LABEL(c->notice), "SSH recovery preview was invalid; no change was made.");
            g_strfreev(f);
        } else if (g_strcmp0(request->action, "ssh-client-key-preview") == 0 && stdout_text && g_str_has_prefix(stdout_text, "P\t")) {
            gchar **f = g_strsplit(stdout_text, "\t", 5);
            gchar *expected_path = f[2] ? g_strdup_printf("~/.ssh/ternuxx-keys/%s", f[2]) : NULL;
            gboolean valid = f[1] && g_regex_match_simple("^[0-9a-f]{32}$", f[1], 0, 0)
                && f[2] && g_regex_match_simple("^[a-z0-9][a-z0-9_-]{0,31}$", f[2], 0, 0)
                && f[3] && expected_path && g_strcmp0(f[3], expected_path) == 0 && f[4];
            if (valid) { g_strchomp(f[4]); ask_ssh_client_key_confirmation(c, f[2], f[1], f[3], f[4]); }
            else gtk_label_set_text(GTK_LABEL(c->notice), "Native SSH key preview was invalid; no key was created.");
            g_free(expected_path); g_strfreev(f);
        } else if ((g_strcmp0(request->action, "ssh-key-add-preview") == 0 || g_strcmp0(request->action, "ssh-key-remove-preview") == 0)
                && stdout_text && g_str_has_prefix(stdout_text, "P\t")) {
            gchar **f = g_strsplit(stdout_text, "\t", 4);
            gboolean valid = f[1] && strlen(f[1]) == 24 && f[2]
                && g_regex_match_simple("^SHA256:[A-Za-z0-9+/]{43}$", f[2], 0, 0) && f[3];
            if (valid) ask_ssh_key_confirmation(c, request->action, request->resource_id, f[1], f[2]);
            else gtk_label_set_text(GTK_LABEL(c->notice), "SSH key preview incomplete; no change was made.");
            g_strfreev(f);
        } else if (g_strcmp0(request->action, "shortcut-preview") == 0 && stdout_text && g_str_has_prefix(stdout_text, "P\t")) {
            gchar **f = g_strsplit(stdout_text, "\t", 6);
            if (f[1] && f[2] && f[3] && f[4] && g_strcmp0(f[2], "true") == 0
                    && g_strcmp0(f[1], "-") != 0 && strlen(f[1]) == 24) {
                g_strchomp(f[4]);
                ask_shortcut_confirmation(c, request->resource_id, request->detail_id, f[1], f[3], f[4]);
            } else {
                set_text(c, "Shortcut is already in the requested state. No change was made.");
                gtk_label_set_text(GTK_LABEL(c->notice), "No shortcut change needed");
            }
            g_strfreev(f);
        } else if ((g_strcmp0(request->action, "ssh-preview-start") == 0 || g_strcmp0(request->action, "ssh-preview-stop") == 0 || g_strcmp0(request->action, "ssh-preview-restart") == 0)
                && stdout_text && g_str_has_prefix(stdout_text, "P\t")) {
            gchar **f = g_strsplit(stdout_text, "\t", 4);
            if (f[1] && f[2] && f[3] && g_strcmp0(f[2], "true") == 0 && g_strcmp0(f[1], "-") != 0) {
                g_strchomp(f[3]); ask_ssh_confirmation(c, request->action, f[1], f[3]);
            } else {
                set_text(c, "Managed SSH 8023 is already in the requested state. No change was made.");
                gtk_label_set_text(GTK_LABEL(c->notice), "No service change needed");
            }
            g_strfreev(f);
        } else if ((g_strcmp0(request->action, "proot-probe-preview") == 0 || g_strcmp0(request->action, "proot-session-stop-preview") == 0)
                && stdout_text && g_str_has_prefix(stdout_text, "P\t")) {
            gchar **f = g_strsplit(stdout_text, "\t", 7);
            gboolean valid_plan = f[1] && g_str_has_prefix(f[1], "plan-") && strlen(f[1]) == 69;
            if (valid_plan && g_strcmp0(request->action, "proot-probe-preview") == 0 && f[2]) {
                g_strchomp(f[2]);
                gchar *message = g_strdup_printf("Start only the fixed 300-second isolated Debian diagnostic probe?\n\n%s", f[2]);
                queue_proot_confirmation(c, "proot-probe-apply", NULL, f[1], message);
                g_free(message);
            } else if (valid_plan && g_strcmp0(request->action, "proot-session-stop-preview") == 0
                       && f[2] && f[3] && f[4] && f[5] && f[6]) {
                g_strchomp(f[6]);
                gchar *message = g_strdup_printf("Close only this Ternuxx-owned PRoot session?\n\nSession: %s\nProfile: %s\nSignal: %s\nScope: %s\nImpact: %s",
                                                  f[3], f[2], f[4], f[5], f[6]);
                queue_proot_confirmation(c, "proot-session-stop-apply", f[3], f[1], message);
                g_free(message);
            } else {
                gtk_label_set_text(GTK_LABEL(c->notice), "PRoot preview did not contain a valid exact plan.");
            }
            g_strfreev(f);
        } else if (g_strcmp0(request->action, "monitor") == 0 && stdout_text && g_str_has_prefix(stdout_text,"M\t")) {
            gchar **f=g_strsplit(stdout_text,"\t",5);
            if(f[1]&&f[2]&&f[3]&&f[4]) {
                g_strchomp(f[4]);
                gtk_check_button_set_active(GTK_CHECK_BUTTON(c->monitor_enabled),g_strcmp0(f[1],"True")==0||g_strcmp0(f[1],"true")==0);
                gtk_spin_button_set_value(GTK_SPIN_BUTTON(c->monitor_interval),g_ascii_strtod(f[2],NULL)); gtk_drop_down_set_selected(GTK_DROP_DOWN(c->monitor_unit),0);
                gtk_check_button_set_active(GTK_CHECK_BUTTON(c->monitor_focus),g_strcmp0(f[3],"True")==0||g_strcmp0(f[3],"true")==0);
                gtk_check_button_set_active(GTK_CHECK_BUTTON(c->monitor_launch),g_strcmp0(f[4],"True")==0||g_strcmp0(f[4],"true")==0);
            }
            g_strfreev(f); set_text(c,"Android Activity/focus monitoring policy\n\nLinux GUI health is inspected separately. Status reads do not launch Termux:X11.");
        } else {
            const gchar *message = (stderr_text && *stderr_text) ? stderr_text :
                ((stdout_text && *stdout_text) ? stdout_text : "Request completed.");
            set_text(c, message);
        }
        const gchar *notice = success && g_strcmp0(request->action,"terminal-session-options")==0
            ? "Choose a managed terminal or start a new one."
            : success && g_strcmp0(request->action,"proot-session-stop-apply")==0
            ? "Verified Debian terminal stopped."
            : success ? "Shared management service request completed"
            : ((stderr_text && *stderr_text) ? stderr_text : "Operation failed; inspect the result details.");
        gtk_label_set_text(GTK_LABEL(c->notice), notice);
        gtk_widget_set_sensitive(c->start_button, TRUE); gtk_widget_set_sensitive(c->stop_button, TRUE); gtk_widget_set_sensitive(c->ssh_restart_button, TRUE);
        if (success && (g_strcmp0(request->action,"start-desktop")==0 || g_strcmp0(request->action,"stop-desktop")==0))
            run_bridge(c,"inspect","native.desktop.session",NULL,NULL,NULL,NULL);
        else if (success && (g_strcmp0(request->action,"ssh-apply-start")==0 || g_strcmp0(request->action,"ssh-apply-stop")==0 || g_strcmp0(request->action,"ssh-apply-restart")==0))
            run_bridge(c,"inspect","network.ssh.managed-8023",NULL,NULL,NULL,NULL);
        else if (success && (g_strcmp0(request->action,"ssh-key-add-apply")==0 || g_strcmp0(request->action,"ssh-key-remove-apply")==0))
            run_bridge(c,"ssh-keys-list",NULL,NULL,NULL,NULL,NULL);
        else if (success && g_strcmp0(request->action,"ssh-client-key-apply")==0)
            gtk_label_set_text(GTK_LABEL(c->notice), "Native recovery key created. Review the public-key path in the result, then enroll it separately if needed.");
        else if (success && g_strcmp0(request->action,"ssh-autostart-apply")==0)
            run_bridge(c,"ssh-autostart-status",NULL,NULL,NULL,NULL,NULL);
        else if (success && g_strcmp0(request->action,"ssh-wakelock-apply")==0)
            run_bridge(c,"ssh-wakelock-status",NULL,NULL,NULL,NULL,NULL);
        else if (success && g_strcmp0(request->action,"set-monitor")==0)
            run_bridge(c,"monitor",NULL,NULL,NULL,NULL,NULL);
        else if (success && g_strcmp0(request->action,"cron-apply")==0)
            run_bridge(c,"cron-jobs",NULL,NULL,NULL,NULL,NULL);
    }
    g_free(stdout_text); g_free(stderr_text); g_free(request->action); g_free(request->resource_id); g_free(request->detail_id); g_free(request->plan_id); g_free(request);
}
static void run_bridge(Center *c, const gchar *action, const gchar *arg1, const gchar *arg2,
                       const gchar *arg3, const gchar *arg4, const gchar *arg5) {
    gchar *script = bridge_path(), *python = python_path();
    if (!script || !g_file_test(script, G_FILE_TEST_IS_REGULAR)) {
        gtk_label_set_text(GTK_LABEL(c->notice), "Management bridge is unavailable; check TERNUXX_CHECKOUT.");
        g_free(script); g_free(python); return;
    }
    gboolean lifecycle = g_strcmp0(action,"start-desktop")==0 || g_strcmp0(action,"stop-desktop")==0
        || g_str_has_prefix(action,"ssh-preview-") || g_str_has_prefix(action,"ssh-apply-");
    if (lifecycle) { gtk_widget_set_sensitive(c->start_button,FALSE); gtk_widget_set_sensitive(c->stop_button,FALSE); gtk_widget_set_sensitive(c->ssh_restart_button,FALSE); }
    GPtrArray *argv = g_ptr_array_new(); g_ptr_array_add(argv, python); g_ptr_array_add(argv, script);
    g_ptr_array_add(argv, (gpointer)action);
    if (arg1) g_ptr_array_add(argv, (gpointer)arg1); if (arg2) g_ptr_array_add(argv, (gpointer)arg2);
    if (arg3) g_ptr_array_add(argv, (gpointer)arg3); if (arg4) g_ptr_array_add(argv, (gpointer)arg4); if (arg5) g_ptr_array_add(argv, (gpointer)arg5);
    g_ptr_array_add(argv, NULL);
    GError *error = NULL;
    GSubprocess *process = g_subprocess_newv((const gchar * const *)argv->pdata,
        G_SUBPROCESS_FLAGS_STDOUT_PIPE | G_SUBPROCESS_FLAGS_STDERR_PIPE, &error);
    gtk_label_set_text(GTK_LABEL(c->notice), "Working…");
    if (!process) {
        gtk_label_set_text(GTK_LABEL(c->notice), error ? error->message : "Could not start management request");
        g_clear_error(&error);
    } else {
        Request *request = g_new0(Request, 1); request->center = c;
        request->action = g_strdup(action); request->resource_id = g_strdup(arg1); request->detail_id = g_strdup(arg2); request->plan_id = g_strdup(arg3);
        g_subprocess_communicate_utf8_async(process, NULL, NULL, request_done, request);
        g_object_unref(process);
    }
    g_ptr_array_unref(argv); g_free(script); g_free(python);
}
static void resource_free(gpointer ptr) {
    Resource *r = ptr; if (!r) return; g_free(r->id); g_free(r->category); g_free(r->name);
    g_free(r->status); g_free(r->availability); g_free(r->description); g_free(r->operations); g_free(r);
}
static void clear_rows(GtkWidget *list) {
    GtkWidget *child; while ((child = gtk_widget_get_first_child(list)) != NULL) gtk_list_box_remove(GTK_LIST_BOX(list), child);
}
static const gchar *status_label(const gchar *status) {
    if (!status) return "Unknown";
    if (!g_strcmp0(status,"implemented")) return "Implemented";
    if (!g_strcmp0(status,"partial")) return "Partial";
    if (!g_strcmp0(status,"external")) return "Externally managed";
    if (!g_strcmp0(status,"unverified")) return "Unverified";
    if (!g_strcmp0(status,"unavailable")) return "Unavailable";
    if (!g_strcmp0(status,"planned")) return "Planned";
    if (!g_strcmp0(status,"unknown")) return "Unknown";
    return status;
}
static void show_resource(Center *c, Resource *r) {
    if (!r) return;
    const gchar *gui_actions = "Status and details only.";
    if (g_strcmp0(r->id, "native.desktop.session") == 0)
        gui_actions = "Check status · Start or stop desktop";
    else if (g_strcmp0(r->id, "graphics.native") == 0)
        gui_actions = "Check status · Verify OpenGL, GLES, Vulkan · Select backend";
    else if (g_strcmp0(r->id, "graphics.debian") == 0)
        gui_actions = "Check status · Verify OpenGL, GLES, Vulkan";
    else if (g_strcmp0(r->id, "network.ssh.managed-8023") == 0)
        gui_actions = "Check status · Generate a Native recovery key · Enroll, revoke, or restore public keys · Set SSH automatic start · Start, stop, or restart managed SSH (8023)";
    else if (g_strcmp0(r->id, "native.wakelock") == 0)
        gui_actions = "Inspect Wake Lock leases · Set managed SSH keep-awake preference";
    else if (g_strcmp0(r->id, "native.gui.activity-monitor") == 0)
        gui_actions = "Review or update monitoring settings";
    else if (g_strcmp0(r->id, "recovery.native-state") == 0)
        gui_actions = "View operation history";
    else if (g_strcmp0(r->id, "automation.cron-registry") == 0)
        gui_actions = "Manage scheduler and jobs · View run history";
    else if (g_strcmp0(r->id, "native.timezone") == 0)
        gui_actions = "View or change Ternuxx timezone";
    else if (g_strcmp0(r->id, "proot.debian.workloads") == 0)
        gui_actions = "Launch apps · Manage shortcuts · Inspect sessions";
    gchar *availability = g_strdup(r->availability && *r->availability ? r->availability : "unknown");
    g_strdelimit(availability, "-_", ' ');
    availability[0] = g_ascii_toupper(availability[0]);
    gchar *summary = g_strdup_printf("%s\n\nCapability: %s\nAvailability: %s\n\n%s\n\nIn this app\n%s",
        r->name, status_label(r->status), availability, r->description, gui_actions);
    set_text(c, summary); g_free(summary); g_free(availability);
    g_free(c->selected_resource_id); c->selected_resource_id = g_strdup(r->id);
    gboolean graphics = g_str_has_prefix(r->id, "graphics.");
    gboolean desktop = g_strcmp0(r->id, "native.desktop.session") == 0;
    gboolean managed_ssh = g_strcmp0(r->id, "network.ssh.managed-8023") == 0;
    gboolean wakelock = g_strcmp0(r->id, "native.wakelock") == 0;
    gboolean monitor = g_strcmp0(r->id, "native.gui.activity-monitor") == 0;
    gboolean history = g_strcmp0(r->id, "recovery.native-state") == 0;
    gboolean system_health = g_strcmp0(r->id, "native.system.health") == 0;
    gboolean cron = g_strcmp0(r->id, "automation.cron-registry") == 0;
    gboolean timezone = g_strcmp0(r->id, "native.timezone") == 0;
    gboolean proot_apps = g_strcmp0(r->id, "proot.debian.workloads") == 0;
    gtk_widget_set_visible(c->proot_sessions_button, proot_apps);
    gtk_widget_set_visible(c->proot_recovery_button, proot_apps);
    gtk_widget_set_visible(c->proot_probe_button, proot_apps);
    gtk_widget_set_visible(c->proot_terminal_button, proot_apps);
    gtk_widget_set_visible(c->proot_stop_button, proot_apps);
    gtk_widget_set_visible(c->proot_confirm_button, proot_apps && c->proot_pending_action != NULL);
    gtk_widget_set_visible(c->proot_cancel_button, proot_apps && c->proot_pending_action != NULL);
    gtk_widget_set_visible(c->history_button, history);
    gtk_widget_set_visible(c->desktop_log_button, system_health);
    gtk_widget_set_visible(c->logs_button, system_health);
    gtk_widget_set_visible(c->audit_logs_button, system_health);
    gtk_widget_set_visible(c->cron_button, cron);
    gtk_widget_set_visible(c->cron_history_button, cron);
    gtk_widget_set_visible(c->cron_manage_button, cron);
    gtk_widget_set_visible(c->timezone_set_button, timezone);
    gtk_widget_set_visible(c->proot_app_button, proot_apps);
    gtk_widget_set_visible(c->proot_shortcut_button, proot_apps);
    gtk_widget_set_visible(c->proot_list_button, proot_apps);
    gtk_widget_set_visible(c->graphics_api_button, graphics);
    gtk_button_set_label(GTK_BUTTON(c->start_button), managed_ssh ? "Start managed SSH (8023)" : "Start desktop");
    gtk_button_set_label(GTK_BUTTON(c->stop_button), managed_ssh ? "Stop managed SSH (8023)" : "Stop desktop");
    gtk_widget_set_visible(c->start_button, desktop || managed_ssh || graphics); gtk_widget_set_visible(c->stop_button, desktop || managed_ssh || graphics);
    gtk_button_set_label(GTK_BUTTON(c->ssh_restart_button), "Restart managed SSH (8023)");
    gtk_widget_set_visible(c->ssh_restart_button, managed_ssh);
    gtk_widget_set_visible(c->ssh_keys_button, managed_ssh);
    gtk_widget_set_visible(c->ssh_enroll_button, managed_ssh);
    gtk_widget_set_visible(c->ssh_revoke_button, managed_ssh);
    gtk_widget_set_visible(c->ssh_rollback_button, managed_ssh);
    gtk_widget_set_visible(c->ssh_generate_button, managed_ssh);
    gtk_widget_set_visible(c->ssh_autostart_button, managed_ssh);
    gtk_widget_set_visible(c->ssh_wakelock_button, wakelock);
    gtk_widget_set_visible(c->graphics_select_button, g_strcmp0(r->id, "graphics.native") == 0);
    if (graphics) { gtk_button_set_label(GTK_BUTTON(c->start_button), "Graphics status"); gtk_button_set_label(GTK_BUTTON(c->stop_button), "Verify OpenGL"); }
    else { gtk_button_set_label(GTK_BUTTON(c->start_button), managed_ssh ? "Start managed SSH (8023)" : "Start desktop"); gtk_button_set_label(GTK_BUTTON(c->stop_button), managed_ssh ? "Stop managed SSH (8023)" : "Stop desktop"); }
    gtk_widget_set_visible(c->monitor_box, monitor);
    GtkWidget *action_buttons[] = {c->start_button, c->stop_button, c->ssh_restart_button, c->ssh_keys_button, c->ssh_enroll_button, c->ssh_revoke_button, c->ssh_rollback_button, c->ssh_generate_button, c->ssh_autostart_button, c->ssh_wakelock_button, c->graphics_select_button,
        c->graphics_api_button, c->history_button, c->desktop_log_button, c->logs_button,
        c->audit_logs_button, c->cron_button, c->cron_history_button, c->cron_manage_button,
        c->timezone_set_button, c->proot_app_button, c->proot_shortcut_button,
        c->proot_list_button, c->proot_sessions_button, c->proot_recovery_button,
        c->proot_probe_button, c->proot_terminal_button, c->proot_stop_button,
        c->proot_confirm_button, c->proot_cancel_button};
    gboolean has_actions = FALSE;
    for (guint i = 0; i < G_N_ELEMENTS(action_buttons); i++)
        has_actions = has_actions || gtk_widget_get_visible(action_buttons[i]);
    gtk_widget_set_visible(c->action_scroll, has_actions);
    if (desktop || graphics) run_bridge(c, "inspect", r->id, NULL, NULL, NULL, NULL);
    else if (monitor) run_bridge(c, "monitor", NULL, NULL, NULL, NULL, NULL);
    else run_bridge(c, "inspect", r->id, NULL, NULL, NULL, NULL);
}
static void resource_selected(GtkListBox *box, GtkListBoxRow *row, gpointer data) {
    (void)box; Center *c = data; if (!row) return;
    Resource *r = g_object_get_data(G_OBJECT(row), "resource"); show_resource(c, r);
}
static gint resource_name_compare(gconstpointer a, gconstpointer b, gpointer data) {
    (void)data;
    const Resource *left = *(Resource * const *)a;
    const Resource *right = *(Resource * const *)b;
    return g_utf8_collate(left->name, right->name);
}
static void fill_resource_rows(Center *c) {
    clear_rows(c->resource_list); const gchar *query=gtk_editable_get_text(GTK_EDITABLE(c->search));
    gchar *needle=g_utf8_strdown(query?query:"",-1);
    GPtrArray *visible = g_ptr_array_new();
    for (guint i = 0; i < c->resources->len; i++) {
        Resource *r = g_ptr_array_index(c->resources, i); if (g_strcmp0(r->category, c->selected_category)) continue;
        gchar *raw=g_strconcat(r->name," ",r->description,NULL); gchar *haystack=g_utf8_strdown(raw,-1); g_free(raw);
        gboolean match=!needle||!*needle||g_strstr_len(haystack,-1,needle)!=NULL; g_free(haystack); if(!match) continue;
        g_ptr_array_add(visible, r);
    }
    g_ptr_array_sort_with_data(visible, (GCompareDataFunc)resource_name_compare, NULL);
    for (guint i = 0; i < visible->len; i++) {
        Resource *r = g_ptr_array_index(visible, i);
        GtkWidget *line = gtk_box_new(GTK_ORIENTATION_VERTICAL, 3); gchar *numbered = g_strdup_printf("%02u  %s", i + 1, r->name); GtkWidget *title = gtk_label_new(numbered); g_free(numbered);
        GtkWidget *meta = gtk_label_new(status_label(r->status)); gtk_label_set_wrap(GTK_LABEL(title),TRUE); gtk_label_set_wrap_mode(GTK_LABEL(title),PANGO_WRAP_WORD_CHAR); gtk_label_set_max_width_chars(GTK_LABEL(title),22); gtk_widget_set_hexpand(title,TRUE); gtk_widget_set_halign(title,GTK_ALIGN_FILL);
        gtk_widget_set_halign(meta, GTK_ALIGN_START); gtk_widget_add_css_class(meta, "dim-label");
        gtk_box_append(GTK_BOX(line), title); gtk_box_append(GTK_BOX(line), meta);
        GtkWidget *listrow = gtk_list_box_row_new(); gtk_list_box_row_set_child(GTK_LIST_BOX_ROW(listrow), line);
        g_object_set_data(G_OBJECT(listrow), "resource", r); gtk_list_box_append(GTK_LIST_BOX(c->resource_list), listrow);
    }
    g_ptr_array_unref(visible);
    GtkListBoxRow *first = gtk_list_box_get_row_at_index(GTK_LIST_BOX(c->resource_list), 0);
    if (first) gtk_list_box_select_row(GTK_LIST_BOX(c->resource_list), first);
    g_free(needle);
}
static void category_selected(GtkListBox *box, GtkListBoxRow *row, gpointer data) {
    (void)box; Center *c = data; if (!row) return;
    const gchar *id = g_object_get_data(G_OBJECT(row), "category-id");
    g_free(c->selected_category); c->selected_category = g_strdup(id); fill_resource_rows(c);
}
static void search_changed(GtkEditable *entry, gpointer data) {
    (void)entry; Center *c=data; if(c->selected_category) fill_resource_rows(c);
}
static void append_category(Center *c, gchar **fields) {
    GtkWidget *row = gtk_list_box_row_new(); gchar *numbered = g_strdup_printf("%u. %s", ++c->category_count, fields[2]); GtkWidget *label = gtk_label_new(numbered); g_free(numbered);
    gtk_label_set_wrap(GTK_LABEL(label),TRUE); gtk_label_set_wrap_mode(GTK_LABEL(label),PANGO_WRAP_WORD_CHAR); gtk_label_set_max_width_chars(GTK_LABEL(label),22); gtk_widget_set_hexpand(label,TRUE); gtk_widget_set_halign(label,GTK_ALIGN_FILL); gtk_list_box_row_set_child(GTK_LIST_BOX_ROW(row), label);
    g_object_set_data_full(G_OBJECT(row), "category-id", g_strdup(fields[1]), g_free);
    gtk_list_box_append(GTK_LIST_BOX(c->category_list), row);
}
static void append_resource(Center *c, gchar **f) {
    Resource *r = g_new0(Resource, 1); r->id=g_strdup(f[1]); r->category=g_strdup(f[2]);
    r->name=g_strdup(f[3]); r->status=g_strdup(f[4]); r->availability=g_strdup(f[5]); r->description=g_strdup(f[6]); r->operations=g_strdup(f[7] ? f[7] : "");
    g_ptr_array_add(c->resources, r);
}
static void load_catalog(Center *c) {
    gchar *script = bridge_path(), *python = python_path(), *out = NULL, *err = NULL; gint status = 0; GError *error = NULL;
    if (!script || !g_file_test(script, G_FILE_TEST_IS_REGULAR)) { gtk_label_set_text(GTK_LABEL(c->notice), "Set TERNUXX_CHECKOUT to the Native Termux checkout."); goto done; }
    gchar *argv[] = {python, script, "catalog", NULL};
    if (!g_spawn_sync(NULL, argv, NULL, G_SPAWN_SEARCH_PATH, NULL, NULL, &out, &err, &status, &error) || status != 0) {
        gtk_label_set_text(GTK_LABEL(c->notice), error ? error->message : (err && *err ? err : "Catalog request failed")); goto done;
    }
    gchar **lines = g_strsplit(out, "\n", -1);
    for (guint i=0; lines[i]; i++) {
        gchar **f=g_strsplit(lines[i], "\t", 8);
        if (f[0] && g_strcmp0(f[0],"C")==0 && f[1] && f[2]) append_category(c,f);
        else if (f[0] && g_strcmp0(f[0],"R")==0 && f[6]) append_resource(c,f);
        g_strfreev(f);
    }
    g_strfreev(lines); GtkListBoxRow *first=gtk_list_box_get_row_at_index(GTK_LIST_BOX(c->category_list),0);
    if (first) gtk_list_box_select_row(GTK_LIST_BOX(c->category_list), first);
    gtk_label_set_text(GTK_LABEL(c->notice), "Connected to Native Termux shared management service");
done:
    g_free(script); g_free(python); g_free(out); g_free(err); g_clear_error(&error);
}
static void confirmed_action(GObject *source, GAsyncResult *result, gpointer user_data) {
    GtkAlertDialog *dialog = GTK_ALERT_DIALOG(source); Request *request = user_data; GError *error = NULL;
    int choice = gtk_alert_dialog_choose_finish(dialog, result, &error);
    if (!error && choice == 1) {
        if (g_str_has_prefix(request->action, "ssh-apply-"))
            run_bridge(request->center, request->action, "confirmed", request->resource_id, NULL, NULL, NULL);
        else if (g_strcmp0(request->action, "ssh-key-add-apply") == 0 || g_strcmp0(request->action, "ssh-key-remove-apply") == 0)
            run_bridge(request->center, request->action, "confirmed", request->resource_id, request->plan_id, NULL, NULL);
        else if (g_strcmp0(request->action, "ssh-key-rollback-apply") == 0)
            run_bridge(request->center, "ssh-key-rollback-apply", request->resource_id, request->plan_id, NULL, NULL, NULL);
        else if (g_strcmp0(request->action, "ssh-client-key-apply") == 0)
            run_bridge(request->center, "ssh-client-key-apply", "confirmed", request->resource_id, request->plan_id, NULL, NULL);
        else if (g_strcmp0(request->action, "ssh-autostart-apply") == 0)
            run_bridge(request->center, "ssh-autostart-apply", "confirmed", request->resource_id, request->plan_id, NULL, NULL);
        else if (g_strcmp0(request->action, "ssh-wakelock-apply") == 0)
            run_bridge(request->center, "ssh-wakelock-apply", "confirmed", request->resource_id, request->plan_id, NULL, NULL);
        else if (g_strcmp0(request->action, "shortcut-apply") == 0)
            run_bridge(request->center, "shortcut-apply", request->resource_id, request->detail_id, request->plan_id, NULL, NULL);
        else if (g_strcmp0(request->action, "cron-apply") == 0)
            run_bridge(request->center, "cron-apply", request->plan_id, NULL, NULL, NULL, NULL);
        else if (g_strcmp0(request->action, "proot-probe-apply") == 0)
            run_bridge(request->center, "proot-probe-apply", request->plan_id, NULL, NULL, NULL, NULL);
        else if (g_strcmp0(request->action, "proot-session-stop-apply") == 0)
            run_bridge(request->center, "proot-session-stop-apply", request->resource_id, request->plan_id, NULL, NULL, NULL);
        else
            run_bridge(request->center, request->action, "confirmed", NULL, NULL, NULL, NULL);
    }
    else if (error) { gtk_label_set_text(GTK_LABEL(request->center->notice), error->message); g_clear_error(&error); }
    else gtk_label_set_text(GTK_LABEL(request->center->notice), "Action cancelled");
    g_free(request->action); g_free(request->resource_id); g_free(request->detail_id); g_free(request->plan_id); g_free(request);
}
static void ask_shortcut_confirmation(Center *c, const gchar *action, const gchar *app_id,
                                      const gchar *plan_id, const gchar *target, const gchar *transition) {
    gchar *message = g_strdup_printf("Confirm %s shortcut for %s?\n\nTarget: %s\nChange: %s\n\nOnly this exact Ternuxx-owned launcher will change.", action, app_id, target, transition);
    GtkAlertDialog *dialog = gtk_alert_dialog_new("%s", message);
    const char *choices[] = {"Cancel", "Confirm", NULL}; gtk_alert_dialog_set_buttons(dialog, choices);
    gtk_alert_dialog_set_default_button(dialog, 0);
    Request *request = g_new0(Request, 1); request->center = c;
    request->action = g_strdup("shortcut-apply"); request->resource_id = g_strdup(action);
    request->detail_id = g_strdup(app_id); request->plan_id = g_strdup(plan_id);
    gtk_alert_dialog_choose(dialog, GTK_WINDOW(c->window), NULL, confirmed_action, request);
    gtk_label_set_text(GTK_LABEL(c->notice), "Reviewing exact PRoot shortcut change");
    g_object_unref(dialog); g_free(message);
}
static void ask_ssh_confirmation(Center *c, const gchar *preview_action, const gchar *plan_id, const gchar *impact) {
    gboolean start = g_strcmp0(preview_action, "ssh-preview-start") == 0;
    gboolean restart = g_strcmp0(preview_action, "ssh-preview-restart") == 0;
    const gchar *verb = start ? "start" : restart ? "restart" : "stop";
    gchar *message = g_strdup_printf("Confirm %s of the Ternuxx-managed SSH service on 127.0.0.1:8023?\n\n%s\n\nManual development SSH on port 8022 is excluded.", verb, impact);
    GtkAlertDialog *dialog = gtk_alert_dialog_new("%s", message);
    const char *choices[] = {"Cancel", "Confirm", NULL}; gtk_alert_dialog_set_buttons(dialog, choices);
    gtk_alert_dialog_set_default_button(dialog, 0);
    Request *request = g_new0(Request, 1); request->center = c;
    request->action = g_strdup(start ? "ssh-apply-start" : restart ? "ssh-apply-restart" : "ssh-apply-stop"); request->resource_id = g_strdup(plan_id);
    gtk_alert_dialog_choose(dialog, GTK_WINDOW(c->window), NULL, confirmed_action, request);
    gtk_label_set_text(GTK_LABEL(c->notice), "Reviewing managed SSH service impact");
    g_object_unref(dialog); g_free(message);
}
static void confirm_action(GtkButton *button, gpointer data) {
    Center *c=data; gboolean start=GPOINTER_TO_INT(g_object_get_data(G_OBJECT(button),"start"));
    if (g_str_has_prefix(c->selected_resource_id ? c->selected_resource_id : "", "graphics.")) {
        const gchar *provider = g_strcmp0(c->selected_resource_id, "graphics.native") == 0 ? "native" : "debian";
        if (start) run_bridge(c, "inspect", c->selected_resource_id, NULL, NULL, NULL, NULL);
        else run_bridge(c, "graphics-verify", provider, "opengl", NULL, NULL, NULL);
        return;
    }
    if (g_strcmp0(c->selected_resource_id, "network.ssh.managed-8023") == 0) {
        const gchar *action = button == GTK_BUTTON(c->ssh_restart_button) ? "restart" : start ? "start" : "stop";
        gchar *preview = g_strdup_printf("ssh-preview-%s", action);
        run_bridge(c, preview, NULL, NULL, NULL, NULL, NULL);
        g_free(preview);
        return;
    }
    GtkAlertDialog *dialog=gtk_alert_dialog_new("Confirm native desktop %s?",start?"start":"stop");
    const char *choices[]={"Cancel","Confirm",NULL}; gtk_alert_dialog_set_buttons(dialog,choices);
    gtk_alert_dialog_set_default_button(dialog,0); Request *request=g_new0(Request,1);
    request->center=c; request->action=g_strdup(start?"start-desktop":"stop-desktop");
    gtk_alert_dialog_choose(dialog,GTK_WINDOW(c->window),NULL,confirmed_action,request); g_object_unref(dialog);
}
static void graphics_select_done(GObject *source, GAsyncResult *result, gpointer user_data) {
    GtkAlertDialog *dialog=GTK_ALERT_DIALOG(source); Center *c=user_data; GError *error=NULL;
    int choice=gtk_alert_dialog_choose_finish(dialog,result,&error);
    if (!error && choice == 1) run_bridge(c,"graphics-select","kgsl-freedreno",NULL,NULL,NULL,NULL);
    else if (!error && choice == 2) run_bridge(c,"graphics-select","system",NULL,NULL,NULL,NULL);
    else if (error) { gtk_label_set_text(GTK_LABEL(c->notice),error->message); g_clear_error(&error); }
}
static void select_graphics(GtkButton *button, gpointer data) {
    (void)button; Center *c=data;
    GtkAlertDialog *dialog=gtk_alert_dialog_new("Choose the Native graphics backend for future desktop starts.");
    const char *choices[]={"Cancel","KGSL Freedreno","System stack",NULL}; gtk_alert_dialog_set_buttons(dialog,choices);
    gtk_alert_dialog_set_default_button(dialog,0); gtk_alert_dialog_choose(dialog,GTK_WINDOW(c->window),NULL,graphics_select_done,c); g_object_unref(dialog);
}
static void graphics_api_done(GObject *source, GAsyncResult *result, gpointer user_data) {
    GtkAlertDialog *dialog = GTK_ALERT_DIALOG(source); Request *request = user_data; GError *error = NULL;
    int choice = gtk_alert_dialog_choose_finish(dialog, result, &error);
    if (!error && choice > 0) {
        const gchar *api = choice == 1 ? "opengl" : choice == 2 ? "gles" : "vulkan";
        run_bridge(request->center, "graphics-verify", request->resource_id, api, NULL, NULL, NULL);
    } else if (error) {
        gtk_label_set_text(GTK_LABEL(request->center->notice), error->message); g_clear_error(&error);
    }
    g_free(request->action); g_free(request->resource_id); g_free(request);
}
static void choose_graphics_api(GtkButton *button, gpointer data) {
    (void)button; Center *c = data;
    const gchar *provider = g_strcmp0(c->selected_resource_id, "graphics.native") == 0 ? "native" : "debian";
    GtkAlertDialog *dialog = gtk_alert_dialog_new("Choose the graphics API to verify.");
    const char *choices[] = {"Cancel", "OpenGL", "OpenGL ES", "Vulkan", NULL};
    gtk_alert_dialog_set_buttons(dialog, choices); gtk_alert_dialog_set_default_button(dialog, 0);
    Request *request = g_new0(Request, 1); request->center = c;
    request->action = g_strdup("graphics-verify"); request->resource_id = g_strdup(provider);
    gtk_alert_dialog_choose(dialog, GTK_WINDOW(c->window), NULL, graphics_api_done, request);
    g_object_unref(dialog);
}
static void show_history(GtkButton *button, gpointer data) {
    (void)button; run_bridge(data, "history", NULL, NULL, NULL, NULL, NULL);
}
static void cron_form_submit(GtkButton *button, gpointer data) {
    (void)data;
    Center *c = g_object_get_data(G_OBJECT(button), "cron-center");
    GtkWidget *mode = g_object_get_data(G_OBJECT(button), "cron-mode");
    GtkWidget *id = g_object_get_data(G_OBJECT(button), "cron-id");
    GtkWidget *name = g_object_get_data(G_OBJECT(button), "cron-name");
    GtkWidget *action = g_object_get_data(G_OBJECT(button), "cron-action");
    GtkWidget *expr = g_object_get_data(G_OBJECT(button), "cron-expr");
    const gchar *kind = gtk_editable_get_text(GTK_EDITABLE(mode));
    const gchar *job_id = gtk_editable_get_text(GTK_EDITABLE(id));
    const gchar *name_value = gtk_editable_get_text(GTK_EDITABLE(name));
    const gchar *action_id = gtk_editable_get_text(GTK_EDITABLE(action));
    const gchar *cron_expr = gtk_editable_get_text(GTK_EDITABLE(expr));
    if (g_strcmp0(kind, "create") == 0) {
        if (!*name_value || !*action_id || !*cron_expr) {
            gtk_label_set_text(GTK_LABEL(c->notice), "Create needs a name, safe action ID and five-field cron expression.");
            return;
        }
        run_bridge(c, "cron-preview", "create", name_value, action_id, cron_expr, NULL);
    } else if (g_strcmp0(kind, "update") == 0) {
        if (!*job_id || !*name_value) {
            gtk_label_set_text(GTK_LABEL(c->notice), "Update needs a saved job ID and new name.");
            return;
        }
        run_bridge(c, "cron-preview", "update", job_id, "name", name_value, NULL);
    } else if (g_strcmp0(kind, "remove") == 0) {
        if (!*job_id) {
            gtk_label_set_text(GTK_LABEL(c->notice), "Remove needs a saved job ID.");
            return;
        }
        run_bridge(c, "cron-preview", "remove", job_id, NULL, NULL, NULL);
    } else {
        gtk_label_set_text(GTK_LABEL(c->notice), "Choose create, update, or remove.");
    }
}

static void show_cron_form(GtkButton *button, gpointer data) {
    (void)button;
    Center *c = data;
    GtkWidget *win = gtk_window_new();
    gtk_window_set_title(GTK_WINDOW(win), "Manage Cron job");
    gtk_window_set_transient_for(GTK_WINDOW(win), GTK_WINDOW(c->window));
    gtk_window_set_modal(GTK_WINDOW(win), TRUE);
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_widget_set_margin_top(box, 14);
    gtk_widget_set_margin_bottom(box, 14);
    gtk_widget_set_margin_start(box, 14);
    gtk_widget_set_margin_end(box, 14);
    gtk_window_set_child(GTK_WINDOW(win), box);
    gtk_box_append(GTK_BOX(box), gtk_label_new("Preview is saved first; a separate confirmation applies that exact plan."));
    GtkWidget *mode = gtk_entry_new();
    gtk_editable_set_text(GTK_EDITABLE(mode), "create");
    gtk_entry_set_placeholder_text(GTK_ENTRY(mode), "create, update, or remove");
    gtk_box_append(GTK_BOX(box), mode);
    GtkWidget *id = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(id), "Saved job ID (update/remove)");
    gtk_box_append(GTK_BOX(box), id);
    GtkWidget *name = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(name), "Job name (create/update)");
    gtk_box_append(GTK_BOX(box), name);
    GtkWidget *action = gtk_entry_new();
    gtk_editable_set_text(GTK_EDITABLE(action), "diagnostics.doctor");
    gtk_entry_set_placeholder_text(GTK_ENTRY(action), "Registered safe action ID");
    gtk_box_append(GTK_BOX(box), action);
    GtkWidget *expr = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(expr), "Five-field cron expression");
    gtk_box_append(GTK_BOX(box), expr);
    GtkWidget *submit = gtk_button_new_with_label("Preview Cron change");
    g_object_set_data(G_OBJECT(submit), "cron-center", c);
    g_object_set_data(G_OBJECT(submit), "cron-mode", mode);
    g_object_set_data(G_OBJECT(submit), "cron-id", id);
    g_object_set_data(G_OBJECT(submit), "cron-name", name);
    g_object_set_data(G_OBJECT(submit), "cron-action", action);
    g_object_set_data(G_OBJECT(submit), "cron-expr", expr);
    g_signal_connect(submit, "clicked", G_CALLBACK(cron_form_submit), NULL);
    gtk_box_append(GTK_BOX(box), submit);
    gtk_window_present(GTK_WINDOW(win));
}

static void ask_cron_confirmation(Center *c, const gchar *plan_id, const gchar *summary) {
    gchar *message = g_strdup_printf("Review this saved Cron change and confirm only if it matches your request:\n\n%s", summary);
    GtkAlertDialog *dialog = gtk_alert_dialog_new("%s", message);
    const char *choices[] = {"Cancel", "Apply exact plan", NULL};
    gtk_alert_dialog_set_buttons(dialog, choices);
    gtk_alert_dialog_set_default_button(dialog, 0);
    Request *request = g_new0(Request, 1);
    request->center = c;
    request->action = g_strdup("cron-apply");
    request->plan_id = g_strdup(plan_id);
    gtk_alert_dialog_choose(dialog, GTK_WINDOW(c->window), NULL, confirmed_action, request);
    g_object_unref(dialog);
    g_free(message);
}
static void show_cron_jobs(GtkButton *button, gpointer data) {
    (void)button; run_bridge(data, "cron-jobs", NULL, NULL, NULL, NULL, NULL);
}
static void show_proot_sessions(GtkButton *button, gpointer data) {
    (void)button; run_bridge(data, "proot-session-list", NULL, NULL, NULL, NULL, NULL);
}
static void proot_recovery_clicked(GtkButton *button, gpointer data) {
    (void)button; Center *c = data; GtkWidget *window = gtk_window_new();
    gtk_window_set_title(GTK_WINDOW(window), "Inspect PRoot session recovery");
    gtk_window_set_transient_for(GTK_WINDOW(window), GTK_WINDOW(c->window)); gtk_window_set_modal(GTK_WINDOW(window), TRUE);
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8); gtk_widget_set_margin_top(box, 14);
    gtk_widget_set_margin_bottom(box, 14); gtk_widget_set_margin_start(box, 14); gtk_widget_set_margin_end(box, 14);
    gtk_window_set_child(GTK_WINDOW(window), box);
    gtk_box_append(GTK_BOX(box), gtk_label_new("Copy an exact session ID from List PRoot sessions. This action only inspects recovery state."));
    GtkWidget *entry = gtk_entry_new(); gtk_entry_set_placeholder_text(GTK_ENTRY(entry), "proot- plus 32 lowercase hex characters"); gtk_box_append(GTK_BOX(box), entry);
    GtkWidget *row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8); GtkWidget *cancel = gtk_button_new_with_label("Cancel");
    GtkWidget *inspect = gtk_button_new_with_label("Inspect recovery"); gtk_box_append(GTK_BOX(row), cancel);
    gtk_box_append(GTK_BOX(row), inspect); gtk_box_append(GTK_BOX(box), row);
    g_object_set_data(G_OBJECT(window), "stop-center", c); g_object_set_data(G_OBJECT(window), "stop-entry", entry);
    g_signal_connect(cancel, "clicked", G_CALLBACK(proot_app_cancel_clicked), window);
    g_signal_connect(inspect, "clicked", G_CALLBACK(proot_recovery_submit), window); gtk_window_present(GTK_WINDOW(window));
}
static void proot_recovery_submit(GtkButton *button, gpointer data) {
    (void)button; GtkWidget *window=data; Center *c=g_object_get_data(G_OBJECT(window),"stop-center");
    GtkWidget *entry=g_object_get_data(G_OBJECT(window),"stop-entry"); const gchar *id=gtk_editable_get_text(GTK_EDITABLE(entry));
    if (!id || strlen(id)!=38 || !g_str_has_prefix(id,"proot-")) {
        gtk_label_set_text(GTK_LABEL(c->notice),"Enter the exact proot- session ID from the session inventory."); return;
    }
    run_bridge(c,"proot-session-recovery",id,NULL,NULL,NULL,NULL); gtk_window_destroy(GTK_WINDOW(window));
}
static void start_proot_probe(GtkButton *button, gpointer data) {
    (void)button; run_bridge(data, "proot-probe-preview", NULL, NULL, NULL, NULL, NULL);
}
static void proot_stop_preview_clicked(GtkButton *button, gpointer data) {
    (void)button; GtkWidget *window = data;
    Center *c = g_object_get_data(G_OBJECT(window), "stop-center");
    GtkWidget *entry = g_object_get_data(G_OBJECT(window), "stop-entry");
    const gchar *id = gtk_editable_get_text(GTK_EDITABLE(entry));
    if (!id || strlen(id) != 38 || !g_str_has_prefix(id, "proot-")) {
        gtk_label_set_text(GTK_LABEL(c->notice), "Enter the exact proot- session ID from the session inventory."); return;
    }
    run_bridge(c, "proot-session-stop-preview", id, NULL, NULL, NULL, NULL);
    gtk_window_destroy(GTK_WINDOW(window));
}
static void stop_proot_session(GtkButton *button, gpointer data) {
    (void)button; Center *c = data; GtkWidget *window = gtk_window_new();
    gtk_window_set_title(GTK_WINDOW(window), "Stop a verified PRoot session");
    gtk_window_set_transient_for(GTK_WINDOW(window), GTK_WINDOW(c->window));
    gtk_window_set_modal(GTK_WINDOW(window), TRUE);
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_widget_set_margin_top(box, 14); gtk_widget_set_margin_bottom(box, 14);
    gtk_widget_set_margin_start(box, 14); gtk_widget_set_margin_end(box, 14);
    gtk_window_set_child(GTK_WINDOW(window), box);
    gtk_box_append(GTK_BOX(box), gtk_label_new("List sessions first. Enter one exact session ID; a fresh ownership preview and confirmation are required."));
    GtkWidget *entry = gtk_entry_new(); gtk_entry_set_placeholder_text(GTK_ENTRY(entry), "proot- plus 32 lowercase hex characters");
    gtk_box_append(GTK_BOX(box), entry);
    GtkWidget *row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    GtkWidget *cancel = gtk_button_new_with_label("Cancel"); GtkWidget *preview = gtk_button_new_with_label("Preview stop");
    gtk_box_append(GTK_BOX(row), cancel); gtk_box_append(GTK_BOX(row), preview); gtk_box_append(GTK_BOX(box), row);
    g_object_set_data(G_OBJECT(window), "stop-center", c); g_object_set_data(G_OBJECT(window), "stop-entry", entry);
    g_signal_connect(cancel, "clicked", G_CALLBACK(proot_app_cancel_clicked), window);
    g_signal_connect(preview, "clicked", G_CALLBACK(proot_stop_preview_clicked), window);
    gtk_window_present(GTK_WINDOW(window));
}
static void show_proot_shortcuts(GtkButton *button, gpointer data) {
    (void)button; run_bridge(data, "shortcut-list", NULL, NULL, NULL, NULL, NULL);
}
static void show_desktop_log(GtkButton *button, gpointer data) {
    (void)button; run_bridge(data, "logs-read", "native-desktop", NULL, NULL, NULL, NULL);
}
static void show_ssh_keys(GtkButton *button, gpointer data) {
    (void)button; run_bridge(data, "ssh-keys-list", NULL, NULL, NULL, NULL, NULL);
}

static void ssh_key_dialog_cancel(GtkButton *button, gpointer data) {
    (void)button; gtk_window_destroy(GTK_WINDOW(data));
}
static void ssh_key_preview_clicked(GtkButton *button, gpointer data) {
    (void)button; GtkWidget *window = data;
    Center *c = g_object_get_data(G_OBJECT(window), "ssh-key-center");
    const gchar *action = g_object_get_data(G_OBJECT(window), "ssh-key-action");
    GtkWidget *field = g_object_get_data(G_OBJECT(window), "ssh-key-field");
    gchar *subject = NULL;
    if (g_strcmp0(action, "ssh-key-add-preview") == 0) {
        GtkTextBuffer *buffer = gtk_text_view_get_buffer(GTK_TEXT_VIEW(field));
        GtkTextIter start, end; gtk_text_buffer_get_bounds(buffer, &start, &end);
        subject = gtk_text_buffer_get_text(buffer, &start, &end, FALSE); g_strstrip(subject);
        if (!*subject || strchr(subject, '\n') || strchr(subject, '\r') || strlen(subject) > 16384) {
            gtk_label_set_text(GTK_LABEL(c->notice), "Paste exactly one public-key line. Private keys are not accepted.");
            g_free(subject); return;
        }
    } else {
        subject = g_strdup(gtk_editable_get_text(GTK_EDITABLE(field))); g_strstrip(subject);
        if (!g_regex_match_simple("^SHA256:[A-Za-z0-9+/]{43}$", subject, 0, 0)) {
            gtk_label_set_text(GTK_LABEL(c->notice), "Use a SHA256 fingerprint from the shared key inventory.");
            g_free(subject); return;
        }
    }
    run_bridge(c, action, subject, NULL, NULL, NULL, NULL);
    gtk_window_destroy(GTK_WINDOW(window)); g_free(subject);
}
static void ssh_key_dialog(Center *c, gboolean enroll) {
    GtkWidget *window = gtk_window_new();
    gtk_window_set_title(GTK_WINDOW(window), enroll ? "Enroll SSH public key" : "Revoke SSH public key");
    gtk_window_set_transient_for(GTK_WINDOW(window), GTK_WINDOW(c->window));
    gtk_window_set_modal(GTK_WINDOW(window), TRUE); gtk_window_set_default_size(GTK_WINDOW(window), 520, enroll ? 330 : 220);
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_widget_set_margin_top(box, 14); gtk_widget_set_margin_bottom(box, 14);
    gtk_widget_set_margin_start(box, 14); gtk_widget_set_margin_end(box, 14); gtk_window_set_child(GTK_WINDOW(window), box);
    GtkWidget *hint = gtk_label_new(enroll
        ? "Paste one SSH public-key line. It grants access to both Native SSH ports 8022 and 8023. Never paste a private key."
        : "Enter the SHA256 fingerprint shown in the shared SSH key inventory. Revocation affects both ports 8022 and 8023; the final valid key cannot be removed.");
    gtk_label_set_wrap(GTK_LABEL(hint), TRUE); gtk_box_append(GTK_BOX(box), hint);
    GtkWidget *field;
    if (enroll) {
        field = gtk_text_view_new(); gtk_text_view_set_wrap_mode(GTK_TEXT_VIEW(field), GTK_WRAP_NONE);
        GtkWidget *scroll = gtk_scrolled_window_new(); gtk_widget_set_vexpand(scroll, TRUE);
        gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(scroll), field); gtk_box_append(GTK_BOX(box), scroll);
    } else {
        field = gtk_entry_new(); gtk_entry_set_placeholder_text(GTK_ENTRY(field), "SHA256 fingerprint"); gtk_box_append(GTK_BOX(box), field);
    }
    GtkWidget *buttons = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    GtkWidget *cancel = gtk_button_new_with_label("Cancel");
    GtkWidget *preview = gtk_button_new_with_label(enroll ? "Preview enrollment" : "Preview revocation");
    gtk_box_append(GTK_BOX(buttons), cancel); gtk_box_append(GTK_BOX(buttons), preview); gtk_box_append(GTK_BOX(box), buttons);
    g_object_set_data(G_OBJECT(window), "ssh-key-center", c);
    g_object_set_data_full(G_OBJECT(window), "ssh-key-action", g_strdup(enroll ? "ssh-key-add-preview" : "ssh-key-remove-preview"), g_free);
    g_object_set_data(G_OBJECT(window), "ssh-key-field", field);
    g_signal_connect(cancel, "clicked", G_CALLBACK(ssh_key_dialog_cancel), window);
    g_signal_connect(preview, "clicked", G_CALLBACK(ssh_key_preview_clicked), window);
    gtk_window_present(GTK_WINDOW(window));
}
static void enroll_ssh_key(GtkButton *button, gpointer data) {
    (void)button; ssh_key_dialog(data, TRUE);
}
static void revoke_ssh_key(GtkButton *button, gpointer data) {
    (void)button; ssh_key_dialog(data, FALSE);
}
static void ssh_client_key_preview(GtkButton *button, gpointer data) {
    (void)button; GtkWidget *window = data;
    Center *c = g_object_get_data(G_OBJECT(window), "ssh-client-key-center");
    GtkWidget *field = g_object_get_data(G_OBJECT(window), "ssh-client-key-name");
    gchar *name = g_strdup(gtk_editable_get_text(GTK_EDITABLE(field))); g_strstrip(name);
    if (!g_regex_match_simple("^[a-z0-9][a-z0-9_-]{0,31}$", name, 0, 0)) {
        gtk_label_set_text(GTK_LABEL(c->notice), "Use 1–32 lowercase letters, numbers, dashes, or underscores; start with a letter or number.");
        g_free(name); return;
    }
    run_bridge(c, "ssh-client-key-preview", name, NULL, NULL, NULL, NULL);
    gtk_window_destroy(GTK_WINDOW(window)); g_free(name);
}
static void generate_ssh_key(GtkButton *button, gpointer data) {
    (void)button; Center *c = data; GtkWidget *window = gtk_window_new();
    gtk_window_set_title(GTK_WINDOW(window), "Create Native SSH recovery key");
    gtk_window_set_transient_for(GTK_WINDOW(window), GTK_WINDOW(c->window)); gtk_window_set_modal(GTK_WINDOW(window), TRUE);
    gtk_window_set_default_size(GTK_WINDOW(window), 440, 210);
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 8);
    gtk_widget_set_margin_top(box, 14); gtk_widget_set_margin_bottom(box, 14);
    gtk_widget_set_margin_start(box, 14); gtk_widget_set_margin_end(box, 14);
    gtk_window_set_child(GTK_WINDOW(window), box);
    GtkWidget *hint = gtk_label_new("Creates an unencrypted Ed25519 keypair in the private Native .ssh/ternuxx-keys directory. The private key is mode 0600. Creating it does not enroll it; enrollment is a separate action and grants access to ports 8022 and 8023.");
    gtk_label_set_wrap(GTK_LABEL(hint), TRUE); gtk_box_append(GTK_BOX(box), hint);
    GtkWidget *field = gtk_entry_new(); gtk_entry_set_placeholder_text(GTK_ENTRY(field), "Recovery key name (for example: phone-recovery)");
    gtk_editable_set_text(GTK_EDITABLE(field), "recovery8023"); gtk_box_append(GTK_BOX(box), field);
    GtkWidget *buttons = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    GtkWidget *cancel = gtk_button_new_with_label("Cancel"), *preview = gtk_button_new_with_label("Review key creation");
    gtk_box_append(GTK_BOX(buttons), cancel); gtk_box_append(GTK_BOX(buttons), preview); gtk_box_append(GTK_BOX(box), buttons);
    g_object_set_data(G_OBJECT(window), "ssh-client-key-center", c); g_object_set_data(G_OBJECT(window), "ssh-client-key-name", field);
    g_signal_connect(cancel, "clicked", G_CALLBACK(ssh_key_dialog_cancel), window);
    g_signal_connect(preview, "clicked", G_CALLBACK(ssh_client_key_preview), window);
    gtk_window_present(GTK_WINDOW(window));
}
static void ask_ssh_client_key_confirmation(Center *c, const gchar *name, const gchar *plan_id,
                                            const gchar *path, const gchar *impact) {
    gchar *message = g_strdup_printf("Create Native SSH recovery key ‘%s’?\\n\\nPrivate key: %s\\n\\n%s\\n\\nThe key will not be enrolled automatically. Keep the private key private; use the separate public-key enrollment action when ready.", name, path, impact);
    GtkAlertDialog *dialog = gtk_alert_dialog_new("%s", message);
    const char *choices[] = {"Cancel", "Create key", NULL}; gtk_alert_dialog_set_buttons(dialog, choices);
    gtk_alert_dialog_set_default_button(dialog, 0);
    Request *request = g_new0(Request, 1); request->center = c;
    request->action = g_strdup("ssh-client-key-apply"); request->resource_id = g_strdup(name); request->plan_id = g_strdup(plan_id);
    gtk_alert_dialog_choose(dialog, GTK_WINDOW(c->window), NULL, confirmed_action, request);
    gtk_label_set_text(GTK_LABEL(c->notice), "Reviewing Native SSH key creation");
    g_object_unref(dialog); g_free(message);
}
static void change_ssh_autostart(GtkButton *button, gpointer data) {
    (void)button; run_bridge(data, "ssh-autostart-status", NULL, NULL, NULL, NULL, NULL);
}
static void ask_ssh_autostart_confirmation(Center *c, const gchar *enabled,
                                           const gchar *plan_id, const gchar *effect) {
    gboolean desired = g_strcmp0(enabled, "true") == 0;
    gchar *message = g_strdup_printf("%s managed SSH automatic start?\n\n%s\n\nThis preference applies when the Runit supervisor next starts. The current SSH process will not be stopped or started.", desired ? "Enable" : "Disable", effect);
    GtkAlertDialog *dialog = gtk_alert_dialog_new("%s", message);
    const char *choices[] = {"Cancel", desired ? "Enable at startup" : "Disable at startup", NULL};
    gtk_alert_dialog_set_buttons(dialog, choices); gtk_alert_dialog_set_default_button(dialog, 0);
    Request *request = g_new0(Request, 1); request->center = c;
    request->action = g_strdup("ssh-autostart-apply"); request->resource_id = g_strdup(enabled);
    request->plan_id = g_strdup(plan_id);
    gtk_alert_dialog_choose(dialog, GTK_WINDOW(c->window), NULL, confirmed_action, request);
    gtk_label_set_text(GTK_LABEL(c->notice), "Reviewing SSH automatic-start preference");
    g_object_unref(dialog); g_free(message);
}
static void ask_ssh_key_confirmation(Center *c, const gchar *action, const gchar *subject,
                                     const gchar *plan_id, const gchar *fingerprint) {
    gboolean enroll = g_strcmp0(action, "ssh-key-add-preview") == 0;
    gchar *message = g_strdup_printf("Confirm %s of SSH key %s?\n\nThis changes the shared Native authorized-key file used by owner-managed SSH 8022 and Ternuxx SSH 8023. The exact preview will be revalidated before writing.",
        enroll ? "enrollment" : "revocation", fingerprint);
    GtkAlertDialog *dialog = gtk_alert_dialog_new("%s", message);
    const char *choices[] = {"Cancel", enroll ? "Enroll key" : "Revoke key", NULL};
    gtk_alert_dialog_set_buttons(dialog, choices); gtk_alert_dialog_set_default_button(dialog, 0);
    Request *request = g_new0(Request, 1); request->center = c;
    request->action = g_strdup(enroll ? "ssh-key-add-apply" : "ssh-key-remove-apply");
    request->resource_id = g_strdup(subject); request->plan_id = g_strdup(plan_id);
    gtk_alert_dialog_choose(dialog, GTK_WINDOW(c->window), NULL, confirmed_action, request);
    gtk_label_set_text(GTK_LABEL(c->notice), "Reviewing shared SSH key change");
    g_object_unref(dialog); g_free(message);
}

static void ssh_rollback_choice(GObject *source, GAsyncResult *result, gpointer user_data) {
    GtkAlertDialog *dialog = GTK_ALERT_DIALOG(source); Request *request = user_data; GError *error = NULL;
    int choice = gtk_alert_dialog_choose_finish(dialog, result, &error);
    if (!error && choice > 0) {
        gchar **ids = g_strsplit(request->resource_id ? request->resource_id : "", ",", -1);
        guint index = (guint)(choice - 1);
        if (ids[index] && g_regex_match_simple("^[0-9a-f]{32}$", ids[index], 0, 0))
            run_bridge(request->center, "ssh-key-rollback-preview", ids[index], NULL, NULL, NULL, NULL);
        else gtk_label_set_text(GTK_LABEL(request->center->notice), "Selected SSH recovery record is invalid.");
        g_strfreev(ids);
    } else if (error) { gtk_label_set_text(GTK_LABEL(request->center->notice), error->message); g_clear_error(&error); }
    else gtk_label_set_text(GTK_LABEL(request->center->notice), "SSH recovery cancelled.");
    g_free(request->action); g_free(request->resource_id); g_free(request->detail_id); g_free(request->plan_id); g_free(request);
}
static void restore_ssh_key(GtkButton *button, gpointer data) {
    (void)button; run_bridge(data, "ssh-key-rollback-list", NULL, NULL, NULL, NULL, NULL);
}
static void ask_ssh_rollback_confirmation(Center *c, const gchar *rollback_id,
                                          const gchar *plan_id, const gchar *effect) {
    gchar *message = g_strdup_printf("Restore the exact previous authorized_keys file?\n\n%s\n\nThis affects owner-managed SSH 8022 and Ternuxx SSH 8023. Restore is refused if the file changed since this snapshot.", effect);
    GtkAlertDialog *dialog = gtk_alert_dialog_new("%s", message);
    const char *choices[] = {"Cancel", "Restore saved key state", NULL};
    gtk_alert_dialog_set_buttons(dialog, choices); gtk_alert_dialog_set_default_button(dialog, 0);
    Request *request = g_new0(Request, 1); request->center = c;
    request->action = g_strdup("ssh-key-rollback-apply"); request->resource_id = g_strdup(rollback_id);
    request->plan_id = g_strdup(plan_id);
    gtk_alert_dialog_choose(dialog, GTK_WINDOW(c->window), NULL, confirmed_action, request);
    gtk_label_set_text(GTK_LABEL(c->notice), "Reviewing exact SSH key recovery");
    g_object_unref(dialog); g_free(message);
}
static void show_management_log(GtkButton *button, gpointer data) {
    (void)button; run_bridge(data, "logs-read", "management-api", NULL, NULL, NULL, NULL);
}
static void show_cron_log(GtkButton *button, gpointer data) {
    (void)button; run_bridge(data, "logs-read", "cron-scheduler", NULL, NULL, NULL, NULL);
}
static void show_cron_history(GtkButton *button, gpointer data) {
    (void)button; run_bridge(data, "cron-history", NULL, NULL, NULL, NULL, NULL);
}
static void proot_app_launch_clicked(GtkButton *button, gpointer data) {
    (void)button; GtkWidget *window = data;
    Center *c = g_object_get_data(G_OBJECT(window), "proot-center");
    GtkWidget *entry = g_object_get_data(G_OBJECT(window), "proot-entry");
    const gchar *app_id = gtk_editable_get_text(GTK_EDITABLE(entry));
    const gchar *known[] = {"terminal", "files", "firefox", "blender", "pavucontrol", "system-config-printer",
        "thunar-bulk-rename", "thunar-settings", "thunar-volman-settings", "vlc", "xarchiver",
        "xfce4-appfinder", "xfce4-terminal-settings", "shortcut-manager", NULL};
    gboolean allowed = FALSE;
    for (guint i = 0; known[i]; i++) if (g_strcmp0(app_id, known[i]) == 0) allowed = TRUE;
    if (!allowed) gtk_label_set_text(GTK_LABEL(c->notice), "Choose a listed PRoot app ID.");
    else run_bridge(c, "proot-app-launch", app_id, NULL, NULL, NULL, NULL);
    gtk_window_destroy(GTK_WINDOW(window));
}
static void proot_app_cancel_clicked(GtkButton *button, gpointer data) {
    (void)button; gtk_window_destroy(GTK_WINDOW(data));
}
static void launch_proot_app(GtkButton *button, gpointer data) {
    (void)button; Center *c = data;
    GtkWidget *window = gtk_window_new();
    gtk_window_set_title(GTK_WINDOW(window), "Launch a PRoot app");
    gtk_window_set_transient_for(GTK_WINDOW(window), GTK_WINDOW(c->window));
    gtk_window_set_modal(GTK_WINDOW(window), TRUE); gtk_window_set_default_size(GTK_WINDOW(window), 500, 210);
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_widget_set_margin_top(box, 16); gtk_widget_set_margin_bottom(box, 16);
    gtk_widget_set_margin_start(box, 16); gtk_widget_set_margin_end(box, 16);
    gtk_window_set_child(GTK_WINDOW(window), box);
    gtk_box_append(GTK_BOX(box), gtk_label_new("Launches the selected Debian PRoot app in the current Native Ternuxx display. Guest app availability is not pre-verified. It uses the existing guest and does not install software or change its configuration."));
    gtk_box_append(GTK_BOX(box), gtk_label_new("IDs: terminal, files, firefox, blender, pavucontrol, system-config-printer, thunar-bulk-rename, thunar-settings, thunar-volman-settings, vlc, xarchiver, xfce4-appfinder, xfce4-terminal-settings, shortcut-manager"));
    GtkWidget *entry = gtk_entry_new(); gtk_entry_set_placeholder_text(GTK_ENTRY(entry), "App ID, for example files"); gtk_box_append(GTK_BOX(box), entry);
    GtkWidget *buttons = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    GtkWidget *cancel = gtk_button_new_with_label("Cancel"); GtkWidget *launch = gtk_button_new_with_label("Launch app");
    gtk_box_append(GTK_BOX(buttons), cancel); gtk_box_append(GTK_BOX(buttons), launch); gtk_box_append(GTK_BOX(box), buttons);
    g_object_set_data(G_OBJECT(window), "proot-center", c); g_object_set_data(G_OBJECT(window), "proot-entry", entry);
    g_signal_connect(cancel, "clicked", G_CALLBACK(proot_app_cancel_clicked), window);
    g_signal_connect(launch, "clicked", G_CALLBACK(proot_app_launch_clicked), window);
    gtk_window_present(GTK_WINDOW(window));
}
static void proot_shortcut_preview_clicked(GtkButton *button, gpointer data) {
    (void)button; GtkWidget *window = data;
    Center *c = g_object_get_data(G_OBJECT(window), "shortcut-center");
    GtkWidget *action_entry = g_object_get_data(G_OBJECT(window), "shortcut-action-entry");
    GtkWidget *app_entry = g_object_get_data(G_OBJECT(window), "shortcut-app-entry");
    const gchar *action = gtk_editable_get_text(GTK_EDITABLE(action_entry));
    const gchar *app_id = gtk_editable_get_text(GTK_EDITABLE(app_entry));
    if ((g_strcmp0(action, "add") != 0 && g_strcmp0(action, "remove") != 0) || !app_id || !*app_id) {
        gtk_label_set_text(GTK_LABEL(c->notice), "Enter add/remove and a catalog app ID.");
    } else {
        run_bridge(c, "shortcut-preview", action, app_id, NULL, NULL, NULL);
        gtk_window_destroy(GTK_WINDOW(window));
    }
}
static void manage_proot_shortcut(GtkButton *button, gpointer data) {
    (void)button; Center *c = data;
    GtkWidget *window = gtk_window_new();
    gtk_window_set_title(GTK_WINDOW(window), "Manage one PRoot app shortcut");
    gtk_window_set_transient_for(GTK_WINDOW(window), GTK_WINDOW(c->window));
    gtk_window_set_modal(GTK_WINDOW(window), TRUE); gtk_window_set_default_size(GTK_WINDOW(window), 480, 220);
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_widget_set_margin_top(box, 16); gtk_widget_set_margin_bottom(box, 16);
    gtk_widget_set_margin_start(box, 16); gtk_widget_set_margin_end(box, 16);
    gtk_window_set_child(GTK_WINDOW(window), box);
    gtk_box_append(GTK_BOX(box), gtk_label_new("This edits only the selected Ternuxx-owned launcher in the Native PRoot Apps menu. Existing conflicts are preserved."));
    GtkWidget *action = gtk_entry_new(); gtk_entry_set_placeholder_text(GTK_ENTRY(action), "Action: add or remove");
    GtkWidget *app = gtk_entry_new(); gtk_entry_set_placeholder_text(GTK_ENTRY(app), "Catalog app ID, for example files");
    gtk_box_append(GTK_BOX(box), action); gtk_box_append(GTK_BOX(box), app);
    GtkWidget *buttons = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    GtkWidget *cancel = gtk_button_new_with_label("Cancel"); GtkWidget *preview = gtk_button_new_with_label("Preview change");
    gtk_box_append(GTK_BOX(buttons), cancel); gtk_box_append(GTK_BOX(buttons), preview); gtk_box_append(GTK_BOX(box), buttons);
    g_object_set_data(G_OBJECT(window), "shortcut-center", c);
    g_object_set_data(G_OBJECT(window), "shortcut-action-entry", action);
    g_object_set_data(G_OBJECT(window), "shortcut-app-entry", app);
    g_signal_connect(cancel, "clicked", G_CALLBACK(proot_app_cancel_clicked), window);
    g_signal_connect(preview, "clicked", G_CALLBACK(proot_shortcut_preview_clicked), window);
    gtk_window_present(GTK_WINDOW(window));
}
static void timezone_save_clicked(GtkButton *button, gpointer data) {
    (void)button; GtkWidget *window = data;
    Center *c = g_object_get_data(G_OBJECT(window), "timezone-center");
    GtkWidget *entry = g_object_get_data(G_OBJECT(window), "timezone-entry");
    const gchar *zone = gtk_editable_get_text(GTK_EDITABLE(entry));
    if (zone && *zone) run_bridge(c, "timezone-set", zone, NULL, NULL, NULL, NULL);
    else gtk_label_set_text(GTK_LABEL(c->notice), "Enter an IANA timezone name.");
    gtk_window_destroy(GTK_WINDOW(window));
}
static void timezone_cancel_clicked(GtkButton *button, gpointer data) {
    (void)button; gtk_window_destroy(GTK_WINDOW(data));
}
static void set_timezone(GtkButton *button, gpointer data) {
    (void)button; Center *c = data;
    GtkWidget *window = gtk_window_new();
    gtk_window_set_title(GTK_WINDOW(window), "Set Ternuxx timezone preference");
    gtk_window_set_transient_for(GTK_WINDOW(window), GTK_WINDOW(c->window));
    gtk_window_set_modal(GTK_WINDOW(window), TRUE);
    gtk_window_set_default_size(GTK_WINDOW(window), 420, 150);
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 10);
    gtk_widget_set_margin_top(box, 16); gtk_widget_set_margin_bottom(box, 16);
    gtk_widget_set_margin_start(box, 16); gtk_widget_set_margin_end(box, 16);
    gtk_window_set_child(GTK_WINDOW(window), box);
    gtk_box_append(GTK_BOX(box), gtk_label_new("This changes Ternuxx scheduling preference only, not Android system time."));
    GtkWidget *entry = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(entry), "IANA name, for example Asia/Dhaka");
    gtk_box_append(GTK_BOX(box), entry);
    GtkWidget *buttons = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 8);
    GtkWidget *cancel = gtk_button_new_with_label("Cancel");
    GtkWidget *save = gtk_button_new_with_label("Save preference");
    gtk_box_append(GTK_BOX(buttons), cancel); gtk_box_append(GTK_BOX(buttons), save);
    gtk_box_append(GTK_BOX(box), buttons);
    g_object_set_data(G_OBJECT(window), "timezone-center", c);
    g_object_set_data(G_OBJECT(window), "timezone-entry", entry);
    g_signal_connect(cancel, "clicked", G_CALLBACK(timezone_cancel_clicked), window);
    g_signal_connect(save, "clicked", G_CALLBACK(timezone_save_clicked), window);
    gtk_window_present(GTK_WINDOW(window));
}
static void save_monitor(GtkButton *button, gpointer data) {
    (void)button; Center *c=data; gchar interval[16];
    g_snprintf(interval,sizeof interval,"%d",gtk_spin_button_get_value_as_int(GTK_SPIN_BUTTON(c->monitor_interval)));
    const gchar *unit=gtk_string_object_get_string(GTK_STRING_OBJECT(gtk_drop_down_get_selected_item(GTK_DROP_DOWN(c->monitor_unit))));
    const gchar *effective_unit=unit?unit:"seconds"; gint value=gtk_spin_button_get_value_as_int(GTK_SPIN_BUTTON(c->monitor_interval));
    gint factor=!g_strcmp0(effective_unit,"hours")?3600:(!g_strcmp0(effective_unit,"minutes")?60:1);
    if(value*factor<30||value*factor>86400) { gtk_label_set_text(GTK_LABEL(c->notice),"Use an interval between 30 seconds and 24 hours."); return; }
    run_bridge(c,"set-monitor",gtk_check_button_get_active(GTK_CHECK_BUTTON(c->monitor_enabled))?"true":"false",
        interval,effective_unit,gtk_check_button_get_active(GTK_CHECK_BUTTON(c->monitor_focus))?"true":"false",
        gtk_check_button_get_active(GTK_CHECK_BUTTON(c->monitor_launch))?"true":"false");
}
static gboolean active(GtkApplication *app, gpointer user_data) {
    (void)user_data; Center *c=g_new0(Center,1); app_center=c;
    c->categories=g_ptr_array_new_with_free_func(g_free); c->resources=g_ptr_array_new_with_free_func(resource_free);
    c->window=gtk_application_window_new(app); gtk_window_set_title(GTK_WINDOW(c->window),"Ternuxx Management Center");
    gtk_window_set_default_size(GTK_WINDOW(c->window),720,980);
    GtkCssProvider *theme=gtk_css_provider_new();
    gtk_css_provider_load_from_string(theme,"window{background:#0c1511;color:#e6f1e9;} list,row{background:#111e18;color:#e6f1e9;} list row:selected{background:#245638;} button{background:#17271f;color:#e6f1e9;border:1px solid #2b4034;border-radius:9px;padding:8px;} button:hover{border-color:#62d58a;} label.dim-label{color:#9eb2a3;} textview,textview text{background-color:#111e18;color:#e6f1e9;}");
    gtk_style_context_add_provider_for_display(gdk_display_get_default(),GTK_STYLE_PROVIDER(theme),GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(theme);
    GtkWidget *root=gtk_box_new(GTK_ORIENTATION_VERTICAL,10); gtk_widget_set_margin_top(root,8); gtk_widget_set_margin_bottom(root,8); gtk_widget_set_margin_start(root,8); gtk_widget_set_margin_end(root,8); gtk_window_set_child(GTK_WINDOW(c->window),root);
    GtkWidget *heading=gtk_label_new("TERNUXX  ·  MANAGEMENT CENTER"); gtk_widget_add_css_class(heading,"title-1"); gtk_widget_set_halign(heading,GTK_ALIGN_START); gtk_box_append(GTK_BOX(root),heading);
    GtkWidget *paned=gtk_paned_new(GTK_ORIENTATION_HORIZONTAL); gtk_widget_set_vexpand(paned,TRUE); gtk_box_append(GTK_BOX(root),paned);
    c->category_list=gtk_list_box_new(); gtk_widget_set_size_request(c->category_list,155,-1); gtk_list_box_set_selection_mode(GTK_LIST_BOX(c->category_list),GTK_SELECTION_SINGLE); gtk_paned_set_start_child(GTK_PANED(paned),c->category_list);
    GtkWidget *middle=gtk_paned_new(GTK_ORIENTATION_VERTICAL); GtkWidget *center=gtk_box_new(GTK_ORIENTATION_VERTICAL,8); gtk_widget_set_size_request(center,-1,180); c->search=gtk_search_entry_new(); gtk_search_entry_set_placeholder_text(GTK_SEARCH_ENTRY(c->search),"Search resources"); gtk_box_append(GTK_BOX(center),c->search); c->resource_list=gtk_list_box_new(); gtk_list_box_set_selection_mode(GTK_LIST_BOX(c->resource_list),GTK_SELECTION_SINGLE); GtkWidget *scroll=gtk_scrolled_window_new(); gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(scroll),c->resource_list); gtk_widget_set_vexpand(scroll,TRUE); gtk_box_append(GTK_BOX(center),scroll); gtk_paned_set_start_child(GTK_PANED(middle),center);
    GtkWidget *right=gtk_box_new(GTK_ORIENTATION_VERTICAL,8); c->details=gtk_text_view_new(); gtk_text_view_set_editable(GTK_TEXT_VIEW(c->details),FALSE); gtk_text_view_set_wrap_mode(GTK_TEXT_VIEW(c->details),GTK_WRAP_WORD_CHAR); GtkWidget *detail_scroll=gtk_scrolled_window_new(); gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(detail_scroll),c->details); gtk_widget_set_vexpand(detail_scroll,TRUE);
    GtkWidget *actions=gtk_box_new(GTK_ORIENTATION_VERTICAL,4); c->history_button=gtk_button_new_with_label("View operation history"); gtk_widget_set_visible(c->history_button,FALSE); c->desktop_log_button=gtk_button_new_with_label("Read Native desktop log (may include app output)"); gtk_widget_set_visible(c->desktop_log_button,FALSE); c->logs_button=gtk_button_new_with_label("Read Cron scheduler log"); gtk_widget_set_visible(c->logs_button,FALSE); c->audit_logs_button=gtk_button_new_with_label("Read management audit log"); gtk_widget_set_visible(c->audit_logs_button,FALSE); c->start_button=gtk_button_new_with_label("Start desktop"); c->stop_button=gtk_button_new_with_label("Stop desktop"); c->ssh_restart_button=gtk_button_new_with_label("Restart managed SSH (8023)"); gtk_widget_set_visible(c->ssh_restart_button,FALSE); c->ssh_keys_button=gtk_button_new_with_label("View shared SSH key fingerprints"); gtk_widget_set_visible(c->ssh_keys_button,FALSE); c->ssh_enroll_button=gtk_button_new_with_label("Enroll public key..."); gtk_widget_set_visible(c->ssh_enroll_button,FALSE); c->ssh_revoke_button=gtk_button_new_with_label("Revoke public key..."); gtk_widget_set_visible(c->ssh_revoke_button,FALSE); c->ssh_rollback_button=gtk_button_new_with_label("Restore previous SSH key change..."); gtk_widget_set_visible(c->ssh_rollback_button,FALSE); c->ssh_generate_button=gtk_button_new_with_label("Create Native recovery key..."); gtk_widget_set_visible(c->ssh_generate_button,FALSE); c->ssh_autostart_button=gtk_button_new_with_label("Set SSH start with Termux services..."); gtk_widget_set_visible(c->ssh_autostart_button,FALSE); c->ssh_wakelock_button=gtk_button_new_with_label("Set managed SSH keep-awake preference..."); gtk_widget_set_visible(c->ssh_wakelock_button,FALSE); c->graphics_select_button=gtk_button_new_with_label("Select graphics backend"); gtk_widget_set_visible(c->graphics_select_button,FALSE); c->graphics_api_button=gtk_button_new_with_label("Verify graphics API…"); gtk_widget_set_visible(c->graphics_api_button,FALSE); g_object_set_data(G_OBJECT(c->start_button),"start",GINT_TO_POINTER(TRUE)); g_object_set_data(G_OBJECT(c->stop_button),"start",GINT_TO_POINTER(FALSE)); gtk_widget_set_visible(c->start_button,FALSE); gtk_widget_set_visible(c->stop_button,FALSE); gtk_box_append(GTK_BOX(actions),c->start_button); gtk_box_append(GTK_BOX(actions),c->stop_button); gtk_box_append(GTK_BOX(actions),c->ssh_restart_button); gtk_box_append(GTK_BOX(actions),c->ssh_keys_button); gtk_box_append(GTK_BOX(actions),c->ssh_enroll_button); gtk_box_append(GTK_BOX(actions),c->ssh_revoke_button); gtk_box_append(GTK_BOX(actions),c->ssh_rollback_button); gtk_box_append(GTK_BOX(actions),c->ssh_generate_button); gtk_box_append(GTK_BOX(actions),c->ssh_autostart_button); gtk_box_append(GTK_BOX(actions),c->graphics_select_button); gtk_box_append(GTK_BOX(actions),c->graphics_api_button); gtk_box_append(GTK_BOX(actions),c->history_button); gtk_box_append(GTK_BOX(actions),c->desktop_log_button); gtk_box_append(GTK_BOX(actions),c->logs_button); gtk_box_append(GTK_BOX(actions),c->audit_logs_button); c->cron_button=gtk_button_new_with_label("View saved Cron jobs"); gtk_widget_set_visible(c->cron_button,FALSE); gtk_box_append(GTK_BOX(actions),c->cron_button); c->cron_history_button=gtk_button_new_with_label("View Cron execution history"); gtk_widget_set_visible(c->cron_history_button,FALSE); gtk_box_append(GTK_BOX(actions),c->cron_history_button); c->cron_manage_button=gtk_button_new_with_label("Manage Cron jobs…"); gtk_widget_set_visible(c->cron_manage_button,FALSE); gtk_box_append(GTK_BOX(actions),c->cron_manage_button); c->timezone_set_button=gtk_button_new_with_label("Set Ternuxx timezone preference…"); gtk_widget_set_visible(c->timezone_set_button,FALSE); gtk_box_append(GTK_BOX(actions),c->timezone_set_button); c->proot_app_button=gtk_button_new_with_label("Launch PRoot app…"); gtk_widget_set_visible(c->proot_app_button,FALSE); gtk_box_append(GTK_BOX(actions),c->proot_app_button); c->proot_shortcut_button=gtk_button_new_with_label("Manage PRoot shortcut…"); gtk_widget_set_visible(c->proot_shortcut_button,FALSE); gtk_box_append(GTK_BOX(actions),c->proot_shortcut_button); c->proot_list_button=gtk_button_new_with_label("List PRoot app shortcuts"); gtk_widget_set_visible(c->proot_list_button,FALSE); gtk_box_append(GTK_BOX(actions),c->proot_list_button);
    c->proot_sessions_button=gtk_button_new_with_label("List PRoot sessions"); gtk_widget_set_visible(c->proot_sessions_button,FALSE); gtk_box_append(GTK_BOX(actions),c->proot_sessions_button);
    c->proot_recovery_button=gtk_button_new_with_label("Inspect PRoot recovery..."); gtk_widget_set_visible(c->proot_recovery_button,FALSE); gtk_box_append(GTK_BOX(actions),c->proot_recovery_button);
    c->proot_probe_button=gtk_button_new_with_label("Start isolated probe..."); gtk_widget_set_visible(c->proot_probe_button,FALSE); gtk_box_append(GTK_BOX(actions),c->proot_probe_button); c->proot_terminal_button=gtk_button_new_with_label("Open Debian terminal..."); gtk_widget_set_visible(c->proot_terminal_button,FALSE); gtk_box_append(GTK_BOX(actions),c->proot_terminal_button);
    c->proot_stop_button=gtk_button_new_with_label("Stop verified session..."); gtk_widget_set_visible(c->proot_stop_button,FALSE); gtk_box_append(GTK_BOX(actions),c->proot_stop_button); c->proot_confirm_button=gtk_button_new_with_label("Confirm exact PRoot action"); gtk_widget_set_visible(c->proot_confirm_button,FALSE); gtk_box_append(GTK_BOX(actions),c->proot_confirm_button); c->proot_cancel_button=gtk_button_new_with_label("Cancel PRoot action"); gtk_widget_set_visible(c->proot_cancel_button,FALSE); gtk_box_append(GTK_BOX(actions),c->proot_cancel_button); c->action_scroll=gtk_scrolled_window_new(); gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(c->action_scroll),actions); gtk_scrolled_window_set_max_content_height(GTK_SCROLLED_WINDOW(c->action_scroll),190); gtk_scrolled_window_set_propagate_natural_height(GTK_SCROLLED_WINDOW(c->action_scroll),TRUE); gtk_widget_set_size_request(c->action_scroll,-1,1); gtk_box_append(GTK_BOX(right),c->action_scroll); gtk_box_append(GTK_BOX(right),detail_scroll);
    c->monitor_box=gtk_box_new(GTK_ORIENTATION_VERTICAL,4); c->monitor_enabled=gtk_check_button_new_with_label("Enable Activity/focus monitoring"); c->monitor_interval=gtk_spin_button_new_with_range(1,86400,1); const gchar *units[]={"seconds","minutes","hours",NULL}; c->monitor_unit=gtk_drop_down_new_from_strings(units); c->monitor_focus=gtk_check_button_new_with_label("Check Android Activity focus"); c->monitor_launch=gtk_check_button_new_with_label("Request Activity when background"); gtk_box_append(GTK_BOX(c->monitor_box),c->monitor_enabled); gtk_box_append(GTK_BOX(c->monitor_box),gtk_label_new("Polling interval")); gtk_box_append(GTK_BOX(c->monitor_box),c->monitor_interval); gtk_box_append(GTK_BOX(c->monitor_box),c->monitor_unit); gtk_box_append(GTK_BOX(c->monitor_box),c->monitor_focus); gtk_box_append(GTK_BOX(c->monitor_box),c->monitor_launch); GtkWidget *save=gtk_button_new_with_label("Save monitoring policy"); gtk_box_append(GTK_BOX(c->monitor_box),save); gtk_widget_set_visible(c->monitor_box,FALSE); gtk_box_append(GTK_BOX(right),c->monitor_box);
    gtk_paned_set_end_child(GTK_PANED(middle),right); gtk_paned_set_end_child(GTK_PANED(paned),middle); gtk_paned_set_position(GTK_PANED(paned),165); gtk_paned_set_position(GTK_PANED(middle),190);
    c->notice=gtk_label_new("Loading resource catalog…"); gtk_widget_set_halign(c->notice,GTK_ALIGN_START); gtk_box_append(GTK_BOX(root),c->notice);
    GtkWidget *brand=gtk_box_new(GTK_ORIENTATION_HORIZONTAL,4); GtkWidget *tagline=gtk_label_new("Workstation in your pocket — by Sobuj Miah");
    gtk_widget_set_halign(tagline,GTK_ALIGN_START); gtk_widget_add_css_class(tagline,"dim-label");
    GtkWidget *portfolio=gtk_link_button_new_with_label("https://soobujmiah.github.io/","soobujmiah.github.io");
    gtk_box_append(GTK_BOX(brand),tagline); gtk_box_append(GTK_BOX(brand),portfolio); gtk_box_append(GTK_BOX(root),brand);
    g_signal_connect(c->category_list,"row-selected",G_CALLBACK(category_selected),c); g_signal_connect(c->resource_list,"row-selected",G_CALLBACK(resource_selected),c); g_signal_connect(c->search,"search-changed",G_CALLBACK(search_changed),c); g_signal_connect(c->start_button,"clicked",G_CALLBACK(confirm_action),c); g_signal_connect(c->stop_button,"clicked",G_CALLBACK(confirm_action),c); g_signal_connect(c->ssh_restart_button,"clicked",G_CALLBACK(confirm_action),c); g_signal_connect(c->ssh_keys_button,"clicked",G_CALLBACK(show_ssh_keys),c); g_signal_connect(c->ssh_enroll_button,"clicked",G_CALLBACK(enroll_ssh_key),c); g_signal_connect(c->ssh_revoke_button,"clicked",G_CALLBACK(revoke_ssh_key),c); g_signal_connect(c->ssh_rollback_button,"clicked",G_CALLBACK(restore_ssh_key),c); g_signal_connect(c->ssh_generate_button,"clicked",G_CALLBACK(generate_ssh_key),c); g_signal_connect(c->ssh_autostart_button,"clicked",G_CALLBACK(change_ssh_autostart),c); g_signal_connect(c->ssh_wakelock_button,"clicked",G_CALLBACK(change_ssh_wakelock),c); g_signal_connect(c->graphics_select_button,"clicked",G_CALLBACK(select_graphics),c); g_signal_connect(c->graphics_api_button,"clicked",G_CALLBACK(choose_graphics_api),c); g_signal_connect(c->history_button,"clicked",G_CALLBACK(show_history),c); g_signal_connect(c->desktop_log_button,"clicked",G_CALLBACK(show_desktop_log),c); g_signal_connect(c->logs_button,"clicked",G_CALLBACK(show_cron_log),c); g_signal_connect(c->audit_logs_button,"clicked",G_CALLBACK(show_management_log),c); g_signal_connect(c->cron_button,"clicked",G_CALLBACK(show_cron_jobs),c); g_signal_connect(c->cron_history_button,"clicked",G_CALLBACK(show_cron_history),c); g_signal_connect(c->cron_manage_button,"clicked",G_CALLBACK(show_cron_form),c); g_signal_connect(c->timezone_set_button,"clicked",G_CALLBACK(set_timezone),c); g_signal_connect(c->proot_app_button,"clicked",G_CALLBACK(launch_proot_app),c); g_signal_connect(c->proot_shortcut_button,"clicked",G_CALLBACK(manage_proot_shortcut),c); g_signal_connect(c->proot_list_button,"clicked",G_CALLBACK(show_proot_shortcuts),c); g_signal_connect(c->proot_sessions_button,"clicked",G_CALLBACK(show_proot_sessions),c); g_signal_connect(c->proot_probe_button,"clicked",G_CALLBACK(start_proot_probe),c); g_signal_connect(c->proot_terminal_button,"clicked",G_CALLBACK(open_interactive_terminal),c); g_signal_connect(c->proot_recovery_button,"clicked",G_CALLBACK(proot_recovery_clicked),c); g_signal_connect(c->proot_stop_button,"clicked",G_CALLBACK(stop_proot_session),c); g_signal_connect(c->proot_confirm_button,"clicked",G_CALLBACK(proot_confirm_clicked),c); g_signal_connect(c->proot_cancel_button,"clicked",G_CALLBACK(proot_cancel_clicked),c); g_signal_connect(save,"clicked",G_CALLBACK(save_monitor),c);
    load_catalog(c); gtk_window_present(GTK_WINDOW(c->window)); return TRUE;
}
int main(int argc, char **argv) {
    if (argc == 2 && g_strcmp0(argv[1], "--version") == 0) { g_print("Ternuxx Management Center 0.1\n"); return 0; }
    if (argc == 2 && g_strcmp0(argv[1], "--self-check") == 0) {
        g_print("GTK %u.%u.%u; VTE %u.%u.%u; Native GTK terminal client build is available\n",
                gtk_get_major_version(), gtk_get_minor_version(), gtk_get_micro_version(),
                vte_get_major_version(), vte_get_minor_version(), vte_get_micro_version()); return 0;
    }
    GtkApplication *app=gtk_application_new("dev.ternuxx.management-center",G_APPLICATION_DEFAULT_FLAGS);
    g_signal_connect(app,"activate",G_CALLBACK(active),NULL); int status=g_application_run(G_APPLICATION(app),argc,argv); g_object_unref(app); return status;
}
