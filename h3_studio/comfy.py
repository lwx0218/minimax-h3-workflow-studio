from __future__ import annotations

import json
import mimetypes
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any


def _json_request(url: str, payload: dict[str, Any] | None = None, timeout: float = 30.0) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {} if payload is None else {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def _multipart(fields: dict[str, str], file_field: str, file_path: Path) -> tuple[bytes, str]:
    boundary = f"----h3studio{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for key, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    ctype = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    chunks.append(f"--{boundary}\r\n".encode())
    chunks.append(f'Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"\r\n'.encode())
    chunks.append(f"Content-Type: {ctype}\r\n\r\n".encode())
    chunks.append(file_path.read_bytes())
    chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), boundary


class ComfyClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    @property
    def websocket_url(self) -> str:
        parsed = urllib.parse.urlparse(self.base_url)
        scheme = "wss" if parsed.scheme == "https" else "ws"
        return urllib.parse.urlunparse((scheme, parsed.netloc, "/ws", "", "", ""))

    def system_stats(self) -> dict[str, Any]:
        return _json_request(f"{self.base_url}/system_stats", timeout=10)

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
        raise TimeoutError(f"ComfyUI worker not ready in {timeout_s}s; last_error={last}")

    def upload_image(self, image_path: Path, *, upload_name: str | None = None) -> dict[str, Any]:
        path = image_path
        temp_path: Path | None = None
        if upload_name and upload_name != image_path.name:
            temp_path = image_path.with_name(upload_name)
            temp_path.write_bytes(image_path.read_bytes())
            path = temp_path
        try:
            body, boundary = _multipart({"type": "input", "overwrite": "true"}, "image", path)
            req = urllib.request.Request(
                f"{self.base_url}/upload/image",
                data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def submit_prompt(self, prompt: dict[str, Any], *, client_id: str) -> dict[str, Any]:
        return _json_request(f"{self.base_url}/prompt", {"prompt": prompt, "client_id": client_id}, timeout=60)

    def history(self, prompt_id: str) -> dict[str, Any]:
        return _json_request(f"{self.base_url}/history/{urllib.parse.quote(prompt_id)}", timeout=30)

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
                        copy = dict(item)
                        copy["node_id"] = node_id
                        copy["output_key"] = key
                        outs.append(copy)
    return outs
