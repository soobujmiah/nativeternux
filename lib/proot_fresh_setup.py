"""Fresh, isolated Debian Trixie provisioning for Ternuxx."""
from __future__ import annotations

import hashlib
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import tempfile
import tarfile
import urllib.request


ALIAS = "debian"


class FreshSetupError(ValueError):
    pass


def _private_write(path: Path, data: dict) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".fresh-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def _packages(manifest: dict) -> list[str]:
    groups = manifest.get("packages")
    if not isinstance(groups, dict):
        raise FreshSetupError("Debian package groups are invalid")
    result = []
    for group in ("base", "desktop-compat", "development", "desktop-apps", "fonts"):
        values = groups.get(group)
        if not isinstance(values, list) or not values:
            raise FreshSetupError(f"Debian package group is missing: {group}")
        for package in values:
            if not isinstance(package, str) or not re.fullmatch(r"[a-z0-9][a-z0-9+.-]{0,100}", package):
                raise FreshSetupError("invalid package name in the Debian manifest")
            result.append(package)
    if len(set(result)) != len(result):
        raise FreshSetupError("duplicate package in Debian package groups")
    return result


def preview(*, repo_root: str, prefix: str, home: str, state_dir: str, user: str) -> dict:
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", user) or user == "root":
        raise FreshSetupError("provide an ordinary Debian guest username")
    repo = Path(repo_root)
    manifest_path = repo / "config/proot/debian-trixie.json"
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    if manifest.get("schema_version") != 1 or manifest.get("provider") != "proot-distro":
        raise FreshSetupError("Debian setup profile schema is unsupported")
    containers = Path(prefix) / "var/lib/proot-distro/containers"
    info = containers.lstat()
    if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or info.st_uid != os.getuid():
        raise FreshSetupError("PRoot container directory identity is unsafe")
    rootfs = containers / ALIAS / "rootfs"
    if rootfs.exists() or rootfs.is_symlink():
        raise FreshSetupError("Ternuxx fresh Debian alias already exists; refusing overwrite")
    packages = _packages(manifest)
    kgsl = _kgsl_accessible()
    if kgsl:
        for name in manifest.get("graphics", {}).get("hold_packages", []):
            if name not in packages:
                packages.append(name)
    plan = {
        "schema_version": 1, "operation": "fresh-debian-trixie", "alias": ALIAS,
        "image": manifest["fresh_install"]["base_image"], "image_pin": manifest["fresh_install"]["image_index_digest"],
        "arch_manifest_digest": manifest["fresh_install"]["arch_manifest_digest"],
        "config_digest": manifest["fresh_install"]["config_digest"],
        "layer_digest": manifest["fresh_install"]["layer_digest"],
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "rootfs_target": str(rootfs), "guest_user": user,
        "package_groups": ["base", "desktop-compat", "development", "desktop-apps", "fonts"],
        "packages": packages,
        "apt_snapshot": manifest["fresh_install"]["apt_snapshot"],
        "package_versions": "pinned by the dated Debian snapshot archive",
        "existing_debian_rootfs_changed": False,
        "graphics": {
            "kgsl_accessible_at_preview": kgsl,
            "turnip_archive_sha256": manifest["graphics"]["turnip_archive"]["sha256"],
            "turnip_install_planned": kgsl,
            "rendering_verified": False,
        },
        "free_bytes_at_preview": shutil.disk_usage(containers).free,
    }
    plan_id = hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    plan["plan_id"] = plan_id
    state_base = Path(state_dir)
    state_base.mkdir(mode=0o700, parents=True, exist_ok=True)
    if (state_base.is_symlink() or state_base.stat().st_uid != os.getuid()
            or stat.S_IMODE(state_base.stat().st_mode) & 0o077):
        raise FreshSetupError("Ternuxx state directory is unsafe")
    state = state_base / "proot-setup"
    state.mkdir(mode=0o700, exist_ok=True)
    previews = state / "previews"
    previews.mkdir(mode=0o700, exist_ok=True)
    for directory in (state, previews):
        info = directory.lstat()
        if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)
                or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077):
            raise FreshSetupError("private fresh setup preview directory is unsafe")
    _private_write(previews / f"fresh-{plan_id}.json", plan)
    return {"status": "preview", "plan_id": plan_id, "operation": plan}


