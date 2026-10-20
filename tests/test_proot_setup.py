from __future__ import annotations

import hashlib
import os
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import proot_setup


class ProotSetupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = self.base / "home"
        self.home.mkdir()
        self.prefix = self.base / "prefix"
        self.root = self.prefix / "var/lib/proot-distro/containers/debian/rootfs"
        (self.root / "etc").mkdir(parents=True)
        (self.root / "usr/lib").mkdir(parents=True)
        release = "\n".join(["ID=debian", "VERSION_ID=13", "VERSION_CODENAME=trixie", ""])
        (self.root / "usr/lib/os-release").write_text(release, encoding="utf-8")
        (self.root / "etc/os-release").symlink_to("../usr/lib/os-release")
        passwd = "\n".join([
            "root:x:0:0:root:/root:/bin/bash",
            "sbj:x:1000:1000:Owner:/home/sbj:/bin/bash",
            "",
        ])
        (self.root / "etc/passwd").write_text(passwd, encoding="utf-8")
        self.repo = self.base / "repo"
        manifest = self.repo / "config/proot/debian-trixie.json"
        manifest.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / "config/proot/debian-trixie.json", manifest)
        self.state = self.home / ".local/share/ternuxx"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _guest_digest(self) -> str:
        digest = hashlib.sha256()
        for path in sorted((self.root / "etc").iterdir()):
            digest.update(path.name.encode())
            if path.is_symlink():
                digest.update(os.readlink(path).encode())
            else:
                digest.update(path.read_bytes())
        return digest.hexdigest()

    def test_adoption_preview_and_apply_only_write_native_state(self) -> None:
        before = self._guest_digest()
        preview = proot_setup.preview_adoption(repo_root=str(self.repo), prefix=str(self.prefix),
                                                home=str(self.home), state_dir=str(self.state), user="sbj")
        operation = preview["operation"]
        self.assertEqual(operation["guest_mutations"], [])
        self.assertEqual(operation["package_changes"], [])
        result = proot_setup.apply_adoption(repo_root=str(self.repo), prefix=str(self.prefix),
                                            home=str(self.home), state_dir=str(self.state), user="sbj",
                                            plan_id=preview["plan_id"], confirmed=True)
        self.assertFalse(result["guest_mutations"])
        current = proot_setup.status(repo_root=str(self.repo), prefix=str(self.prefix),
                                     home=str(self.home), state_dir=str(self.state))
        self.assertEqual(current["status"], "adopted")
        record = self.state / "proot-setup/provider.json"
        self.assertEqual(stat.S_IMODE(record.stat().st_mode), 0o600)
        self.assertEqual(self._guest_digest(), before)

    def test_apply_requires_confirmation_and_unchanged_preview(self) -> None:
        preview = proot_setup.preview_adoption(repo_root=str(self.repo), prefix=str(self.prefix),
                                                home=str(self.home), state_dir=str(self.state), user="sbj")
        with self.assertRaisesRegex(proot_setup.SetupError, "explicit confirmation"):
            proot_setup.apply_adoption(repo_root=str(self.repo), prefix=str(self.prefix), home=str(self.home),
                                       state_dir=str(self.state), user="sbj", plan_id=preview["plan_id"],
                                       confirmed=False)
        manifest = self.repo / "config/proot/debian-trixie.json"
        manifest.write_text(manifest.read_text() + " ", encoding="utf-8")
        with self.assertRaisesRegex(proot_setup.SetupError, "differs from the reviewed preview"):
            proot_setup.apply_adoption(repo_root=str(self.repo), prefix=str(self.prefix), home=str(self.home),
                                       state_dir=str(self.state), user="sbj", plan_id=preview["plan_id"],
                                       confirmed=True)

    def test_wrong_release_or_user_is_rejected(self) -> None:
        release = self.root / "usr/lib/os-release"
        release.write_text("\n".join(["ID=ubuntu", "VERSION_ID=24.04", "VERSION_CODENAME=noble", ""]),
                           encoding="utf-8")
        with self.assertRaisesRegex(proot_setup.SetupError, "not the Debian Trixie profile"):
            proot_setup.preview_adoption(repo_root=str(self.repo), prefix=str(self.prefix), home=str(self.home),
                                         state_dir=str(self.state), user="sbj")
        release.write_text("\n".join(["ID=debian", "VERSION_ID=13", "VERSION_CODENAME=trixie", ""]),
                           encoding="utf-8")
        with self.assertRaisesRegex(proot_setup.SetupError, "selected guest account is missing"):
            proot_setup.preview_adoption(repo_root=str(self.repo), prefix=str(self.prefix), home=str(self.home),
                                         state_dir=str(self.state), user="missing")

    def test_rootfs_symlink_is_rejected(self) -> None:
        original = self.root
        saved = self.base / "rootfs-real"
        original.rename(saved)
        original.symlink_to(saved, target_is_directory=True)
        with self.assertRaisesRegex(proot_setup.SetupError, "regular directory tree"):
            proot_setup.preview_adoption(repo_root=str(self.repo), prefix=str(self.prefix), home=str(self.home),
                                         state_dir=str(self.state), user="sbj")


if __name__ == "__main__":
    unittest.main()
