"""HTTP entry point: JSON API, static Guided Mode page and the /canvas/ reverse proxy.

Standard library only. Runs on ThreadingHTTPServer so that long-lived proxied
connections (ComfyUI websocket, video streaming) do not block the API.
"""
from __future__ import annotations

import email.parser
import email.policy
import http.client
import json
import shutil
import signal
import socket
import threading
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .assets import validate_assets
from .comfy import ComfyError, open_url
from .config import StudioConfig, apply_project_local_env
from .service import StudioService
from .workers import NoWorkerAvailable

STATIC_DIR = Path(__file__).resolve().parent / "static"
WS_IDLE_TIMEOUT_S = 600  # drop a proxied websocket that has been silent this long (ComfyUI pings every few seconds)
HOP_BY_HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade"}


def parse_multipart(content_type: str, body: bytes, temp_dir: Path) -> tuple[dict[str, str], dict[str, Path]]:
    """Parse multipart/form-data without the deprecated cgi module."""
    fields: dict[str, str] = {}
    files: dict[str, Path] = {}
    if not content_type.lower().startswith("multipart/form-data"):
        for key, values in urllib.parse.parse_qs(body.decode("utf-8", "replace")).items():
            fields[key] = values[0]
        return fields, files
    raw = b"Content-Type: " + content_type.encode("latin-1") + b"\r\nMIME-Version: 1.0\r\n\r\n" + body
    msg = email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(raw)
    for part in msg.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        payload = part.get_payload(decode=True) or b""
        filename = part.get_filename()
        if filename:
            suffix = Path(filename).suffix or ".bin"
            safe = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in str(name)) or "upload"
            temp_dir.mkdir(parents=True, exist_ok=True)
            dest = temp_dir / f"{safe}{suffix}"
            dest.write_bytes(payload)
            files[str(name)] = dest
        else:
            fields[str(name)] = payload.decode("utf-8", "replace")
    return fields, files


