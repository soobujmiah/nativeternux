"""Exercise the shell package-plan parser with synthetic APT output."""
import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PHASES = ROOT / "lib" / "phases.sh"


class PackagePlanTest(unittest.TestCase):
    def _apt_cache_fixture(self, output):
        temporary = tempfile.TemporaryDirectory(prefix="ternuxx-apt-cache-")
        path = Path(temporary.name) / "apt-cache"
        path.write_text("#!/bin/sh\ncat <<'APT_POLICY'\n" + output + "\nAPT_POLICY\n", encoding="utf-8")
        path.chmod(0o700)
        return temporary, path.parent

    def _candidate(self, output, repository):
        temporary, fixture_bin = self._apt_cache_fixture(output)
        try:
            result = subprocess.run(
                ["bash", "-c", 'source "$1"; _nt_package_candidate_from_official_repo xfce4-session "$2"',
                 "bash", str(PHASES), repository],
                env={**os.environ, "PATH": f"{fixture_bin}:{os.environ['PATH']}"},
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            return result
        finally:
            temporary.cleanup()

    def test_base_workstation_plan_includes_only_the_proot_manager_from_termux_main(self):
        temporary = tempfile.TemporaryDirectory(prefix="ternuxx-proot-manager-plan-")
        fixture_bin = Path(temporary.name)
        apt_get = fixture_bin / "apt-get"
        apt_get.write_text("#!/bin/sh\nprintf 'Inst proot-distro (5.10.0 termux-main stable/main [aarch64])\\n0 upgraded, 1 newly installed, 0 to remove and 0 not upgraded.\\n'\n", encoding="utf-8")
        apt_get.chmod(0o700)
        command = "\n".join([
            'source "$1"',
            '_nt_package_installed() { [[ "$1" != proot-distro ]]; }',
            '_nt_package_candidate_from_official_repo() { [[ "$1" = proot-distro && "$2" = termux-main ]] || return 1; printf "5.10.0\\n"; }',
            '_nt_make_install_plan',
            'printf "ROOTS %s\\n" "${_NT_BASE_PACKAGES[*]}"',
            'printf "REQUEST %s\\n" "${_NT_PLAN_VERSIONS[*]}"',
            'printf "TRANSACTION %s\\n" "${_NT_PLAN_TRANSACTION[*]}"',
        ])
        result = subprocess.run(
            ["bash", "-c", command, "bash", str(PHASES)],
            env={**os.environ, "PATH": f"{fixture_bin}:{os.environ['PATH']}"},
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        temporary.cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        roots = result.stdout.split("ROOTS ", 1)[1].splitlines()[0].split()
        self.assertIn("proot-distro", roots)
        self.assertIn("REQUEST proot-distro=5.10.0", result.stdout)
        self.assertIn("TRANSACTION proot-distro=5.10.0", result.stdout)
        self.assertNotIn("virglrenderer-android", roots)
        self.assertNotIn("mesa-vulkan-icd-freedreno", roots)

    def test_candidate_repository_is_checked_from_policy_origin_lines(self):
        policy = """xfce4-session:
  Installed: (none)
  Candidate: 4.20.4-1
  Version table:
     4.20.4-1 500
        500 https://grimler.se/termux/termux-x11 x11/main aarch64 Packages"""
        accepted = self._candidate(policy, "termux-x11")
        rejected = self._candidate(policy, "termux-main")
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertEqual(accepted.stdout.strip(), "4.20.4-1")
        self.assertNotEqual(rejected.returncode, 0)

    def test_candidate_policy_with_installed_marker_is_parsed(self):
        policy = """xfce4-session:
  Installed: 4.20.4-1
  Candidate: 4.20.4-1
  Version table:
 *** 4.20.4-1 100
        100 https://grimler.se/termux/termux-x11 x11/main aarch64 Packages"""
        result = self._candidate(policy, "termux-x11")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "4.20.4-1")

    def test_signed_index_age_check_uses_shell_tools_without_python(self):
        with tempfile.TemporaryDirectory(prefix="ternuxx-index-") as temporary:
            prefix = Path(temporary) / "usr"
            lists = prefix / "var/lib/apt/lists"
            lists.mkdir(parents=True)
            now = datetime.now(timezone.utc)
            fresh = (now - timedelta(days=1)).strftime("%a, %d %b %Y %H:%M:%S UTC")
            stale = (now - timedelta(days=20)).strftime("%a, %d %b %Y %H:%M:%S UTC")
            for marker in ("termux-main", "termux-x11"):
                (lists / f"mirror_{marker}_InRelease").write_text(f"Date: {fresh}\n", encoding="utf-8")
            env = {**os.environ, "PREFIX": str(prefix)}
            command = f'source "{PHASES}"; _nt_package_index_fresh'
            self.assertEqual(subprocess.run(["bash", "-c", command], env=env, check=False).returncode, 0)
            for marker in ("termux-main", "termux-x11"):
                (lists / f"mirror_{marker}_InRelease").write_text(f"Date: {stale}\n", encoding="utf-8")
            self.assertNotEqual(subprocess.run(["bash", "-c", command], env=env, check=False).returncode, 0)


    def _plan_with_simulation(self, simulation):
        temporary = tempfile.TemporaryDirectory(prefix="ternuxx-apt-plan-")
        fixture_bin = Path(temporary.name)
        apt_get = fixture_bin / "apt-get"
        apt_get.write_text(
            "#!/bin/sh\ncat <<'APT_SIMULATION'\n" + simulation.rstrip() + "\nAPT_SIMULATION\n",
            encoding="utf-8",
        )
        apt_get.chmod(0o700)
        command = "source \"$1\"\n_NT_BASE_PACKAGES=(xfce4-session)\n_nt_package_installed() { return 1; }\n_nt_package_candidate_from_official_repo() { printf '4.20.4-1'; }\nif _nt_make_install_plan; then\n  printf 'PLAN-OK\\n'\n  printf 'TRANSACTION %s\\n' \"${_NT_PLAN_TRANSACTION[*]}\"\n  printf 'SIMULATION-BEGIN\\n%s\\nSIMULATION-END\\n' \"$_NT_PLAN_SIMULATION\"\nelse\n  exit 9\nfi"
        result = subprocess.run(
            ["bash", "-c", command, "bash", str(PHASES)],
            env={**os.environ, "PATH": f"{fixture_bin}:{os.environ['PATH']}"},
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        temporary.cleanup()
        return result

    def test_install_plan_exposes_full_dependency_transaction(self):
        simulation = "\n".join([
            "NOTE: This is only a simulation!",
            "      apt needs root privileges for real execution.",
            "",
            "Reading package lists... Done",
            "The following additional packages will be installed:",
            "  dep-a dep-b",
            "The following NEW packages will be installed:",
            "  xfce4-session dep-a dep-b",
            "0 upgraded, 3 newly installed, 0 to remove and 12 not upgraded.",
            "Inst xfce4-session (4.20.4-1 termux-x11 x11/main [aarch64])",
            "Inst dep-a (1 termux-main stable/main [aarch64])",
            "Inst dep-b (2 termux-x11 x11/main [aarch64])",
            "Conf xfce4-session (4.20.4-1 termux-x11 x11/main [aarch64])",
        ])
        result = self._plan_with_simulation(simulation)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("TRANSACTION xfce4-session=4.20.4-1 dep-a=1 dep-b=2", result.stdout)
        self.assertIn("Inst dep-a (1 termux-main", result.stdout)
        self.assertIn("0 upgraded, 3 newly installed, 0 to remove", result.stdout)

    def _install_command_fixture(self, temporary):
        root = Path(temporary)
        home = root / "home"
        prefix = root / "prefix"
        fixture_bin = root / "bin"
        index_dir = prefix / "var/lib/apt/lists"
        home.mkdir()
        index_dir.mkdir(parents=True)
        fixture_bin.mkdir()
        now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S UTC")
        for marker in ("termux-main", "termux-x11"):
            (index_dir / f"mirror_{marker}_InRelease").write_text(f"Date: {now}\n", encoding="utf-8")
        (fixture_bin / "apt-cache").write_text("""#!/bin/sh
cat <<'POLICY'
xfce4-session:
  Installed: (none)
  Candidate: 4.20.4-1
  Version table:
     4.20.4-1 500
        500 https://grimler.se/termux/termux-x11 x11/main aarch64 Packages
POLICY
""", encoding="utf-8")
        (fixture_bin / "apt-get").write_text("""#!/bin/sh
if [ "$1" = "-s" ]; then
  printf 'Reading package lists... Done\nInst xfce4-session (%s termux-x11 x11/main [aarch64])\n0 upgraded, 1 newly installed, 0 to remove and 0 not upgraded.\n' "${FIXTURE_VERSION:-4.20.4-1}"
  [ -z "${SIM_SUFFIX:-}" ] || printf '%s\n' "$SIM_SUFFIX"
  exit 0
fi
printf '%s\n' "$@" >> "$APT_APPLY_CAPTURE"
""", encoding="utf-8")
        (fixture_bin / "dpkg-query").write_text("""#!/bin/sh
for package in "$@"; do :; done
if [ "$package" = "xfce4-session" ]; then echo 'deinstall ok config-files'; exit 1; fi
echo 'install ok installed'
""", encoding="utf-8")
        for tool in ("apt-cache", "apt-get", "dpkg-query"):
            (fixture_bin / tool).chmod(0o700)
        capture = root / "apt-apply-args.txt"
        env = {
            **os.environ,
            "HOME": str(home),
            "PREFIX": str(prefix),
            "TERMUX_VERSION": "fixture",
            "TERNUXX_STATE_DIR": str(home / ".local/share/ternuxx"),
            "APT_APPLY_CAPTURE": str(capture),
            "PATH": f"{fixture_bin}:{os.environ['PATH']}",
        }
        return env, capture

    def test_preview_id_applies_only_exact_full_closure_in_fixture(self):
        with tempfile.TemporaryDirectory(prefix="ternuxx-install-flow-") as temporary:
            env, capture = self._install_command_fixture(temporary)
            preview = subprocess.run(["bash", "-c", 'source "$1"; nt_require_termux() { return 0; }; nt_cmd_install --preview', "bash", str(PHASES)], env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertEqual(preview.returncode, 0, preview.stderr)
            import re
            match = re.search(r"Preview ID: ([0-9a-f]{64})", preview.stderr)
            self.assertIsNotNone(match, preview.stderr)
            applied = subprocess.run(["bash", "-c", 'source "$1"; nt_require_termux() { return 0; }; nt_cmd_install --yes --plan-id "$2"', "bash", str(PHASES), match.group(1)], env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertIn("install", capture.read_text(encoding="utf-8"))
            self.assertIn("xfce4-session=4.20.4-1", capture.read_text(encoding="utf-8"))
            records = list((Path(temporary) / "home/.local/share/ternuxx/install-transactions").glob("*.json"))
            self.assertEqual({json.loads(item.read_text())["outcome"] for item in records}, {"preview", "applied"})

    def test_changed_simulation_is_refused_before_apt_apply(self):
        with tempfile.TemporaryDirectory(prefix="ternuxx-install-mismatch-") as temporary:
            env, capture = self._install_command_fixture(temporary)
            preview = subprocess.run(["bash", "-c", 'source "$1"; nt_require_termux() { return 0; }; nt_cmd_install --preview', "bash", str(PHASES)], env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertEqual(preview.returncode, 0, preview.stderr)
            import re
            match = re.search(r"Preview ID: ([0-9a-f]{64})", preview.stderr)
            self.assertIsNotNone(match, preview.stderr)
            changed_env = {**env, "SIM_SUFFIX": "Changed repository metadata"}
            applied = subprocess.run(["bash", "-c", 'source "$1"; nt_require_termux() { return 0; }; nt_cmd_install --yes --plan-id "$2"', "bash", str(PHASES), match.group(1)], env=changed_env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertNotEqual(applied.returncode, 0)
            self.assertFalse(capture.exists(), "APT apply path must not run for a changed preview")

    def test_apply_uses_exact_version_pinned_full_transaction(self):
        with tempfile.TemporaryDirectory(prefix="ternuxx-apt-apply-") as temporary:
            fixture_bin = Path(temporary)
            apt_get = fixture_bin / "apt-get"
            apt_get.write_text("#!/bin/sh\nprintf '%s\\n' \"$@\"\n", encoding="utf-8")
            apt_get.chmod(0o700)
            command = 'source "$1"; _NT_PLAN_TRANSACTION=(xfce4-session=4.20.4-1 dep-a=2); _nt_apply_install_transaction'
            result = subprocess.run(["bash", "-c", command, "bash", str(PHASES)], env={**os.environ, "PATH": f"{fixture_bin}:{os.environ['PATH']}"}, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("xfce4-session=4.20.4-1", result.stdout)
            self.assertIn("dep-a=2", result.stdout)
            self.assertIn("--no-upgrade", result.stdout)

    def test_install_plan_fails_closed_without_inst_records(self):
        simulation = "Reading package lists... Done\n0 upgraded, 0 newly installed, 0 to remove."
        result = self._plan_with_simulation(simulation)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("APT did not return a complete install transaction", result.stderr)

    def test_apply_without_saved_preview_id_is_rejected_before_package_probes(self):
        command = "source \"$1\"; nt_fail() { :; }; TERNUXX_QUIET=1; TERNUXX_JSON=0; TERMUX_VERSION=test; PREFIX=/data/data/com.termux/files/usr; nt_cmd_install --yes"
        result = subprocess.run(["bash", "-c", command, "bash", str(PHASES)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(result.returncode, 2)

    def test_install_record_path_rejects_outside_home_and_symlink(self):
        with tempfile.TemporaryDirectory(prefix="ternuxx-install-path-") as temporary, tempfile.TemporaryDirectory(prefix="ternuxx-outside-") as outside:
            home = Path(temporary)
            state = home / "state"
            command = 'source "$1"; _nt_install_state_dir_safe'
            result = subprocess.run(["bash", "-c", command, "bash", str(PHASES)], env={**os.environ, "HOME": str(home), "TERNUXX_STATE_DIR": outside}, check=False)
            self.assertNotEqual(result.returncode, 0)
            target = home / "linked"
            target.symlink_to(Path(outside), target_is_directory=True)
            result = subprocess.run(["bash", "-c", command, "bash", str(PHASES)], env={**os.environ, "HOME": str(home), "TERNUXX_STATE_DIR": str(target / "state")}, check=False)
            self.assertNotEqual(result.returncode, 0)

    def test_transaction_record_persists_exact_preview_and_permissions(self):
        with tempfile.TemporaryDirectory(prefix="ternuxx-install-record-") as temporary:
            state = Path(temporary) / "state"
            command = "\n".join([
                'source "$1"',
                'TERNUXX_STATE_DIR="$2"',
                '_NT_PLAN_SIMULATION="$SIMULATION"',
                '_NT_PLAN_VERSIONS=(xfce4-session=4.20.4-1)',
                '_NT_PLAN_TRANSACTION=(xfce4-session=4.20.4-1 dep-a=1)',
                '_nt_write_install_record preview',
                'plan_id="$(_nt_compute_plan_id)"',
                'printf "PLAN_ID %s\\n" "$plan_id"',
                '_nt_reviewed_preview_matches "$plan_id" >/dev/null || exit 8',
                '_NT_PLAN_TRANSACTION+=(changed=1)',
                'if _nt_reviewed_preview_matches "$plan_id" >/dev/null 2>&1; then exit 9; fi',
            ])
            result = subprocess.run(
                ["bash", "-c", command, "bash", str(PHASES), str(state)],
                env={**os.environ, "HOME": temporary, "SIMULATION": "Inst xfce4-session (4.20.4-1 termux-x11 x11/main [aarch64])\nInst dep-a (1 termux-main stable/main [aarch64])"},
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            records = list((state / "install-transactions").glob("*.json"))
            self.assertEqual(len(records), 1)
            payload = json.loads(records[0].read_text(encoding="utf-8"))
            self.assertEqual(payload["outcome"], "preview")
            self.assertRegex(payload["plan_id"], r"^[0-9a-f]{64}$")
            self.assertEqual(payload["requested_candidates"], ["xfce4-session=4.20.4-1"])
            self.assertEqual(payload["resolved_transaction"], ["xfce4-session=4.20.4-1", "dep-a=1"])
            self.assertIn("termux-main stable/main [aarch64]", payload["apt_simulation"])
            self.assertEqual(records[0].stat().st_mode & 0o777, 0o600)
            self.assertEqual((state / "install-transactions").stat().st_mode & 0o777, 0o700)


if __name__ == "__main__":
    unittest.main()
