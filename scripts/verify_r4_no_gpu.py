#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import h3_studio.workers as workers_mod
from h3_studio.config import StudioConfig
from h3_studio.server import StudioService
from h3_studio.workers import NoWorkerAvailable

PROMPT_TO_URL: dict[str, str] = {}
INTERRUPTS: list[str] = []


class FakeComfyClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    @property
    def websocket_url(self) -> str:
        return self.base_url.replace("http://", "ws://") + "/ws"

    def system_stats(self) -> dict[str, Any]:
        return {"system": {"os": "mock"}, "devices": [{"name": "mock-a5000", "url": self.base_url}]}

    def upload_image(self, image_path: Path, *, upload_name: str | None = None) -> dict[str, Any]:
        return {"name": upload_name or image_path.name, "subfolder": "", "type": "input"}

    def submit_prompt(self, prompt: dict[str, Any], *, client_id: str) -> dict[str, Any]:
        prompt_id = "prompt-" + client_id.rsplit("-", 1)[-1]
        PROMPT_TO_URL[prompt_id] = self.base_url
        return {"prompt_id": prompt_id, "number": len(PROMPT_TO_URL)}

    def history(self, prompt_id: str) -> dict[str, Any]:
        return {
            prompt_id: {
                "status": {"status_str": "success", "completed": True},
                "outputs": {"10": {"gifs": [{"filename": f"{prompt_id}.mp4", "subfolder": "h3_studio", "type": "output"}]}},
            }
        }

    def interrupt(self) -> dict[str, Any]:
        INTERRUPTS.append(self.base_url)
        return {"ok": True, "worker": self.base_url}

    def view_url(self, item: dict[str, Any]) -> str:
        return self.base_url + "/view?filename=" + item.get("filename", "")


def pool_doc(worker_count: int = 5) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "safe_concurrent_runs": 2,
        "host_ram_abort_gib": 9999,
        "host_ram_hard_gib": 10000,
        "workers": [
            {"id": f"worker-gpu{i}", "gpu": str(i), "host": "127.0.0.1", "port": 30211 + i}
            for i in range(worker_count)
        ],
    }


def main() -> int:
    repo = Path.cwd().resolve()
    original_client = workers_mod.ComfyClient
    workers_mod.ComfyClient = FakeComfyClient  # type: ignore[assignment]
    try:
        with tempfile.TemporaryDirectory(prefix="h3-studio-r4-test-") as td:
            os.environ["H3_STUDIO_DATA"] = td
            cfg = StudioConfig.from_env(repo)
            object.__setattr__(cfg, "worker_pool", pool_doc())
            service = StudioService(cfg)
            first = service.submit({"kind": "t2va", "profile": "balanced-r2-a5000", "prompt": "mock rain and stereo wheels", "seed": "101"}, {})
            second = service.submit({"kind": "t2va", "profile": "balanced-r2-a5000", "prompt": "mock harbor bells stereo", "seed": "102"}, {})
            if first["worker"]["id"] == second["worker"]["id"]:
                raise AssertionError("two simultaneous independent Runs were not assigned to distinct Workers")
            try:
                service.submit({"kind": "t2va", "profile": "balanced-r2-a5000", "prompt": "must fail closed", "seed": "103"}, {})
            except NoWorkerAvailable:
                pass
            else:
                raise AssertionError("third Run did not fail closed at safe_concurrent_runs=2")
            done = service.refresh(first["run_id"])
            if done["status"] != "completed" or not done["artifacts"]:
                raise AssertionError("refresh did not correlate completed artifact to the assigned Worker")
            before_cancel = len(INTERRUPTS)
            completed_again = service.cancel(first["run_id"])
            if completed_again["status"] != "completed" or len(INTERRUPTS) != before_cancel:
                raise AssertionError("cancelling a terminal Run must not interrupt the assigned Worker")
            third = service.submit({"kind": "t2va", "profile": "balanced-r2-a5000", "prompt": "after release", "seed": "104"}, {})
            cancelled = service.cancel(third["run_id"])
            if cancelled["status"] != "cancelled" or len(INTERRUPTS) != before_cancel + 1:
                raise AssertionError("active Run cancellation did not call assigned Worker interrupt exactly once")
            third = service.submit({"kind": "t2va", "profile": "balanced-r2-a5000", "prompt": "after active cancel release", "seed": "105"}, {})
            status = service.workers()
            if status["worker_count"] != 5:
                raise AssertionError("five Worker Pool discovery shape missing")
            if third["worker"]["id"] not in {"worker-gpu0", "worker-gpu1", "worker-gpu2", "worker-gpu3", "worker-gpu4"}:
                raise AssertionError("third Run assigned to unknown Worker")
            record = service.store.read(third["run_id"])
            required = ["workflow_api", "model_runtime_identity", "worker", "client_id", "prompt_id"]
            missing = [key for key in required if key not in record]
            if missing:
                raise AssertionError(f"run traceability missing: {missing}")
            for bad in (
                {"id": "bad-port", "gpu": "0", "host": "127.0.0.1", "port": 70000},
                {"id": "bad-url", "gpu": "0", "url": "ftp://127.0.0.1:30211"},
                {"id": "missing-url-port", "gpu": "0", "url": "http://127.0.0.1"},
                {"id": "mismatched-url-port", "gpu": "0", "url": "http://127.0.0.1:30211", "port": 30212},
            ):
                try:
                    workers_mod.WorkerSpec.from_doc(bad)
                except ValueError:
                    pass
                else:
                    raise AssertionError(f"invalid WorkerSpec accepted: {bad}")
            original_mem = workers_mod.host_memory_status
            workers_mod.host_memory_status = lambda: {"error": "mock meminfo failure"}  # type: ignore[assignment]
            try:
                try:
                    service.pool.acquire("run-mem-fail")
                except NoWorkerAvailable as exc:
                    if exc.reason != "host RAM status unavailable":
                        raise AssertionError(f"wrong RAM fail-closed reason: {exc.reason}")
                else:
                    raise AssertionError("pool did not fail closed when host RAM status was unavailable")
            finally:
                workers_mod.host_memory_status = original_mem  # type: ignore[assignment]
            print(json.dumps({
                "ok": True,
                "checked": [
                    "five-worker discovery shape",
                    "distinct worker assignment for two active Runs",
                    "safe concurrency fail-closed",
                    "artifact correlation by assigned worker",
                    "post-completion assignment release",
                    "terminal cancel does not interrupt Worker",
                    "active cancel interrupts assigned Worker once and releases",
                    "WorkerSpec URL/port validation",
                    "host RAM status unavailable fails closed",
                    "run traceability includes worker_pool identity",
                ],
                "assignments": {"first": first["worker"], "second": second["worker"], "third": third["worker"]},
            }, indent=2))
        return 0
    finally:
        workers_mod.ComfyClient = original_client  # type: ignore[assignment]


if __name__ == "__main__":
    raise SystemExit(main())