class Handler(BaseHTTPRequestHandler):
    service: StudioService
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:  # quieter default log
        if "/api/runs" in str(args[0] if args else "") and "GET" in str(args[0]):
            return
        print(f"{self.address_string()} - {fmt % args}", flush=True)

    # ----- helpers ----------------------------------------------------------
    def send_json(self, data: Any, status: int = 200) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def send_bytes(self, raw: bytes, ctype: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length) if length else b""

    def _parts(self) -> tuple[urllib.parse.ParseResult, list[str]]:
        parsed = urllib.parse.urlparse(self.path)
        return parsed, [p for p in parsed.path.split("/") if p]

    # ----- routing ----------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        parsed, parts = self._parts()
        try:
            if parts and parts[0] == "canvas":
                return self.proxy_canvas(parts, parsed)
            if parsed.path == "/":
                return self.send_bytes((STATIC_DIR / "index.html").read_bytes(), "text/html; charset=utf-8")
            if parsed.path == "/favicon.ico":
                return self.send_bytes(b"", "image/x-icon", 204)
            if parsed.path == "/api/config":
                return self.send_json(self.service.config_view())
            if parsed.path == "/api/workers":
                return self.send_json(self.service.pool.status())
            if parsed.path == "/api/health":
                pool = self.service.pool.status()
                return self.send_json({"ok": pool["healthy_count"] > 0 and not pool["memory_block_reason"], "pool": pool})
            if parsed.path == "/api/assets/check":
                qs = urllib.parse.parse_qs(parsed.query)
                return self.send_json(validate_assets(self.service.config.asset_manifest, compute_sha=qs.get("sha256", ["0"])[0] == "1"))
            if parsed.path == "/api/runs":
                return self.send_json({"runs": self.service.store.list_recent()})
            if len(parts) == 3 and parts[:2] == ["api", "runs"]:
                return self.send_json(self.service.refresh(parts[2]))
            if len(parts) == 6 and parts[:2] == ["api", "runs"] and parts[3] == "artifacts" and parts[5] == "file":
                return self.stream_artifact(parts[2], parts[4])
            return self.send_bytes(b"not found", "text/plain", 404)
        except KeyError as exc:
            return self.send_json({"error": "not_found", "detail": str(exc)}, 404)
        except (BrokenPipeError, ConnectionResetError):
            return None
        except Exception as exc:  # noqa: BLE001
            return self.send_json({"error": "internal", "detail": repr(exc)}, 500)

    def do_POST(self) -> None:  # noqa: N802
        parsed, parts = self._parts()
        try:
            if parts and parts[0] == "canvas":
                return self.proxy_canvas(parts, parsed)
            body = self.read_body()  # always drain so a keep-alive connection stays in sync
            if parsed.path == "/api/runs":
                temp_dir = self.service.config.upload_root / f"upload-{uuid.uuid4().hex}"
                try:
                    fields, files = parse_multipart(self.headers.get("Content-Type", ""), body, temp_dir)
                    return self.send_json(self.service.submit(fields, files), 201)
                finally:
                    shutil.rmtree(temp_dir, ignore_errors=True)
            if len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == "cancel":
                return self.send_json(self.service.cancel(parts[2]))
            return self.send_bytes(b"not found", "text/plain", 404)
        except KeyError as exc:
            return self.send_json({"error": "not_found", "detail": str(exc)}, 404)
        except NoWorkerAvailable as exc:
            return self.send_json({"error": "no_worker_available", "reason": exc.reason, "pool": exc.pool_status}, 503)
        except ValueError as exc:
            return self.send_json({"error": "bad_request", "detail": str(exc)}, 400)
        except Exception as exc:  # noqa: BLE001
            return self.send_json({"error": "internal", "detail": repr(exc)}, 500)

    do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_POST

    # ----- artifact streaming with Range passthrough --------------------------
    def stream_artifact(self, run_id: str, artifact_id: str) -> None:
        source = self.service.artifact_source(run_id, artifact_id)
        headers = {}
        if self.headers.get("Range"):
            headers["Range"] = self.headers["Range"]
        try:
            upstream = open_url(urllib.request.Request(source, headers=headers), 120)
        except ComfyError as exc:
            return self.send_json({"error": "worker_error", "status": exc.status, "detail": exc.body[:300]}, 502)
        except OSError as exc:
            return self.send_json({"error": "worker_unreachable", "detail": repr(exc)}, 502)
        with upstream:
            self.send_response(upstream.status)
            for key in ("Content-Type", "Content-Length", "Content-Range", "Accept-Ranges", "Last-Modified", "ETag"):
                value = upstream.headers.get(key)
                if value:
                    self.send_header(key, value)
            if not upstream.headers.get("Accept-Ranges"):
                self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Disposition", f'inline; filename="{run_id}-{artifact_id}.mp4"')
            expected = upstream.headers.get("Content-Length")
            if not expected:
                self.send_header("Connection", "close")
                self.close_connection = True
            self.end_headers()
            self._copy_body(upstream, int(expected) if expected else None)

    def _copy_body(self, src, expected: int | None) -> None:
        """Stream src to the client; close the connection if the upstream ended early or the client went away."""
        sent = 0
        try:
            while True:
                chunk = src.read(256 * 1024)
                if not chunk:
                    break
                self.wfile.write(chunk)
                sent += len(chunk)
        except OSError:
            self.close_connection = True
            return
        if expected is not None and sent != expected:
            self.close_connection = True

    # ----- /canvas/<worker-id>/... reverse proxy ------------------------------
    def proxy_canvas(self, parts: list[str], parsed: urllib.parse.ParseResult) -> None:
        keep_alive_state = self.close_connection
        if self.command != "GET":
            self.close_connection = True  # early replies below do not read the request body
        if len(parts) == 1:
            first = self.service.pool.first_healthy()
            if first is None:
                return self.send_json({"error": "no_healthy_worker"}, 503)
            return self.redirect(f"/canvas/{first.id}/")
        worker_id = parts[1]
        try:
            worker = self.service.pool.get(worker_id)
        except KeyError:
            return self.send_json({"error": "unknown_worker", "worker": worker_id}, 404)
        prefix = f"/canvas/{worker_id}"
        if parsed.path == prefix:
            return self.redirect(prefix + "/" + (f"?{parsed.query}" if parsed.query else ""))
        upstream_path = parsed.path[len(prefix):] or "/"
        if parsed.query:
            upstream_path += "?" + parsed.query
        self.close_connection = keep_alive_state
        if self.headers.get("Upgrade", "").lower() == "websocket":
            return self.proxy_websocket(worker.host, worker.port, upstream_path)
        return self.proxy_http(worker.host, worker.port, upstream_path)

    def redirect(self, location: str) -> None:
        self.send_response(302)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _upstream_headers(self, host: str, port: int) -> dict[str, str]:
        headers = {}
        for key, value in self.headers.items():
            if key.lower() in HOP_BY_HOP or key.lower() in {"host", "origin", "referer", "accept-encoding"}:
                continue
            headers[key] = value
        headers["Host"] = f"{host}:{port}"
        # ComfyUI's origin-only middleware wants Origin to match Host.
        if self.headers.get("Origin"):
            headers["Origin"] = f"http://{host}:{port}"
        headers["Accept-Encoding"] = "identity"
        return headers

    def proxy_http(self, host: str, port: int, path: str) -> None:
        body = self.read_body()
        conn = http.client.HTTPConnection(host, port, timeout=300)
        headers_sent = False
        try:
            conn.request(self.command, path, body=body if body else None, headers=self._upstream_headers(host, port))
            resp = conn.getresponse()
            self.send_response(resp.status, resp.reason)
            expected = None
            for key, value in resp.getheaders():
                if key.lower() in HOP_BY_HOP:
                    continue
                if key.lower() == "content-length":
                    expected = int(value)
                self.send_header(key, value)
            if expected is None:
                self.send_header("Connection", "close")
                self.close_connection = True
            self.end_headers()
            headers_sent = True
            if self.command != "HEAD":
                self._copy_body(resp, expected)
        except (ConnectionRefusedError, socket.timeout, OSError, http.client.HTTPException) as exc:
            if headers_sent:
                self.close_connection = True
            else:
                self.send_json({"error": "worker_unreachable", "detail": repr(exc)}, 502)
        finally:
            conn.close()

    def proxy_websocket(self, host: str, port: int, path: str) -> None:
        """Forward the upgrade handshake; on 101 pump bytes both ways, otherwise relay the refusal and close."""
        self.close_connection = True
        try:
            upstream = socket.create_connection((host, port), timeout=30)
        except OSError as exc:
            return self.send_json({"error": "worker_unreachable", "detail": repr(exc)}, 502)
        client = self.connection
        try:
            headers = self._upstream_headers(host, port)
            headers["Connection"] = "Upgrade"
            headers["Upgrade"] = "websocket"
            request = f"GET {path} HTTP/1.1\r\n" + "".join(f"{k}: {v}\r\n" for k, v in headers.items()) + "\r\n"
            upstream.sendall(request.encode("latin-1"))
            head = b""
            while b"\r\n\r\n" not in head and len(head) < 65536:
                chunk = upstream.recv(4096)
                if not chunk:
                    break
                head += chunk
            status_line = head.split(b"\r\n", 1)[0]
            client.sendall(head)
            if b" 101 " not in status_line:
                # Refused upgrade (403 origin check, 404, ...): the worker keeps the connection alive; we do not.
                return
            upstream.settimeout(WS_IDLE_TIMEOUT_S)
            client.settimeout(WS_IDLE_TIMEOUT_S)

            def pump(src: socket.socket, dst: socket.socket) -> None:
                try:
                    while True:
                        data = src.recv(65536)
                        if not data:
                            break
                        dst.sendall(data)
                except OSError:
                    pass
                finally:
                    for s_ in (src, dst):
                        try:
                            s_.shutdown(socket.SHUT_RDWR)
                        except OSError:
                            pass

            t = threading.Thread(target=pump, args=(upstream, client), daemon=True)
            t.start()
            pump(client, upstream)
            t.join(timeout=5)
        except OSError:
            pass
        finally:
            try:
                upstream.close()
            except OSError:
                pass


def _raise_interrupt(_signum: int, _frame: Any) -> None:
    raise KeyboardInterrupt


def run_server(config: StudioConfig | None = None) -> None:
    signal.signal(signal.SIGTERM, _raise_interrupt)
    cfg = config or StudioConfig.from_env()
    apply_project_local_env(cfg.repo_root)
    service = StudioService(cfg)
    service.start()
    Handler.service = service
    httpd = ThreadingHTTPServer((cfg.studio_host, cfg.studio_port), Handler)
    httpd.daemon_threads = True
    print(f"H3 Studio {__import__('h3_studio').__version__} listening on http://{cfg.studio_host}:{cfg.studio_port}", flush=True)
    print(f"Worker pool: {len(service.pool.workers)} workers, safe_concurrent_runs={service.pool.safe_concurrent_runs}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        service.stop()
        httpd.server_close()


if __name__ == "__main__":
    run_server()
