"""Tests for the pinned, bounded Native CPU inference workflow."""
import hashlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
import cpu_inference  # noqa: E402


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self
    def __exit__(self, *_args):
        self.close()


class CpuInferenceTests(unittest.TestCase):
    def test_cli_setup_guidance_is_english_and_keeps_runtime_package_owner_clear(self):
        source = (ROOT / "lib" / "ai.sh").read_text()
        self.assertIn("The llama-cpp runtime is missing.", source)
        self.assertIn("Ternuxx does not install packages.", source)
        self.assertIn("Review and download the pinned Qwen3 0.6B CPU model?", source)
        self.assertNotRegex(source, "[\u0980-\u09ff]")

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ternuxx-cpu-ai-")
        self.home = Path(self.temporary.name)
        self.state = self.home / ".local" / "share" / "ternuxx"
        self.payload = b"a small test model"
        self.spec = cpu_inference.ModelSpec(
            "test-model", "test.gguf", "https://models.example/test.gguf", len(self.payload),
            hashlib.sha256(self.payload).hexdigest(), "Apache-2.0")
        self.home_patch = patch.object(cpu_inference.Path, "home", return_value=self.home)
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)
        self.addCleanup(self.temporary.cleanup)

    def test_preview_is_deterministic_read_only_and_names_exact_download(self):
        before = list(self.home.rglob("*"))
        first = cpu_inference.preview(home=self.home, state_dir=self.state, spec=self.spec)
        second = cpu_inference.preview(home=self.home, state_dir=self.state, spec=self.spec)
        self.assertEqual(first, second)
        self.assertEqual(first["target"], str(self.state / "models" / "test.gguf"))
        self.assertEqual(first["sha256"], self.spec.sha256)
        self.assertTrue(first["read_only"])
        self.assertEqual(list(self.home.rglob("*")), before)

    def test_preview_reports_insufficient_storage_without_creating_paths(self):
        usage = type("Usage", (), {"total": 100, "used": 90, "free": 10})()
        with patch.object(cpu_inference.shutil, "disk_usage", return_value=usage):
            plan = cpu_inference.preview(home=self.home, state_dir=self.state, spec=self.spec)
            with self.assertRaisesRegex(cpu_inference.InferenceError, "free storage"):
                cpu_inference.install_model(plan_id=plan["plan_id"], confirmed="DOWNLOAD",
                    home=self.home, state_dir=self.state, spec=self.spec,
                    opener=lambda *_a, **_kw: self.fail("download must not start"))
        self.assertEqual(plan["space_check"], "insufficient")
        self.assertFalse((self.state / "models" / self.spec.filename).exists())

    def test_download_requires_matching_plan_and_exact_confirmation(self):
        plan = cpu_inference.preview(home=self.home, state_dir=self.state, spec=self.spec)
        with self.assertRaises(cpu_inference.InferenceError):
            cpu_inference.install_model(plan_id=plan["plan_id"], confirmed="yes", home=self.home,
                                        state_dir=self.state, spec=self.spec)
        with self.assertRaises(cpu_inference.InferenceError):
            cpu_inference.install_model(plan_id="stale", confirmed="DOWNLOAD", home=self.home,
                                        state_dir=self.state, spec=self.spec)
        self.assertFalse((self.state / "models").exists())

    def test_download_verifies_size_and_hash_then_atomically_installs_private_file(self):
        plan = cpu_inference.preview(home=self.home, state_dir=self.state, spec=self.spec)
        def opener(_request, timeout):
            self.assertEqual(timeout, 30)
            return FakeResponse(self.payload)
        result = cpu_inference.install_model(plan_id=plan["plan_id"], confirmed="DOWNLOAD",
            home=self.home, state_dir=self.state, spec=self.spec, opener=opener)
        target = self.state / "models" / "test.gguf"
        self.assertTrue(result["installed"])
        self.assertEqual(target.read_bytes(), self.payload)
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertEqual(target.parent.stat().st_mode & 0o777, 0o700)
        self.assertTrue(cpu_inference._valid_model(target, self.spec))

    def test_bad_hash_cleans_temporary_and_never_installs_target(self):
        plan = cpu_inference.preview(home=self.home, state_dir=self.state, spec=self.spec)
        bad_spec = cpu_inference.ModelSpec(**{**self.spec.__dict__, "sha256": "0" * 64})
        plan = cpu_inference.preview(home=self.home, state_dir=self.state, spec=bad_spec)
        with self.assertRaisesRegex(cpu_inference.InferenceError, "SHA-256"):
            cpu_inference.install_model(plan_id=plan["plan_id"], confirmed="DOWNLOAD",
                home=self.home, state_dir=self.state, spec=bad_spec,
                opener=lambda *_a, **_kw: FakeResponse(self.payload))
        models = self.state / "models"
        self.assertFalse((models / "test.gguf").exists())
        self.assertEqual(list(models.glob("*.part")), [])

    def test_short_download_cleans_temporary_and_preserves_no_partial_model(self):
        plan = cpu_inference.preview(home=self.home, state_dir=self.state, spec=self.spec)
        larger = cpu_inference.ModelSpec(**{**self.spec.__dict__, "size_bytes": len(self.payload) + 1})
        plan = cpu_inference.preview(home=self.home, state_dir=self.state, spec=larger)
        with self.assertRaisesRegex(cpu_inference.InferenceError, "size"):
            cpu_inference.install_model(plan_id=plan["plan_id"], confirmed="DOWNLOAD",
                home=self.home, state_dir=self.state, spec=larger,
                opener=lambda *_a, **_kw: FakeResponse(self.payload))
        self.assertFalse((self.state / "models" / "test.gguf").exists())
        self.assertEqual(list((self.state / "models").glob("*.part")), [])

    def test_cancelled_download_removes_partial_file(self):
        import threading
        event = threading.Event()
        def opener(*_args, **_kwargs):
            event.set()
            return FakeResponse(self.payload)
        plan = cpu_inference.preview(home=self.home, state_dir=self.state, spec=self.spec)
        with self.assertRaisesRegex(cpu_inference.InferenceError, "cancelled"):
            cpu_inference.install_model(plan_id=plan["plan_id"], confirmed="DOWNLOAD",
                home=self.home, state_dir=self.state, spec=self.spec, opener=opener,
                cancel_event=event)
        self.assertFalse((self.state / "models" / "test.gguf").exists())
        self.assertEqual(list((self.state / "models").glob("*.part")), [])

    def test_crash_left_partial_is_recovered_under_model_lock(self):
        plan = cpu_inference.preview(home=self.home, state_dir=self.state, spec=self.spec)
        def opener(*_args, **_kwargs): return FakeResponse(self.payload)
        first = cpu_inference.install_model(plan_id=plan["plan_id"], confirmed="DOWNLOAD",
            home=self.home, state_dir=self.state, spec=self.spec, opener=opener)
        models = self.state / "models"
        stale = models / ".test.gguf.999999.part"
        stale.write_bytes(b"orphaned incomplete download"); stale.chmod(0o600)
        second = cpu_inference.install_model(plan_id=plan["plan_id"], confirmed="DOWNLOAD",
            home=self.home, state_dir=self.state, spec=self.spec,
            opener=lambda *_a, **_kw: self.fail("verified model must not download again"))
        self.assertEqual(first["recovered_partial_downloads"], 0)
        self.assertEqual(second["recovered_partial_downloads"], 1)
        self.assertFalse(stale.exists())

    def test_model_removal_refuses_while_another_operation_holds_lock(self):
        models = self.state / "models"; models.mkdir(parents=True, mode=0o700)
        target = models / "test.gguf"; target.write_bytes(self.payload); target.chmod(0o600)
        lock = models / ".model-operation.lock"; fd = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
        cpu_inference.fcntl.flock(fd, cpu_inference.fcntl.LOCK_EX | cpu_inference.fcntl.LOCK_NB)
        try:
            plan = cpu_inference.preview("remove", home=self.home, state_dir=self.state, spec=self.spec)
            with self.assertRaisesRegex(cpu_inference.InferenceError, "another CPU model operation"):
                cpu_inference.remove_model(plan_id=plan["plan_id"], confirmed="REMOVE",
                    home=self.home, state_dir=self.state, spec=self.spec)
            self.assertEqual(target.read_bytes(), self.payload)
        finally:
            os.close(fd)

    def test_existing_invalid_model_is_preserved(self):
        target = self.state / "models" / "test.gguf"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"user data")
        target.chmod(0o600)
        plan = cpu_inference.preview(home=self.home, state_dir=self.state, spec=self.spec)
        with self.assertRaisesRegex(cpu_inference.InferenceError, "preserved"):
            cpu_inference.install_model(plan_id=plan["plan_id"], confirmed="DOWNLOAD",
                home=self.home, state_dir=self.state, spec=self.spec,
                opener=lambda *_a, **_kw: FakeResponse(self.payload))
        self.assertEqual(target.read_bytes(), b"user data")

    def test_symlinked_model_directory_is_rejected(self):
        outside = self.home / "outside"
        outside.mkdir()
        self.state.mkdir(parents=True)
        (self.state / "models").symlink_to(outside, target_is_directory=True)
        plan = cpu_inference.preview(home=self.home, state_dir=self.state, spec=self.spec)
        with self.assertRaisesRegex(cpu_inference.InferenceError, "symlink"):
            cpu_inference.install_model(plan_id=plan["plan_id"], confirmed="DOWNLOAD",
                home=self.home, state_dir=self.state, spec=self.spec,
                opener=lambda *_a, **_kw: FakeResponse(self.payload))
        self.assertEqual(list(outside.iterdir()), [])

    def test_remove_requires_preview_confirmation_and_only_removes_fixed_model(self):
        target = self.state / "models" / "test.gguf"
        target.parent.mkdir(parents=True, mode=0o700)
        target.write_bytes(self.payload)
        target.chmod(0o600)
        plan = cpu_inference.preview("remove", home=self.home, state_dir=self.state, spec=self.spec)
        with self.assertRaises(cpu_inference.InferenceError):
            cpu_inference.remove_model(plan_id=plan["plan_id"], confirmed="yes", home=self.home,
                                       state_dir=self.state, spec=self.spec)
        result = cpu_inference.remove_model(plan_id=plan["plan_id"], confirmed="REMOVE",
            home=self.home, state_dir=self.state, spec=self.spec)
        self.assertTrue(result["removed"])
        self.assertFalse(target.exists())

    def test_runtime_environment_prioritizes_termux_libraries_and_drops_preload(self):
        with patch.dict(os.environ, {"LD_LIBRARY_PATH": "/codex/lib:/other/lib", "LD_PRELOAD": "/tmp/injected.so"}):
            env = cpu_inference._runtime_env("/termux")
        self.assertEqual(env["LD_LIBRARY_PATH"], "/termux/lib:/codex/lib:/other/lib")
        self.assertNotIn("LD_PRELOAD", env)

    def test_model_output_parser_rejects_unknown_framing_without_leaking_prompt(self):
        with self.assertRaisesRegex(cpu_inference.InferenceError, "unrecognized"):
            cpu_inference._response_text("diagnostic output only", "private prompt")
        with self.assertRaisesRegex(cpu_inference.InferenceError, "one line"):
            cpu_inference.run_inference("line one\nline two")

    def test_run_rejects_prompt_token_limit_and_unverified_model_before_launch(self):
        with patch.object(cpu_inference, "_runtime", return_value="/mock/llama-cli"), \
                patch.object(cpu_inference.subprocess, "run") as run:
            with self.assertRaisesRegex(cpu_inference.InferenceError, "prompt"):
                cpu_inference.run_inference(" ", home=self.home, state_dir=self.state)
            with self.assertRaisesRegex(cpu_inference.InferenceError, "model"):
                cpu_inference.run_inference("hello", home=self.home, state_dir=self.state)
            run.assert_not_called()

    def test_cpu_timeout_terminates_only_the_inference_process_group(self):
        class SlowProcess:
            pid = 4242
            returncode = -15
            def __init__(self): self.calls = 0
            def poll(self): return None
            def communicate(self, timeout=None):
                self.calls += 1
                if self.calls <= 2:
                    raise cpu_inference.subprocess.TimeoutExpired("llama-cli", timeout)
                return "", ""
        process = SlowProcess()
        with patch.object(cpu_inference.subprocess, "Popen", return_value=process), \
                patch.object(cpu_inference.os, "killpg") as kill_group:
            with self.assertRaisesRegex(cpu_inference.InferenceError, "timed out"):
                cpu_inference._execute_cpu(["llama-cli"], timeout=1, prefix="/termux")
        self.assertEqual([call.args[1] for call in kill_group.call_args_list],
                         [cpu_inference.signal.SIGTERM, cpu_inference.signal.SIGKILL])

    def test_run_is_cpu_only_bounded_and_reports_backend(self):
        target = self.state / "models" / cpu_inference.MODEL.filename
        target.parent.mkdir(parents=True, mode=0o700)
        target.write_bytes(b"x" * cpu_inference.MODEL.size_bytes)
        target.chmod(0o600)
        process = type("Process", (), {"returncode": 0, "pid": 123,
            "communicate": lambda self, timeout: ("banner\n> Say CPU_OK\nCPU_OK\n[ Prompt: 1 t/s ]\nExiting...", ""),
            "poll": lambda self: 0})()
        with patch.object(cpu_inference, "_valid_model", return_value=True), \
                patch.object(cpu_inference, "_runtime", return_value="/mock/llama-cli"), \
                patch.object(cpu_inference.subprocess, "Popen", return_value=process) as popen:
            result = cpu_inference.run_inference("Say CPU_OK", home=self.home, state_dir=self.state,
                                                 prefix="/termux")
        self.assertEqual(result["backend"], "CPU")
        self.assertEqual(result["gpu_layers"], 0)
        self.assertEqual(result["output"], "CPU_OK")
        argv = popen.call_args.args[0]
        self.assertIn("-ngl", argv)
        self.assertEqual(argv[argv.index("-ngl") + 1], "0")
        self.assertIn("--simple-io", argv)
        self.assertTrue(popen.call_args.kwargs["start_new_session"])
        self.assertEqual(popen.call_args.kwargs["env"]["LD_LIBRARY_PATH"].split(":")[0], "/termux/lib")


if __name__ == "__main__":
    unittest.main()
