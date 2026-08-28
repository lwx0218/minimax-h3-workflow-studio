#!/usr/bin/env python3
"""Regression tests for R1 verifier and resource-monitor fail-closed behavior."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from run_r1_h3_attempt import (
    ResourceMonitor,
    parse_official_request,
    prepare_attempt_root,
    stop_monitor_for_success,
    stop_process,
    unexpected_sensitive_environment,
)
from verify_r1 import contains_argv_sequence

ROOT = Path(__file__).resolve().parent.parent


class ArgvVerificationTests(unittest.TestCase):
    def test_exact_option_value_matches(self) -> None:
        argv = ["sglang", "serve", "--num-gpus", "2", "--tp-size=2"]
        self.assertTrue(contains_argv_sequence(argv, ["--num-gpus", "2"]))
        self.assertFalse(contains_argv_sequence(argv, ["--num-gpus", "20"]))
        self.assertFalse(contains_argv_sequence(argv, ["--tp-size", "2"]))


class CanonicalRequestTests(unittest.TestCase):
    def test_external_source_cannot_add_request_controls(self) -> None:
        tmp_root = ROOT / "var/tmp/r1-feasibility/tests"
        tmp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tmp_root) as directory:
            source = Path(directory) / "request.sh"
            source.write_text(
                "cat <<'JSON'\n"
                '{"prompt":"fixed prompt","enable_cache_dit":true,"num_inference_steps":1}\n'
                "JSON\n",
                encoding="utf-8",
            )
            request, _ = parse_official_request(source, "model")
            self.assertNotIn("enable_cache_dit", request)
            self.assertEqual(request["num_inference_steps"], 50)
            self.assertEqual(request["conditions"], [])
            self.assertEqual(request["flow_shift"], 12.0)
            self.assertEqual(request["audio_flow_shift"], 3.0)


class EnvironmentContractTests(unittest.TestCase):
    def test_unlisted_sensitive_environment_is_rejected(self) -> None:
        environment = {
            "NCCL_NET": "Socket",
            "SGLANG_CACHE_DIT_ENABLED": "true",
            "UNRELATED_CACHE": "allowed",
        }
        self.assertEqual(
            unexpected_sensitive_environment(environment, {"NCCL_NET": "Socket"}),
            ["SGLANG_CACHE_DIT_ENABLED"],
        )

    def test_listed_sensitive_environment_is_allowed(self) -> None:
        environment = {"NCCL_NET": "Socket", "NCCL_P2P_DISABLE": "1"}
        self.assertEqual(unexpected_sensitive_environment(environment, environment), [])


class ResourceMonitorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_root = ROOT / "var/tmp/r1-feasibility/tests"
        self.tmp_root.mkdir(parents=True, exist_ok=True)

    def test_sampling_exception_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.tmp_root) as directory:
            trace = Path(directory) / "resources.csv"
            monitor = ResourceMonitor(
                trace,
                pgid=999_999_999,
                visible_gpus=[0],
                stop_event=threading.Event(),
                abort_bytes=230 * 1024**3,
            )
            with (
                patch("run_r1_h3_attempt.meminfo", return_value=(251, 200, 51)),
                patch("run_r1_h3_attempt.process_group_rss", return_value=1),
                patch("run_r1_h3_attempt.gpu_sample", side_effect=RuntimeError("synthetic sampler failure")),
            ):
                monitor.start()
                monitor.join(timeout=5)
            self.assertFalse(monitor.is_alive())
            self.assertTrue(monitor.monitor_failed.is_set())
            self.assertIn("synthetic sampler failure", monitor.monitor_error or "")
            self.assertIn("monitor_error", trace.read_text(encoding="utf-8"))

    def test_trace_setup_failure_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.tmp_root) as directory:
            missing_parent = Path(directory) / "missing-parent" / "resources.csv"
            monitor = ResourceMonitor(
                missing_parent,
                pgid=999_999_999,
                visible_gpus=[0],
                stop_event=threading.Event(),
                abort_bytes=230 * 1024**3,
            )
            monitor.start()
            monitor.join(timeout=5)
            self.assertFalse(monitor.is_alive())
            self.assertTrue(monitor.monitor_failed.is_set())
            self.assertFalse(monitor.ready.is_set())

    def test_late_failure_cannot_pass_success_gate(self) -> None:
        with tempfile.TemporaryDirectory(dir=self.tmp_root) as directory:
            stop_event = threading.Event()
            monitor = ResourceMonitor(
                Path(directory) / "resources.csv",
                pgid=999_999_999,
                visible_gpus=[0],
                stop_event=stop_event,
                abort_bytes=230 * 1024**3,
            )
            good_sample = {0: (1, 30, 10.0, "P8")}
            with (
                patch("run_r1_h3_attempt.meminfo", return_value=(251, 200, 51)),
                patch("run_r1_h3_attempt.process_group_rss", return_value=1),
                patch("run_r1_h3_attempt.gpu_sample", side_effect=[good_sample, RuntimeError("late failure")]),
            ):
                monitor.start()
                self.assertTrue(monitor.ready.wait(timeout=2))
                self.assertTrue(monitor.monitor_failed.wait(timeout=3))
                with self.assertRaisesRegex(RuntimeError, "late failure"):
                    stop_monitor_for_success(monitor, stop_event)


class ProcessCleanupTests(unittest.TestCase):
    def test_stop_process_terminates_other_process_groups_in_session(self) -> None:
        code = (
            "import subprocess,time; "
            "child=subprocess.Popen(['sleep','60'], process_group=0); "
            "print(child.pid, flush=True); time.sleep(60)"
        )
        parent = subprocess.Popen(
            [sys.executable, "-c", code],
            stdout=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        assert parent.stdout is not None
        child_pid = int(parent.stdout.readline().strip())
        stop_process(parent, grace_seconds=2)
        parent.stdout.close()
        self.assertIsNotNone(parent.returncode)
        self.assertFalse(Path(f"/proc/{child_pid}").exists())


class AttemptEvidenceTests(unittest.TestCase):
    def test_existing_attempt_directory_is_rejected(self) -> None:
        tmp_root = ROOT / "var/tmp/r1-feasibility/tests"
        tmp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tmp_root) as directory:
            output_root = Path(directory).resolve()
            (output_root / "C2").mkdir()
            with self.assertRaisesRegex(FileExistsError, "cannot be overwritten"):
                prepare_attempt_root(output_root, "C2")


if __name__ == "__main__":
    unittest.main()
