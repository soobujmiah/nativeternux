#!/usr/bin/env bash
set -euo pipefail

ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
CLI="$ROOT/bin/ternuxx"
ROOT_CLI="$ROOT/ternuxx"

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
root_version="$(bash "$ROOT_CLI" --version)"
bin_version="$(bash "$CLI" --version)"

grep -Fq 'Start the Native Termux:X11/XFCE session' <<<"$main_help"
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
grep -Fq 'proot status' <<<"$main_help"
grep -Fq 'proot verify --distro debian' <<<"$proot_help"
grep -Fq 'recovery resolve OPERATION_ID' <<<"$root_help"
grep -Fq 'remote access preview' <<<"$root_help"
grep -Fq 'never' <<<"$remote_help"
grep -Fq 'public ingress' <<<"$remote_help"
grep -Fq 'Usage:' <<<"$root_help"
grep -Fq 'ternuxx <command> [options]' <<<"$root_help"
grep -Fq 'Ternuxx v' <<<"$root_version"
grep -Fq 'Ternuxx v' <<<"$bin_version"
grep -Fq 'Ternuxx v' <<<"$bin_version"

if grep -Eq 'not implemented|stub|no packages are installed' <<<"$main_help$start_help$stop_help$restart_help$install_help"; then
  echo 'Stale stub claim found in CLI help' >&2
  exit 1
fi

echo 'CLI help contract: PASS'