def _stage_turnip(manifest: dict, artifact_dir: Path) -> tuple[Path, Path]:
    spec = manifest["graphics"]["turnip_archive"]
    artifact_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if artifact_dir.is_symlink() or artifact_dir.stat().st_uid != os.getuid() or stat.S_IMODE(artifact_dir.stat().st_mode) & 0o077:
        raise FreshSetupError("private graphics artifact cache is unsafe")
    archive_path = artifact_dir / (spec["sha256"] + ".tar.gz")
    if not archive_path.exists():
        temp = artifact_dir / (".download-" + str(os.getpid()))
        request = urllib.request.Request(spec["url"], headers={"User-Agent": "Ternuxx/1"})
        try:
            with urllib.request.urlopen(request, timeout=90) as response, temp.open("wb") as output:
                shutil.copyfileobj(response, output)
                output.flush()
                os.fsync(output.fileno())
            if hashlib.sha256(temp.read_bytes()).hexdigest() != spec["sha256"]:
                raise FreshSetupError("Turnip archive hash does not match the profile")
            os.chmod(temp, 0o600)
            os.replace(temp, archive_path)
        finally:
            try:
                temp.unlink()
            except FileNotFoundError:
                pass
    if hashlib.sha256(archive_path.read_bytes()).hexdigest() != spec["sha256"]:
        raise FreshSetupError("cached Turnip archive hash does not match the profile")
    outputs = []
    with tarfile.open(archive_path, "r:gz") as archive:
        for name, expected in ((spec["driver_member"], spec["driver_sha256"]),
                               (spec["icd_member"], spec["icd_sha256"])):
            found = [member for member in archive.getmembers() if member.name.removeprefix("./") == name]
            if len(found) != 1 or not found[0].isreg() or found[0].size > 256 * 1024 * 1024:
                raise FreshSetupError("Turnip archive member is missing or unsafe")
            stream = archive.extractfile(found[0])
            if stream is None:
                raise FreshSetupError("Turnip archive member could not be read")
            content = stream.read()
            if hashlib.sha256(content).hexdigest() != expected:
                raise FreshSetupError("Turnip archive member hash does not match the profile")
            output = artifact_dir / (expected + ".member")
            output.write_bytes(content)
            os.chmod(output, 0o600)
            outputs.append(output)
    return outputs[0], outputs[1]


def _guest_turnip_install(user: str, packages: list[str], driver: Path, icd: Path,
                          manager: str, alias: str, runner) -> None:
    for source, name in ((driver, "ternuxx-turnip-driver.so"), (icd, "ternuxx-turnip-icd.json")):
        result = runner([manager, "copy", str(source), f"{alias}:/tmp/{name}"],
                        check=False, timeout=180)
        if result.returncode:
            raise FreshSetupError("verified Turnip artifact could not be copied to the new guest")
    icd_config = json.loads(icd.read_text(encoding="utf-8"))
    if not isinstance(icd_config, dict) or not isinstance(icd_config.get("ICD"), dict):
        raise FreshSetupError("Turnip ICD metadata is invalid")
    icd_config["ICD"]["library_path"] = "/usr/local/lib/aarch64-linux-gnu/libvulkan_freedreno.so"
    icd_text = json.dumps(icd_config, sort_keys=True, separators=(",", ":"))
    script = " && ".join([
        "set -eu",
        "install -d -m 0755 /usr/local/lib/aarch64-linux-gnu /usr/local/share/vulkan/icd.d",
        "install -m 0644 /tmp/ternuxx-turnip-driver.so /usr/local/lib/aarch64-linux-gnu/libvulkan_freedreno.so",
        "printf %s " + shlex.quote(icd_text) + " > /usr/local/share/vulkan/icd.d/ternuxx_freedreno_icd.json",
        "rm -f /tmp/ternuxx-turnip-driver.so /tmp/ternuxx-turnip-icd.json",
        "apt-mark hold " + " ".join(shlex.quote(p) for p in manifest_holds(packages)),
    ])
    result = runner([manager, "login", "--isolated", "--user", "root", alias,
                     "--", "/bin/bash", "-lc", script], check=False, timeout=300)
    if result.returncode:
        raise FreshSetupError("Turnip files or Mesa package holds could not be installed")


def manifest_holds(packages: list[str]) -> list[str]:
    holds = ["libegl-mesa0", "libgbm1", "libgl1-mesa-dri", "libglx-mesa0", "mesa-vulkan-drivers"]
    return [item for item in holds if item in packages]


