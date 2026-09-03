"""Minimal ComfyUI HTTP client (standard library only)."""
from __future__ import annotations

import json
import mimetypes
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

VIDEO_SUFFIXES = (".mp4", ".webm", ".mkv", ".mov")


def _json_request(url: str, payload: dict[str, Any] | None = None, timeout: float = 30.0, method: str | None = None) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {} if payload is None else {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def _multipart(fields: dict[str, str], file_field: str, file_path: Path, filename: str) -> tuple[bytes, str]:
    boundary = f"----h3studio{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for key, value in fields.items():
        chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n".encode())
    ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; filename=\"{filename}\"\r\nContent-Type: {ctype}\r\n\r\n".encode())
    chunks.append(file_path.read_bytes())
    chunks.append(f"\r\n--{boundary}--\r\n".encode())
    return b"".join(chunks), boundary


class ComfyClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def system_stats(self) -> dict[str, Any]:
        return _json_request(f"{self.base_url}/system_stats", timeout=5)

    def wait_ready(self, timeout_s: int = 120) -> dict[str, Any]:
        start = time.monotonic()
        last = None
        while time.monotonic() - start < timeout_s:
            try:
                stats = self.system_stats()
                return {"ready": True, "after_s": round(time.monotonic() - start, 3), "system_stats": stats}
            except Exception as exc:  # noqa: BLE001
                last = repr(exc)
                time.sleep(1)
        raise TimeoutError(f"ComfyUI worker {self.base_url} not ready in {timeout_s}s; last_error={last}")

    def upload_image(self, image_path: Path, *, upload_name: str | None = None) -> dict[str, Any]:
        body, boundary = _multipart({"type": "input", "overwrite": "true"}, "image", image_path, upload_name or image_path.name)
        req = urllib.request.Request(
            f"{self.base_url}/upload/image",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def submit_prompt(self, prompt: dict[str, Any], *, client_id: str) -> dict[str, Any]:
        return _json_request(f"{self.base_url}/prompt", {"prompt": prompt, "client_id": client_id}, timeout=60)

    def history(self, prompt_id: str) -> dict[str, Any]:
        return _json_request(f"{self.base_url}/history/{urllib.parse.quote(prompt_id)}", timeout=30)

    def queue(self) -> dict[str, Any]:
        """Return {"queue_running": [...], "queue_pending": [...]}; item[1] is the prompt_id."""
        return _json_request(f"{self.base_url}/queue", timeout=10)

    def queue_state(self, prompt_id: str) -> str:
        """'running', 'pending' or 'absent' for a prompt on this worker's native queue."""
        q = self.queue()
        for item in q.get("queue_running", []):
            if len(item) > 1 and item[1] == prompt_id:
                return "running"
        for item in q.get("queue_pending", []):
            if len(item) > 1 and item[1] == prompt_id:
                return "pending"
        return "absent"

    def delete_queued(self, prompt_id: str) -> None:
        _json_request(f"{self.base_url}/queue", {"delete": [prompt_id]}, timeout=10)

    def interrupt(self) -> dict[str, Any]:
        return _json_request(f"{self.base_url}/interrupt", {}, timeout=10)

    def view_url(self, item: dict[str, Any]) -> str:
        qs = urllib.parse.urlencode({
            "filename": item.get("filename", ""),
            "subfolder": item.get("subfolder", ""),
            "type": item.get("type", "output"),
        })
        return f"{self.base_url}/view?{qs}"


def flatten_history_outputs(history_entry: dict[str, Any]) -> list[dict[str, Any]]:
    outs: list[dict[str, Any]] = []
    for node_id, payload in (history_entry.get("outputs") or {}).items():
        if not isinstance(payload, dict):
            continue
        for key, value in payload.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and "filename" in item:
                        outs.append(dict(item, node_id=node_id, output_key=key))
    return outs


def video_artifacts(history_entry: dict[str, Any], client: ComfyClient) -> list[dict[str, Any]]:
    """Video outputs of a finished ComfyUI history entry, with worker view URLs."""
    artifacts = []
    for idx, item in enumerate(flatten_history_outputs(history_entry)):
        if str(item.get("filename", "")).lower().endswith(VIDEO_SUFFIXES):
            artifacts.append({"artifact_id": f"a{idx}", **item, "view_url": client.view_url(item)})
    return artifacts


def history_status(entry: dict[str, Any] | None) -> str | None:
    """Map a ComfyUI history entry to 'completed' / 'failed' / None (not finished)."""
    if not isinstance(entry, dict):
        return None
    status = entry.get("status") or {}
    if status.get("completed") is True or status.get("status_str") == "success":
        return "completed"
    if status.get("status_str") == "error":
        return "failed"
    return None
