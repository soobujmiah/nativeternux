#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
CLI="$ROOT/bin/tx"
ROOT_CLI="$ROOT/tx"

main_help="$(bash "$CLI" --help)"
start_help="$(bash "$CLI" start --help)"
stop_help="$(bash "$CLI" stop --help)"
restart_help="$(bash "$CLI" restart --help)"
status_help="$(bash "$CLI" status --help)"
install_help="$(bash "$CLI" install --help)"
remote_help="$(bash "$CLI" --help remote)"
proot_help="$(bash "$CLI" --help proot)"
ssh_help="$(bash "$CLI" --help ssh)"
root_help="$(bash "$ROOT_CLI" --help)"
tui_help="$(bash "$ROOT_CLI" --help tui)"
web_help="$(bash "$ROOT_CLI" --help web)"
mng_help="$(bash "$ROOT_CLI" --help mng)"
db_help="$(bash "$ROOT_CLI" --help db)"
root_version="$(bash "$ROOT_CLI" --version)"
bin_version="$(bash "$CLI" --version)"

grep -Fq 'Desktop:       start, stop, restart, status, gui, tui, web' <<<"$main_help"
grep -Fq 'start/stop/restart change process and session state' <<<"$main_help"
grep -Fq 'This command starts processes and writes private session state/log files.' <<<"$start_help"
grep -Fq "Add --graphics to probe the" <<<"$(bash "$CLI" doctor --help)"
grep -Fq 'It sends SIGTERM' <<<"$stop_help"
grep -Fq 'Runs stop, then start.' <<<"$restart_help"
grep -Fq 'start or stop processes.' <<<"$status_help"
grep -Fq 'Each full dependency preview is saved' <<<"$install_help"
grep -Fq 'This changes the Termux environment.' <<<"$install_help"
grep -Fq 'does not automatically remove packages' <<<"$install_help"
grep -Fq 'ssh start --yes --plan-id <id>' <<<"$ssh_help"
grep -Fq 'ssh stop --yes --plan-id <id>' <<<"$ssh_help"
grep -Fq 'ssh restart --yes --plan-id <id>' <<<"$ssh_help"
grep -Fq 'proot status' <<<"$main_help"
grep -Fq 'proot verify --distro debian' <<<"$proot_help"
grep -Fq 'expected renderer class' <<<"$proot_help"
grep -Fq 'does not switch drivers' <<<"$proot_help"
grep -Fq 'tx recovery resolve OPERATION_ID' <<<"$root_help"
grep -Fq 'tx remote access preview' <<<"$root_help"
grep -Fq 'first-party command, distinct from a bare `db` shell alias' <<<"$db_help"
grep -Fq 'bypass Ternuxx' <<<"$db_help"
grep -Fq 'never' <<<"$remote_help"
grep -Fq 'public ingress' <<<"$remote_help"
grep -Fq 'Usage:' <<<"$root_help"
grep -Fq 'tx <command> [options]' <<<"$root_help"
grep -Fq 'Open the Native Termux GTK management center' <<<"$root_help"
grep -Fq 'Commands by task:' <<<"$root_help"
grep -Fq 'up=start, dn=stop, rs=restart' <<<"$root_help"
grep -Fq 'tx help NAME' <<<"$root_help"
grep -Fq 'H for operation history' <<<"$tui_help"
grep -Fq 'a to run an action' <<<"$tui_help"
! grep -Fq '1–5 to switch views' <<<"$tui_help"
grep -Fq 'graphics verification' <<<"$web_help"
grep -Fq 'timezone' <<<"$web_help"
grep -Fq 'cron executions list|show' <<<"$mng_help"
grep -Fq 'does not run jobs' <<<"$mng_help"
grep -Fq 'The inspect action does not read key or password files' <<<"$ssh_help"
grep -Fq 'tx mng logs list|read SOURCE_ID - Read bounded Ternuxx-owned log tails' <<<"$mng_help"
if grep -Fq $'\x14' <<<"$mng_help"; then
  echo 'Control character found in management help' >&2
  exit 1
fi
! grep -Eq '^[[:space:]]+gui[[:space:]]' <<<"$root_help"
grep -Fq 'Ternuxx v' <<<"$root_version"
grep -Fq 'Ternuxx v' <<<"$bin_version"
grep -Fq 'Ternuxx v' <<<"$bin_version"

if grep -Eq 'not implemented|stub|no packages are installed' <<<"$main_help$start_help$stop_help$restart_help$install_help"; then
  echo 'Stale stub claim found in CLI help' >&2
  exit 1
fi

echo 'CLI help contract: PASS'