def _verify_base_image(prefix: str, manifest: dict) -> None:
    spec = manifest["fresh_install"]
    container = Path(prefix) / "var/lib/proot-distro/containers" / ALIAS
    path = container / "manifest.json"
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode) or info.st_uid != os.getuid() or info.st_size > 1024 * 1024:
        raise FreshSetupError("installed base image manifest is unsafe")
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
        image_manifest = saved["manifest"]
        image_config = saved["image_config"]
        config = image_manifest["config"]
        layers = image_manifest["layers"]
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise FreshSetupError("installed OCI image metadata is incomplete") from exc
    if (saved.get("image_ref") != spec["base_image"] or saved.get("arch") != "aarch64"
            or image_config.get("architecture") != "arm64"
            or image_config.get("created") != spec["image_created"]
            or config.get("digest") != spec["config_digest"]
            or config.get("size") != spec["config_size"]
            or not isinstance(layers, list) or len(layers) != 1
            or layers[0].get("digest") != spec["layer_digest"]
            or layers[0].get("size") != spec["layer_size"]):
        raise FreshSetupError("installed Debian base image does not match the pinned arm64 image content")


def _kgsl_accessible() -> bool:
    path = Path("/dev/kgsl-3d0")
    return path.is_char_device() and os.access(path, os.R_OK | os.W_OK)


