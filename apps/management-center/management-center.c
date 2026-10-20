#include <gtk/gtk.h>
#include <string.h>

typedef struct { gchar *id, *category, *name, *status, *availability, *description, *operations; } Resource;
typedef struct { GtkWidget *window, *category_list, *resource_list, *details, *notice, *search;
                 GtkWidget *start_button, *stop_button, *graphics_select_button, *graphics_api_button, *history_button, *cron_button, *monitor_box, *monitor_enabled,
                 *monitor_interval, *monitor_unit, *monitor_focus, *monitor_launch; GPtrArray *categories,
                 *resources; gchar *selected_category, *selected_resource_id; } Center;
typedef struct { Center *center; gchar *action; gchar *resource_id; } Request;
static Center *app_center;
static void run_bridge(Center *c, const gchar *action, const gchar *arg1, const gchar *arg2,
                       const gchar *arg3, const gchar *arg4, const gchar *arg5);
static void ask_ssh_confirmation(Center *c, const gchar *preview_action, const gchar *plan_id, const gchar *impact);
static void choose_graphics_api(GtkButton *button, gpointer data);

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
        if ((g_strcmp0(request->action, "ssh-preview-start") == 0 || g_strcmp0(request->action, "ssh-preview-stop") == 0)
                && stdout_text && g_str_has_prefix(stdout_text, "P\t")) {
            gchar **f = g_strsplit(stdout_text, "\t", 4);
            if (f[1] && f[2] && f[3] && g_strcmp0(f[2], "true") == 0 && g_strcmp0(f[1], "-") != 0) {
                g_strchomp(f[3]); ask_ssh_confirmation(c, request->action, f[1], f[3]);
            } else {
                set_text(c, "Managed SSH 8023 is already in the requested state. No change was made.");
                gtk_label_set_text(GTK_LABEL(c->notice), "No service change needed");
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
        gtk_label_set_text(GTK_LABEL(c->notice), success ? "Shared management service request completed" :
            ((stderr_text && *stderr_text) ? stderr_text : "Operation failed; inspect the result details."));
        gtk_widget_set_sensitive(c->start_button, TRUE); gtk_widget_set_sensitive(c->stop_button, TRUE);
        if (success && (g_strcmp0(request->action,"start-desktop")==0 || g_strcmp0(request->action,"stop-desktop")==0))
            run_bridge(c,"inspect","native.desktop.session",NULL,NULL,NULL,NULL);
        else if (success && (g_strcmp0(request->action,"ssh-apply-start")==0 || g_strcmp0(request->action,"ssh-apply-stop")==0))
            run_bridge(c,"inspect","network.ssh.managed-8023",NULL,NULL,NULL,NULL);
        else if (success && g_strcmp0(request->action,"set-monitor")==0)
            run_bridge(c,"monitor",NULL,NULL,NULL,NULL,NULL);
    }
    g_free(stdout_text); g_free(stderr_text); g_free(request->action); g_free(request->resource_id); g_free(request);
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
    if (lifecycle) { gtk_widget_set_sensitive(c->start_button,FALSE); gtk_widget_set_sensitive(c->stop_button,FALSE); }
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
        request->action = g_strdup(action); request->resource_id = g_strdup(arg1);
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
    const gchar *gui_actions = "Inspect shared service operations; no guided mutation is available in this window.";
    if (g_strcmp0(r->id, "native.desktop.session") == 0)
        gui_actions = "Inspect status; start or stop the Native desktop with confirmation.";
    else if (g_strcmp0(r->id, "graphics.native") == 0)
        gui_actions = "Check status; verify OpenGL, GLES or Vulkan; select the Native backend for future starts.";
    else if (g_strcmp0(r->id, "graphics.debian") == 0)
        gui_actions = "Check status; verify OpenGL, GLES or Vulkan (read-only guest inspection).";
    else if (g_strcmp0(r->id, "network.ssh.managed-8023") == 0)
        gui_actions = "Inspect status; preview and confirm start or stop of managed SSH on 127.0.0.1:8023.";
    else if (g_strcmp0(r->id, "native.gui.activity-monitor") == 0)
        gui_actions = "Inspect and save the Activity/focus monitoring policy.";
    else if (g_strcmp0(r->id, "recovery.native-state") == 0)
        gui_actions = "Inspect recorded operation history.";
    else if (g_strcmp0(r->id, "automation.cron-registry") == 0)
        gui_actions = "Inspect scheduler status and list saved Cron jobs.";
    gchar *summary = g_strdup_printf("%s\n\nCapability: %s\nLive state: queried from the shared service\nAvailability: %s\n\n%s\n\nShared supported operations:\n%s\n\nActions available in this GTK app:\n%s\n\nAn operation listed by the shared catalog may require another client or a capability not granted to this app.",
        r->name, status_label(r->status), r->availability, r->description,
        r->operations && *r->operations ? r->operations : "None",
        gui_actions);
    set_text(c, summary); g_free(summary);
    g_free(c->selected_resource_id); c->selected_resource_id = g_strdup(r->id);
    gboolean graphics = g_str_has_prefix(r->id, "graphics.");
    gboolean desktop = g_strcmp0(r->id, "native.desktop.session") == 0;
    gboolean managed_ssh = g_strcmp0(r->id, "network.ssh.managed-8023") == 0;
    gboolean monitor = g_strcmp0(r->id, "native.gui.activity-monitor") == 0;
    gboolean history = g_strcmp0(r->id, "recovery.native-state") == 0;
    gboolean cron = g_strcmp0(r->id, "automation.cron-registry") == 0;
    gtk_widget_set_visible(c->history_button, history);
    gtk_widget_set_visible(c->cron_button, cron);
    gtk_widget_set_visible(c->graphics_api_button, graphics);
    gtk_button_set_label(GTK_BUTTON(c->start_button), managed_ssh ? "Start managed SSH (8023)" : "Start desktop");
    gtk_button_set_label(GTK_BUTTON(c->stop_button), managed_ssh ? "Stop managed SSH (8023)" : "Stop desktop");
    gtk_widget_set_visible(c->start_button, desktop || managed_ssh || graphics); gtk_widget_set_visible(c->stop_button, desktop || managed_ssh || graphics);
    gtk_widget_set_visible(c->graphics_select_button, g_strcmp0(r->id, "graphics.native") == 0);
    if (graphics) { gtk_button_set_label(GTK_BUTTON(c->start_button), "Graphics status"); gtk_button_set_label(GTK_BUTTON(c->stop_button), "Verify OpenGL"); }
    else { gtk_button_set_label(GTK_BUTTON(c->start_button), managed_ssh ? "Start managed SSH (8023)" : "Start desktop"); gtk_button_set_label(GTK_BUTTON(c->stop_button), managed_ssh ? "Stop managed SSH (8023)" : "Stop desktop"); }
    gtk_widget_set_visible(c->monitor_box, monitor);
    if (desktop || graphics) run_bridge(c, "inspect", r->id, NULL, NULL, NULL, NULL);
    else if (monitor) run_bridge(c, "monitor", NULL, NULL, NULL, NULL, NULL);
    else run_bridge(c, "inspect", r->id, NULL, NULL, NULL, NULL);
}
static void resource_selected(GtkListBox *box, GtkListBoxRow *row, gpointer data) {
    (void)box; Center *c = data; if (!row) return;
    Resource *r = g_object_get_data(G_OBJECT(row), "resource"); show_resource(c, r);
}
static void fill_resource_rows(Center *c) {
    clear_rows(c->resource_list); const gchar *query=gtk_editable_get_text(GTK_EDITABLE(c->search));
    gchar *needle=g_utf8_strdown(query?query:"",-1);
    for (guint i = 0; i < c->resources->len; i++) {
        Resource *r = g_ptr_array_index(c->resources, i); if (g_strcmp0(r->category, c->selected_category)) continue;
        gchar *raw=g_strconcat(r->name," ",r->description,NULL); gchar *haystack=g_utf8_strdown(raw,-1); g_free(raw);
        gboolean match=!needle||!*needle||g_strstr_len(haystack,-1,needle)!=NULL; g_free(haystack); if(!match) continue;
        GtkWidget *line = gtk_box_new(GTK_ORIENTATION_VERTICAL, 3); GtkWidget *title = gtk_label_new(r->name);
        GtkWidget *meta = gtk_label_new(status_label(r->status)); gtk_widget_set_halign(title, GTK_ALIGN_START);
        gtk_widget_set_halign(meta, GTK_ALIGN_START); gtk_widget_add_css_class(meta, "dim-label");
        gtk_box_append(GTK_BOX(line), title); gtk_box_append(GTK_BOX(line), meta);
        GtkWidget *listrow = gtk_list_box_row_new(); gtk_list_box_row_set_child(GTK_LIST_BOX_ROW(listrow), line);
        g_object_set_data(G_OBJECT(listrow), "resource", r); gtk_list_box_append(GTK_LIST_BOX(c->resource_list), listrow);
    }
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
    GtkWidget *row = gtk_list_box_row_new(); GtkWidget *label = gtk_label_new(fields[2]);
    gtk_widget_set_halign(label, GTK_ALIGN_START); gtk_list_box_row_set_child(GTK_LIST_BOX_ROW(row), label);
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
        else
            run_bridge(request->center, request->action, "confirmed", NULL, NULL, NULL, NULL);
    }
    else if (error) { gtk_label_set_text(GTK_LABEL(request->center->notice), error->message); g_clear_error(&error); }
    else gtk_label_set_text(GTK_LABEL(request->center->notice), "Action cancelled");
    g_free(request->action); g_free(request);
}
static void ask_ssh_confirmation(Center *c, const gchar *preview_action, const gchar *plan_id, const gchar *impact) {
    gboolean start = g_strcmp0(preview_action, "ssh-preview-start") == 0;
    gchar *message = g_strdup_printf("Confirm %s of the Ternuxx-managed SSH service on 127.0.0.1:8023?\n\n%s\n\nManual development SSH on port 8022 is excluded.", start ? "start" : "stop", impact);
    GtkAlertDialog *dialog = gtk_alert_dialog_new("%s", message);
    const char *choices[] = {"Cancel", "Confirm", NULL}; gtk_alert_dialog_set_buttons(dialog, choices);
    gtk_alert_dialog_set_default_button(dialog, 0);
    Request *request = g_new0(Request, 1); request->center = c;
    request->action = g_strdup(start ? "ssh-apply-start" : "ssh-apply-stop"); request->resource_id = g_strdup(plan_id);
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
        run_bridge(c, start ? "ssh-preview-start" : "ssh-preview-stop", NULL, NULL, NULL, NULL, NULL);
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
static void show_cron_jobs(GtkButton *button, gpointer data) {
    (void)button; run_bridge(data, "cron-jobs", NULL, NULL, NULL, NULL, NULL);
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
    gtk_window_set_default_size(GTK_WINDOW(c->window),1100,680);
    GtkCssProvider *theme=gtk_css_provider_new();
    gtk_css_provider_load_from_string(theme,"window{background:#0c1511;color:#e6f1e9} list,row{background:#111e18;color:#e6f1e9} list row:selected{background:#245638} button{background:#17271f;color:#e6f1e9;border:1px solid #2b4034;border-radius:9px;padding:8px} button:hover{border-color:#62d58a} label.dim-label{color:#9eb2a3}");
    gtk_style_context_add_provider_for_display(gdk_display_get_default(),GTK_STYLE_PROVIDER(theme),GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);
    g_object_unref(theme);
    GtkWidget *root=gtk_box_new(GTK_ORIENTATION_VERTICAL,10); gtk_widget_set_margin_top(root,14); gtk_widget_set_margin_bottom(root,14); gtk_widget_set_margin_start(root,14); gtk_widget_set_margin_end(root,14); gtk_window_set_child(GTK_WINDOW(c->window),root);
    GtkWidget *heading=gtk_label_new("TERN UXX   ·   MANAGEMENT CENTER"); gtk_widget_add_css_class(heading,"title-1"); gtk_widget_set_halign(heading,GTK_ALIGN_START); gtk_box_append(GTK_BOX(root),heading);
    GtkWidget *paned=gtk_paned_new(GTK_ORIENTATION_HORIZONTAL); gtk_widget_set_vexpand(paned,TRUE); gtk_box_append(GTK_BOX(root),paned);
    c->category_list=gtk_list_box_new(); gtk_widget_set_size_request(c->category_list,210,-1); gtk_list_box_set_selection_mode(GTK_LIST_BOX(c->category_list),GTK_SELECTION_SINGLE); gtk_paned_set_start_child(GTK_PANED(paned),c->category_list);
    GtkWidget *middle=gtk_paned_new(GTK_ORIENTATION_HORIZONTAL); GtkWidget *center=gtk_box_new(GTK_ORIENTATION_VERTICAL,8); gtk_widget_set_size_request(center,260,-1); c->search=gtk_search_entry_new(); gtk_search_entry_set_placeholder_text(GTK_SEARCH_ENTRY(c->search),"Search resources"); gtk_box_append(GTK_BOX(center),c->search); c->resource_list=gtk_list_box_new(); gtk_list_box_set_selection_mode(GTK_LIST_BOX(c->resource_list),GTK_SELECTION_SINGLE); GtkWidget *scroll=gtk_scrolled_window_new(); gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(scroll),c->resource_list); gtk_widget_set_vexpand(scroll,TRUE); gtk_box_append(GTK_BOX(center),scroll); gtk_paned_set_start_child(GTK_PANED(middle),center);
    GtkWidget *right=gtk_box_new(GTK_ORIENTATION_VERTICAL,8); c->details=gtk_text_view_new(); gtk_text_view_set_editable(GTK_TEXT_VIEW(c->details),FALSE); gtk_text_view_set_wrap_mode(GTK_TEXT_VIEW(c->details),GTK_WRAP_WORD_CHAR); GtkWidget *detail_scroll=gtk_scrolled_window_new(); gtk_scrolled_window_set_child(GTK_SCROLLED_WINDOW(detail_scroll),c->details); gtk_widget_set_vexpand(detail_scroll,TRUE); gtk_box_append(GTK_BOX(right),detail_scroll);
    GtkWidget *actions=gtk_box_new(GTK_ORIENTATION_HORIZONTAL,6); c->history_button=gtk_button_new_with_label("View operation history"); gtk_widget_set_visible(c->history_button,FALSE); c->start_button=gtk_button_new_with_label("Start desktop"); c->stop_button=gtk_button_new_with_label("Stop desktop"); c->graphics_select_button=gtk_button_new_with_label("Select graphics backend"); gtk_widget_set_visible(c->graphics_select_button,FALSE); c->graphics_api_button=gtk_button_new_with_label("Verify graphics API…"); gtk_widget_set_visible(c->graphics_api_button,FALSE); g_object_set_data(G_OBJECT(c->start_button),"start",GINT_TO_POINTER(TRUE)); g_object_set_data(G_OBJECT(c->stop_button),"start",GINT_TO_POINTER(FALSE)); gtk_widget_set_visible(c->start_button,FALSE); gtk_widget_set_visible(c->stop_button,FALSE); gtk_box_append(GTK_BOX(actions),c->start_button); gtk_box_append(GTK_BOX(actions),c->stop_button); gtk_box_append(GTK_BOX(actions),c->graphics_select_button); gtk_box_append(GTK_BOX(actions),c->graphics_api_button); gtk_box_append(GTK_BOX(actions),c->history_button); c->cron_button=gtk_button_new_with_label("View saved Cron jobs"); gtk_widget_set_visible(c->cron_button,FALSE); gtk_box_append(GTK_BOX(actions),c->cron_button); gtk_box_append(GTK_BOX(right),actions);
    c->monitor_box=gtk_box_new(GTK_ORIENTATION_VERTICAL,4); c->monitor_enabled=gtk_check_button_new_with_label("Enable Activity/focus monitoring"); c->monitor_interval=gtk_spin_button_new_with_range(1,86400,1); const gchar *units[]={"seconds","minutes","hours",NULL}; c->monitor_unit=gtk_drop_down_new_from_strings(units); c->monitor_focus=gtk_check_button_new_with_label("Check Android Activity focus"); c->monitor_launch=gtk_check_button_new_with_label("Request Activity when background"); gtk_box_append(GTK_BOX(c->monitor_box),c->monitor_enabled); gtk_box_append(GTK_BOX(c->monitor_box),gtk_label_new("Polling interval")); gtk_box_append(GTK_BOX(c->monitor_box),c->monitor_interval); gtk_box_append(GTK_BOX(c->monitor_box),c->monitor_unit); gtk_box_append(GTK_BOX(c->monitor_box),c->monitor_focus); gtk_box_append(GTK_BOX(c->monitor_box),c->monitor_launch); GtkWidget *save=gtk_button_new_with_label("Save monitoring policy"); gtk_box_append(GTK_BOX(c->monitor_box),save); gtk_widget_set_visible(c->monitor_box,FALSE); gtk_box_append(GTK_BOX(right),c->monitor_box);
    gtk_paned_set_end_child(GTK_PANED(middle),right); gtk_paned_set_end_child(GTK_PANED(paned),middle);
    c->notice=gtk_label_new("Loading resource catalog…"); gtk_widget_set_halign(c->notice,GTK_ALIGN_START); gtk_box_append(GTK_BOX(root),c->notice);
    GtkWidget *brand=gtk_box_new(GTK_ORIENTATION_HORIZONTAL,4); GtkWidget *tagline=gtk_label_new("Workstation in your pocket — by Sobuj Miah");
    gtk_widget_set_halign(tagline,GTK_ALIGN_START); gtk_widget_add_css_class(tagline,"dim-label");
    GtkWidget *portfolio=gtk_link_button_new_with_label("https://soobujmiah.github.io/","soobujmiah.github.io");
    gtk_box_append(GTK_BOX(brand),tagline); gtk_box_append(GTK_BOX(brand),portfolio); gtk_box_append(GTK_BOX(root),brand);
    g_signal_connect(c->category_list,"row-selected",G_CALLBACK(category_selected),c); g_signal_connect(c->resource_list,"row-selected",G_CALLBACK(resource_selected),c); g_signal_connect(c->search,"search-changed",G_CALLBACK(search_changed),c); g_signal_connect(c->start_button,"clicked",G_CALLBACK(confirm_action),c); g_signal_connect(c->stop_button,"clicked",G_CALLBACK(confirm_action),c); g_signal_connect(c->graphics_select_button,"clicked",G_CALLBACK(select_graphics),c); g_signal_connect(c->graphics_api_button,"clicked",G_CALLBACK(choose_graphics_api),c); g_signal_connect(c->history_button,"clicked",G_CALLBACK(show_history),c); g_signal_connect(c->cron_button,"clicked",G_CALLBACK(show_cron_jobs),c); g_signal_connect(save,"clicked",G_CALLBACK(save_monitor),c);
    load_catalog(c); gtk_window_present(GTK_WINDOW(c->window)); return TRUE;
}
int main(int argc, char **argv) {
    if (argc == 2 && g_strcmp0(argv[1], "--version") == 0) { g_print("Ternuxx Management Center 0.1\n"); return 0; }
    if (argc == 2 && g_strcmp0(argv[1], "--self-check") == 0) {
        g_print("GTK %u.%u.%u; Native GTK client build is available\n", gtk_get_major_version(), gtk_get_minor_version(), gtk_get_micro_version()); return 0;
    }
    GtkApplication *app=gtk_application_new("dev.ternuxx.management-center",G_APPLICATION_DEFAULT_FLAGS);
    g_signal_connect(app,"activate",G_CALLBACK(active),NULL); int status=g_application_run(G_APPLICATION(app),argc,argv); g_object_unref(app); return status;
}
