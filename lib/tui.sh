#!/data/data/com.termux/files/usr/bin/bash
nt_cmd_tui() {
  nt_require_termux || return 1
  nt_require_command python3 || return 1
  exec python3 "$_TN_LIB_DIR/terminal_ui.py"
}