def apply(*, repo_root: str, prefix: str, home: str, state_dir: str, user: str,
          plan_id: str, confirmed: bool, runner=subprocess.run) -> dict:
    if not confirmed:
        raise FreshSetupError("fresh Debian install requires explicit confirmation")
    if not re.fullmatch(r"[0-9a-f]{64}", plan_id):
        raise FreshSetupError("valid fresh setup preview ID required")
    manifest_path = Path(repo_root) / "config/proot/debian-trixie.json"
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    state_base = Path(state_dir)
    for directory in (state_base, state_base / "proot-setup", state_base / "proot-setup" / "previews"):
        info = directory.lstat()
        if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)
                or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077):
            raise FreshSetupError("private fresh setup state directory is unsafe")
    state = state_base / "proot-setup"
    previews = state / "previews"
    plan_path = previews / f"fresh-{plan_id}.json"
    info = plan_path.lstat()
    if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
        raise FreshSetupError("saved fresh setup preview is unsafe")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    identity = {key: value for key, value in plan.items() if key != "plan_id"}
    recalculated = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if (plan.get("plan_id") != plan_id or recalculated != plan_id
            or plan.get("guest_user") != user or plan.get("alias") != ALIAS
            or plan.get("manifest_sha256") != hashlib.sha256(raw).hexdigest()
            or plan.get("rootfs_target") != str(Path(prefix) / "var/lib/proot-distro/containers" / ALIAS / "rootfs")):
        raise FreshSetupError("fresh setup preview differs from the reviewed plan or current profile")
    manager = shutil.which("proot-distro")
    if not manager:
        raise FreshSetupError("proot-distro is unavailable")
    rootfs = Path(plan["rootfs_target"])
    if bool(plan["graphics"]["kgsl_accessible_at_preview"]) != _kgsl_accessible():
        raise FreshSetupError("KGSL capability changed since the fresh setup preview; create a new preview")
    journal = state / f"fresh-{plan_id}.journal.json"
    lock_path = state / f"fresh-{plan_id}.lock"
    if journal.is_symlink() or lock_path.is_symlink():
        raise FreshSetupError("fresh setup journal or lock is a symbolic link")
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        os.close(lock_fd)
        raise FreshSetupError("another fresh Debian setup operation is active") from exc
    try:
        if rootfs.is_symlink():
            raise FreshSetupError("fresh destination is a symbolic link")
        if rootfs.exists():
            try:
                prior = json.loads(journal.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise FreshSetupError("fresh destination exists without Ternuxx operation journal") from exc
            if prior.get("plan_id") != plan_id or prior.get("alias") != ALIAS or prior.get("state") != "failed":
                raise FreshSetupError("fresh destination is not a failed Ternuxx install from this exact preview")
        turnip_files = None
        if plan["graphics"]["turnip_install_planned"]:
            turnip_files = _stage_turnip(manifest, state / "artifacts")
        _private_write(journal, {"plan_id": plan_id, "alias": ALIAS, "state": "installing"})
        if not rootfs.exists():
            result = runner([manager, "install", "--name", ALIAS, "--architecture", manifest["fresh_install"]["architecture"], manifest["fresh_install"]["base_image"]],
                            check=False, timeout=1800)
            if result.returncode:
                raise FreshSetupError("proot-distro failed to create the new Debian alias")
        # Validate the exact OCI content that proot-distro installed before
        # changing APT sources, installing packages, or creating guest users.
        _verify_base_image(prefix, manifest)
        package_set = list(plan["packages"])
        if bool(turnip_files) != bool(plan["graphics"]["turnip_install_planned"]):
            raise FreshSetupError("Turnip plan and verified artifact selection do not match")
        package_args = " ".join(shlex.quote(item) for item in package_set)
        guest_user = shlex.quote(user)
        snapshot = manifest["fresh_install"]["apt_snapshot"]
        sources = (
            "Types: deb\nURIs: " + snapshot["main_archive"] + "\nSuites: trixie trixie-updates\nComponents: main\nSigned-By: /usr/share/keyrings/debian-archive-keyring.gpg\nCheck-Valid-Until: no\n\n"
            "Types: deb\nURIs: " + snapshot["security_archive"] + "\nSuites: trixie-security\nComponents: main\nSigned-By: /usr/share/keyrings/debian-archive-keyring.gpg\nCheck-Valid-Until: no\n"
        )
        configure_sources = "rm -f /etc/apt/sources.list && find /etc/apt/sources.list.d -maxdepth 1 -type f \\( -name '*.sources' -o -name '*.list' \\) -delete && printf %s " + shlex.quote(sources) + " > /etc/apt/sources.list.d/ternuxx-snapshot.sources"
        script = " && ".join([
            "set -eu", "export DEBIAN_FRONTEND=noninteractive", configure_sources,
            "apt-get -o Acquire::Check-Valid-Until=false update",
            f"apt-get install -y --no-install-recommends {package_args}",
            "printf '%s\\n' 'en_US.UTF-8 UTF-8' > /etc/locale.gen", "locale-gen",
            "getent passwd " + guest_user + " >/dev/null || useradd --create-home --shell /bin/bash " + guest_user,
            f"usermod -aG sudo {guest_user}", "update-locale LANG=en_US.UTF-8",
        ])
        result = runner([manager, "login", "--isolated", "--user", "root", ALIAS,
                         "--", "/bin/bash", "-lc", script], check=False, timeout=3600)
        if result.returncode:
            raise FreshSetupError("Debian package setup failed; new alias retained for inspection")
        release = (rootfs / "etc/os-release").read_text(encoding="utf-8")
        if "ID=debian" not in release or "VERSION_CODENAME=trixie" not in release:
            raise FreshSetupError("new guest release did not match Debian Trixie")
        if turnip_files:
            _guest_turnip_install(user, package_set, turnip_files[0], turnip_files[1], manager, ALIAS, runner)
            expected_driver = manifest["graphics"]["turnip_archive"]["driver_sha256"]
            actual_driver = hashlib.sha256((rootfs / manifest["graphics"]["managed_install_paths"]["driver"].lstrip("/")).read_bytes()).hexdigest()
            if actual_driver != expected_driver:
                raise FreshSetupError("installed Turnip driver does not match the pinned artifact")
        versions = runner([manager, "login", "--isolated", "--user", "root", ALIAS,
                           "--", "/usr/bin/dpkg-query", "-W", "-f", "$"+"{binary:Package}=$"+"{Version}\\n"],
                          capture_output=True, text=True, check=False, timeout=120)
        out = getattr(versions, "stdout", "")
        if versions.returncode != 0 or not isinstance(out, str) or not out.strip():
            raise FreshSetupError("installed package-version inventory could not be recorded")
        version_path = state / "debian-package-versions.txt"
        fd, version_tmp = tempfile.mkstemp(prefix=".versions-", dir=state)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(out)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(version_tmp, version_path)
        finally:
            try:
                os.unlink(version_tmp)
            except FileNotFoundError:
                pass
        record = {
            "schema_version": 1, "plan_id": plan_id, "alias": ALIAS, "guest_user": user,
            "manifest_sha256": plan["manifest_sha256"], "release": "Debian Trixie",
            "package_versions_sha256": hashlib.sha256(out.encode() if isinstance(out, str) else b"").hexdigest(),
            "package_versions_recorded": True, "package_versions_file": str(version_path),
            "existing_debian_rootfs_changed": False,
            "turnip_installed": bool(turnip_files), "turnip_runtime_verified": False,
            "origin": "fresh-preview-confirmed-install",
        }
        _private_write(state / "fresh-provider.json", record)
        _private_write(journal, {"plan_id": plan_id, "alias": ALIAS, "state": "complete"})
        return {"status": "installed", "record": record}
    except (OSError, subprocess.TimeoutExpired, FreshSetupError) as exc:
        _private_write(journal, {"plan_id": plan_id, "alias": ALIAS, "state": "failed", "detail": str(exc)[:240]})
        raise
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)
