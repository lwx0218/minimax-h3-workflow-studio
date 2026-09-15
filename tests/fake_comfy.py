"""A tiny stand-in for a ComfyUI worker: enough of the HTTP API to test the Studio."""
from __future__ import annotations

import json
import threading
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class FakeComfyState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.pending: list[str] = []      # prompt ids waiting
        self.running: str | None = None
        self.history: dict[str, dict[str, Any]] = {}
        self.prompts: dict[str, dict[str, Any]] = {}
        self.interrupts = 0
        self.uploads: list[str] = []
        self.object_info = dict.fromkeys(("MiniMaxH3Director", "UNETLoader", "CLIPLoader", "VAELoader", "CreateVideo", "SaveVideo"), {})
        self.prompt_delay_s = 0.0          # slow down POST /prompt to exercise cancel-during-submit
        self.video = b"\x00\x00\x00\x1cftypisom" + bytes(range(256)) * 8

    def _advance(self) -> None:
        if self.running is None and self.pending:
            self.running = self.pending.pop(0)

    def submit(self, prompt: dict[str, Any], client_id: str) -> str:
        pid = uuid.uuid4().hex
        with self.lock:
            self.prompts[pid] = {"prompt": prompt, "client_id": client_id}
            self.pending.append(pid)
            self._advance()
        return pid

    def finish(self, pid: str, *, error: bool = False) -> None:
        with self.lock:
            if self.running == pid:
                self.running = None
            elif pid in self.pending:
                self.pending.remove(pid)
            prefix = self.prompts[pid]["prompt"].get("10", {}).get("inputs", {}).get("filename_prefix") or self.prompts[pid]["prompt"].get("12", {}).get("inputs", {}).get("filename_prefix", "out")
            sub, _, name = prefix.rpartition("/")
            self.history[pid] = {
                "status": {"status_str": "error" if error else "success", "completed": not error, "messages": [["execution_error", {"exception_message": "boom"}]] if error else []},
                "outputs": {} if error else {"10": {"images": [{"filename": f"{name}_00001_.mp4", "subfolder": sub, "type": "output"}]}},
            }
            self._advance()

    def finish_all(self) -> None:
        with self.lock:
            ids = ([self.running] if self.running else []) + list(self.pending)
        for pid in ids:
            self.finish(pid)


class FakeComfyHandler(BaseHTTPRequestHandler):
    state: FakeComfyState
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args: Any) -> None:
        pass

    def _json(self, data: Any, status: int = 200) -> None:
        raw = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        st = self.state
        if parsed.path == "/system_stats":
            return self._json({"system": {"os": "fake"}, "devices": [{"name": "fake-gpu", "vram_total": 24 * 1024**3, "vram_free": 20 * 1024**3}]})
        if parsed.path == "/object_info":
            return self._json(st.object_info)
        if parsed.path == "/queue":
            with st.lock:
                return self._json({"queue_running": [[0, st.running]] if st.running else [], "queue_pending": [[i + 1, p] for i, p in enumerate(st.pending)]})
        if parsed.path.startswith("/history/"):
            pid = parsed.path.split("/")[-1]
            return self._json({pid: st.history[pid]} if pid in st.history else {})
        if parsed.path == "/view":
            data = st.video
            rng = self.headers.get("Range")
            if rng and rng.startswith("bytes="):
                start_s, end_s = rng[6:].split("-")
                start = int(start_s)
                end = int(end_s) if end_s else len(data) - 1
                chunk = data[start:end + 1]
                self.send_response(206)
                self.send_header("Content-Type", "video/mp4")
                self.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
                self.send_header("Content-Length", str(len(chunk)))
                self.end_headers()
                self.wfile.write(chunk)
                return
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            self.wfile.write(data)
            return
        if parsed.path == "/ws" and self.headers.get("Upgrade", "").lower() == "websocket":
            if "deny" in parsed.query:
                # Emulate ComfyUI refusing the upgrade (origin middleware) on a keep-alive connection.
                return self._json({"error": "forbidden"}, 403)
            # Not a real websocket: complete the upgrade and echo bytes, which is all the proxy test needs.
            self.send_response(101)
            self.send_header("Upgrade", "websocket")
            self.send_header("Connection", "Upgrade")
            self.send_header("X-Client-Id", urllib.parse.parse_qs(parsed.query).get("clientId", [""])[0])
            self.end_headers()
            self.close_connection = True
            conn = self.connection
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                conn.sendall(b"echo:" + chunk)
            return
        if parsed.path == "/":
            body = b"<html><head><title>fake comfy</title></head><body>Origin=" + (self.headers.get("Origin") or "").encode() + b" Host=" + (self.headers.get("Host") or "").encode() + b"</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return self._json({"error": "not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        st = self.state
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if parsed.path == "/prompt":
            if st.prompt_delay_s:
                import time
                time.sleep(st.prompt_delay_s)
            doc = json.loads(body)
            pid = st.submit(doc["prompt"], doc.get("client_id", ""))
            return self._json({"prompt_id": pid, "number": len(st.prompts), "node_errors": {}})
        if parsed.path == "/queue":
            doc = json.loads(body)
            with st.lock:
                for pid in doc.get("delete", []):
                    if pid in st.pending:
                        st.pending.remove(pid)
            return self._json({})
        if parsed.path == "/interrupt":
            with st.lock:
                st.interrupts += 1
                if st.running:
                    st.history[st.running] = {"status": {"status_str": "error", "completed": False, "messages": [["execution_interrupted", {}]]}, "outputs": {}}
                    st.running = None
                    st._advance()
            return self._json({})
        if parsed.path == "/upload/image":
            name = "upload.png"
            for line in body.split(b"\r\n"):
                if b'filename="' in line:
                    name = line.split(b'filename="')[1].split(b'"')[0].decode()
            st.uploads.append(name)
            return self._json({"name": name, "subfolder": "", "type": "input"})
        return self._json({"error": "not found"}, 404)


class _QuietServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):  # connection resets from proxied sockets are expected
        pass


class FakeComfyServer:
    def __init__(self) -> None:
        self.state = FakeComfyState()
        handler = type("Handler", (FakeComfyHandler,), {"state": self.state})
        self.httpd = _QuietServer(("127.0.0.1", 0), handler)
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self) -> "FakeComfyServer":
        self.thread.start()
        return self

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
