#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from h3_studio.config import StudioConfig
from h3_studio.server import StudioService
from h3_studio.workflows import load_api_template, workflow_summary


class FakeComfy:
    def __init__(self):
        self.base_url = "http://127.0.0.1:9"
        self.submitted: dict[str, Any] = {}

    @property
    def websocket_url(self) -> str:
        return "ws://127.0.0.1:9/ws"

    def system_stats(self) -> dict[str, Any]:
        return {"system": {"os": "mock"}, "devices": [{"name": "mock-a5000"}]}

    def upload_image(self, image_path: Path, *, upload_name: str | None = None) -> dict[str, Any]:
        return {"name": upload_name or image_path.name, "subfolder": "", "type": "input"}

    def submit_prompt(self, prompt: dict[str, Any], *, client_id: str) -> dict[str, Any]:
        self.submitted[client_id] = prompt
        return {"prompt_id": "mock-prompt", "number": 1}

    def history(self, prompt_id: str) -> dict[str, Any]:
        return {
            prompt_id: {
                "status": {"status_str": "success", "completed": True},
                "outputs": {"10": {"gifs": [{"filename": "mock.mp4", "subfolder": "h3_studio", "type": "output"}]}},
            }
        }

    def interrupt(self) -> dict[str, Any]:
        return {"ok": True}

    def view_url(self, item: dict[str, Any]) -> str:
        return "mock://artifact"


def assert_no_banned_classes(summary: dict[str, Any]) -> None:
    banned = {"WorkflowDocument", "ExecutionPlan", "DAGExecutor", "NodeRegistry"}
    classes = " ".join(summary["class_types"])
    for word in banned:
        if word in classes:
            raise AssertionError(f"banned parallel graph class in workflow: {word}")


def main() -> int:
    repo = Path.cwd().resolve()
    with tempfile.TemporaryDirectory(prefix="h3-studio-r3-test-") as td:
        os.environ["H3_STUDIO_DATA"] = td
        cfg = StudioConfig.from_env(repo)
        for kind in ("t2va", "fl2va_first_frame"):
            tmpl = load_api_template(repo, kind)
            summary = workflow_summary(tmpl)
            if not summary["save_nodes"]:
                raise AssertionError(f"{kind} template has no SaveVideo node")
            assert_no_banned_classes(summary)
        service = StudioService(cfg)
        service.comfy = FakeComfy()  # type: ignore[assignment]
        t2 = service.submit({"kind": "t2va", "profile": "balanced-r2-a5000", "prompt": "mock prompt with sound", "seed": "42"}, {})
        t2_done = service.refresh(t2["run_id"])
        if t2_done["status"] != "completed" or not t2_done["artifacts"]:
            raise AssertionError("mock T2VA did not complete with artifact")
        img = Path(td) / "first.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\nmock")
        fl = service.submit({"kind": "fl2va_first_frame", "profile": "balanced-r2-a5000", "prompt": "continue from frame with stereo ambience", "seed": "43"}, {"first_frame": img})
        fl_done = service.refresh(fl["run_id"])
        if fl_done["status"] != "completed" or not fl_done["artifacts"]:
            raise AssertionError("mock FL2VA did not complete with artifact")
        index = cfg.run_root / fl["run_id"] / "run.json"
        record = json.loads(index.read_text(encoding="utf-8"))
        if "workflow_api" not in record or "model_runtime_identity" not in record:
            raise AssertionError("run traceability fields missing")
    print(json.dumps({"ok": True, "checked": ["configs", "workflow templates", "mock Guided Mode T2VA", "mock Guided Mode FL2VA", "run traceability"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
